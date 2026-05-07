# -*- coding: utf-8 -*-
"""
魔法链接登录系统 - FastAPI 主应用

首次编辑：2026-05-07
最近修改：2026-05-07

职责说明：
- 提供 REST 接口与首页 HTML；
- 魔法链接写入 Redis（magic:*），登录会话写入 Redis（session:*）；
- 用户邮箱与 PRO 状态持久化到 SQLite。

约定：
- 错误响应多为 JSON 字符串 + 对应 HTTP 状态码（与前端 Fetch 解析一致）；
- Cookie `session_id` 使用 HttpOnly，避免 XSS 直接读取会话标识。
"""

from fastapi import FastAPI, Depends, Request, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# --- 业务模块 ---
from database import init_db, get_db, get_or_create_user, get_user_by_id, upgrade_to_pro, update_last_login
from redis_client import create_magic_token, verify_magic_token, create_session, get_session, delete_session, refresh_session
from config import RESEND_API_KEY, FROM_EMAIL, FORCE_TEST_RECIPIENT

from sqlalchemy.orm import Session
import requests
import re
from fastapi.responses import RedirectResponse

# FastAPI 应用实例。
app = FastAPI()

# 挂载静态目录，保留 /static/* 访问能力（虽然首页走的是手动读取）。
app.mount("/static", StaticFiles(directory="static"), name="static")

# 进程启动时初始化数据库表。
init_db()

class SendMagicLinkRequest(BaseModel):
    """发送魔法链接接口请求体。"""
    email: str

class UpgradeRequest(BaseModel):
    """模拟支付升级接口请求体。"""
    order_id: str

def get_current_user(request: Request, db: Session = Depends(get_db)):
    """
    鉴权依赖：
    1) 从 Cookie 读取 session_id
    2) 在 Redis 取 user_id
    3) 刷新 session TTL（滑动过期）
    4) 返回数据库用户对象
    任一步骤失败均视为未登录（返回 None）。
    """
    session_id = request.cookies.get("session_id")
    if not session_id:
        return None
    try:
        user_id = get_session(session_id)
    except Exception:
        return None
    if not user_id:
        return None
    try:
        refresh_session(session_id)
    except Exception:
        return None
    return get_user_by_id(db, user_id)

