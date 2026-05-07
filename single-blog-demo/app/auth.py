"""
auth.py

后台登录相关逻辑。

教学版只支持“单管理员”：
- 用户名和密码从 .env 读取；
- 登录状态保存在 session 中；
- 不做多用户、角色、权限表等复杂设计。
"""

import os

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def get_admin_username():
    """读取管理员用户名；如果 .env 没配置，默认是 admin。"""
    return os.getenv("ADMIN_USERNAME", "admin")


def get_admin_password():
    """读取管理员密码；如果 .env 没配置，默认是 password。"""
    return os.getenv("ADMIN_PASSWORD", "password")


def is_logged_in(request: Request) -> bool:
    """
    判断当前请求是否已经登录。

    Session 可以理解为服务端给浏览器发的一张“临时通行证”。
    登录成功后写入 request.session["admin"] = True。
    """
    return request.session.get("admin") is True


def require_login(request: Request):
    """
    后台页面通用的登录检查。

    如果没登录，返回一个重定向响应；
    如果已登录，返回 None。
    """
    if not is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)
    return None


@router.get("/login")
def login_page(request: Request):
    """显示登录页面。"""
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": "",
            "username": get_admin_username(),
        },
    )


@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """处理登录表单提交。"""
    if username == get_admin_username() and password == get_admin_password():
        request.session["admin"] = True
        return RedirectResponse(url="/admin/articles", status_code=303)

    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": "用户名或密码错误",
            "username": username,
        },
        status_code=400,
    )


@router.get("/logout")
def logout(request: Request):
    """退出登录：清空 session 后回到登录页。"""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)
