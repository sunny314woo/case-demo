# -*- coding: utf-8 -*-
"""
环境与常量配置

首次编辑：2026-05-07
最近修改：2026-05-07

从环境变量读取连接信息与密钥；缺省值尽量贴合本地开发（Redis localhost、SQLite 文件）。
"""

import os
from dotenv import load_dotenv

# 读取项目根目录 .env，便于本地开发时统一配置。
load_dotenv()

# Redis 连接配置：用于存储魔法链接 token 和登录会话。
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

# Resend 邮件配置：用于发送魔法链接邮件。
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "onboarding@resend.dev")
# 本地测试开关：有值时强制发到该邮箱，忽略前端输入邮箱。
FORCE_TEST_RECIPIENT = os.getenv("FORCE_TEST_RECIPIENT", "")

# SQLite 连接串，默认在项目目录生成 users.db。
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./users.db")

# Redis TTL（单位：秒）
# 魔法链接有效期 15 分钟，Session 有效期 30 天（滑动过期）。
MAGIC_LINK_TTL = 900
SESSION_TTL = 2592000