def is_valid_email(email: str) -> bool:
    """基础邮箱格式校验，拦截明显非法输入。"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def send_email(email: str, token: str):
    """
    发送魔法链接邮件。
    - 若配置了 FORCE_TEST_RECIPIENT，则强制发送到测试邮箱。
    - 若未配置有效 RESEND_API_KEY，则仅打印调试链接，便于本地联调。
    """
    recipient = FORCE_TEST_RECIPIENT if FORCE_TEST_RECIPIENT else email
    if not RESEND_API_KEY or RESEND_API_KEY == "re_xxxxxxxxxxxx":
        # 未配置真实 Key：不落邮件，仅控制台打印完整验证 URL（本地调试）。
        print(f"[DEBUG] Magic link for {recipient}: http://localhost:8000/api/auth/verify?token={token}")
        return True
    
    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "from": FROM_EMAIL,
        "to": recipient,
        "subject": "您的魔法登录链接",
        # 演示环境链接域名写死为 localhost；上线应改为可配置的公网 Base URL。
        "text": f"点击以下链接登录（15分钟内有效）：\n\nhttp://localhost:8000/api/auth/verify?token={token}\n\n如果按钮无法点击，请复制链接到浏览器打开。\n\n此链接为一次性链接，使用后即失效。"
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        return response.status_code == 200
    except Exception:
        # 网络异常或超时：视为发送失败，由上层返回 500。
        return False

@app.get("/")
async def index():
    """返回单页面前端。"""
    with open("static/index.html", "r", encoding="utf-8") as f:
        return Response(content=f.read(), media_type="text/html")

@app.post("/api/auth/send-magic-link")
async def send_magic_link(request: SendMagicLinkRequest):
    """
    发送魔法链接：
    1) 校验邮箱
    2) 生成并缓存 token（Redis）
    3) 发送邮件
    """
    email = request.email.strip()
    if not is_valid_email(email):
        # 与需求一致：非法邮箱返回 400 + 统一 JSON（避免 Pydantic 默认 422）。
        return Response(
            content='{"success": false, "message": "邮箱格式错误"}',
            media_type="application/json",
            status_code=400,
        )
    try:
        # Redis 写入 magic:{token} -> email，TTL 见 config.MAGIC_LINK_TTL。
        token = create_magic_token(email)
    except Exception:
        return Response(
            content='{"success": false, "message": "服务暂时不可用，请稍后重试"}',
            media_type="application/json",
            status_code=503,
        )
    if not send_email(email, token):
        # Resend 返回非 200 或网络失败。
        return Response(
            content='{"success": false, "message": "邮件发送失败，请稍后重试"}',
            media_type="application/json",
            status_code=500,
        )
    return {"success": True, "message": "魔法链接已发送，请查收邮件"}

@app.get("/api/auth/verify")
async def verify_magic_link(token: str, db: Session = Depends(get_db)):
    """
    校验魔法链接：
    1) 校验 token（成功后自动作废）
    2) 按邮箱查找或创建用户
    3) 创建 Redis Session
    4) 写入 Cookie 并 302 跳转首页
    """
    try:
        email = verify_magic_token(token)
    except Exception:
        return Response(
            content='{"success": false, "message": "服务暂时不可用，请稍后重试"}',
            media_type="application/json",
            status_code=503,
        )
    if not email:
        return Response(
            content='{"success": false, "message": "链接无效或已过期"}',
            media_type="application/json",
            status_code=400,
        )
    
    user = get_or_create_user(db, email)
    update_last_login(db, user.id)
    try:
        session_id = create_session(user.id)
    except Exception:
        return Response(
            content='{"success": false, "message": "服务暂时不可用，请稍后重试"}',
            media_type="application/json",
            status_code=503,
        )
    response = RedirectResponse(url="/", status_code=302)
    # max_age 与 Redis session TTL 对齐（30 天）；生产建议补充 Secure / SameSite。
    response.set_cookie(key="session_id", value=session_id, httponly=True, max_age=2592000)
    return response

@app.get("/api/user/me")
async def get_me(user = Depends(get_current_user)):
    """获取当前登录用户信息。"""
    if not user:
        return Response(
            content='{"success": false, "message": "未登录"}',
            media_type="application/json",
            status_code=401,
        )
    # 不返回密码等敏感字段（本 Demo 无密码字段）。
    return {
        "success": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "is_pro": bool(user.is_pro),
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
    }

@app.post("/api/user/upgrade-to-pro")
async def upgrade(request: UpgradeRequest, user = Depends(get_current_user), db: Session = Depends(get_db)):
    """模拟支付升级：仅要求已登录；order_id 当前版本不落库，仅占位演示。"""
    if not user:
        return Response(
            content='{"success": false, "message": "请先登录"}',
            media_type="application/json",
            status_code=401,
        )
    
    try:
        if upgrade_to_pro(db, user.id):
            return {"success": True, "is_pro": True, "message": "升级成功，您现在是PRO用户了"}
        return Response(
            content='{"success": false, "message": "升级失败"}',
            media_type="application/json",
            status_code=400,
        )
    except Exception:
        return Response(
            content='{"success": false, "message": "服务暂时不可用，请稍后重试"}',
            media_type="application/json",
            status_code=503,
        )

@app.post("/api/auth/logout")
async def logout(request: Request):
    """登出：删除 Redis Session，并清理浏览器 Cookie。"""
    session_id = request.cookies.get("session_id")
    try:
        if session_id:
            delete_session(session_id)
    except Exception:
        return Response(
            content='{"success": false, "message": "服务暂时不可用，请稍后重试"}',
            media_type="application/json",
            status_code=503,
        )
    response = Response(content='{"success": true, "message": "已登出"}', media_type="application/json")
    # 同步清除浏览器端 Cookie，避免残留无效 session_id。
    response.delete_cookie("session_id")
    return response

if __name__ == "__main__":
    # 本地直接运行入口：python main.py
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
