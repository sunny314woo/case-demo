"""
main.py

FastAPI 项目入口。

启动命令：
    uvicorn app.main:app --reload

这个文件只做“应用级配置”：
- 创建 FastAPI 应用；
- 初始化数据库；
- 注册路由；
- 挂载静态资源目录；
- 挂载上传图片目录；
- 开启 session。
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app import db
from app import articles
from app import auth
from app import uploads


# 读取 .env 文件。没有 .env 也不会报错，程序会使用默认值。
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="Single Blog Demo")

# SessionMiddleware 负责给 request.session 提供能力。
# SECRET_KEY 用来给 session 签名，真实项目里必须换成复杂随机值。
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "dev-secret-key"),
)

# static/ 用来放 CSS、JS 等前端静态文件。
app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")

# uploads/ 用来访问用户上传的图片，例如 /uploads/abc.png。
app.mount("/uploads", StaticFiles(directory=BASE_DIR / "uploads"), name="uploads")


@app.on_event("startup")
def on_startup():
    """应用启动时初始化数据库。"""
    db.init_db()


# 注册路由。路由拆到多个文件里，是为了让 main.py 保持清爽。
app.include_router(auth.router)
app.include_router(uploads.router)
app.include_router(articles.router)
