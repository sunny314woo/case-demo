# -*- coding: utf-8 -*-
"""
Redis 封装：魔法链接 token 与用户会话

首次编辑：2026-05-07
最近修改：2026-05-07

键约定：
- magic:{token} -> 邮箱字符串，TTL = MAGIC_LINK_TTL；
- session:{session_id} -> user_id 字符串，TTL = SESSION_TTL（读取时可刷新实现滑动过期）。
"""

import redis
import uuid
from config import REDIS_HOST, REDIS_PORT, REDIS_DB, MAGIC_LINK_TTL, SESSION_TTL

# 全局单例连接，避免每次请求重复建立 Redis 客户端。
redis_client = None

def get_redis():
    """获取 Redis 客户端（懒加载单例）。"""
    global redis_client
    if redis_client is None:
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            # 自动 decode 为 str，避免 bytes / str 混用。
            decode_responses=True
        )
    return redis_client

def create_magic_token(email: str) -> str:
    """创建一次性魔法链接 token，并写入 Redis（带过期时间）。"""
    token = uuid.uuid4().hex
    r = get_redis()
    r.setex(f"magic:{token}", MAGIC_LINK_TTL, email)
    return token

def verify_magic_token(token: str) -> str:
    """校验魔法 token，命中后立即删除，保证 token 只能使用一次。"""
    r = get_redis()
    email = r.get(f"magic:{token}")
    if email:
        r.delete(f"magic:{token}")
    return email

def create_session(user_id: int) -> str:
    """创建用户会话并写入 Redis，返回 session_id。"""
    session_id = uuid.uuid4().hex
    r = get_redis()
    r.setex(f"session:{session_id}", SESSION_TTL, user_id)
    return session_id

def get_session(session_id: str) -> int:
    """根据 session_id 获取 user_id，不存在则返回 None。"""
    r = get_redis()
    user_id = r.get(f"session:{session_id}")
    # Redis 中存的是字符串形式的整数，这里转回 int 供 ORM 查询使用。
    return int(user_id) if user_id else None

def delete_session(session_id: str):
    """删除指定会话（登出时调用）。"""
    r = get_redis()
    r.delete(f"session:{session_id}")

def refresh_session(session_id: str):
    """刷新会话 TTL，实现“30 天无活动过期”的滑动过期策略。"""
    r = get_redis()
    user_id = r.get(f"session:{session_id}")
    if user_id:
        r.setex(f"session:{session_id}", SESSION_TTL, user_id)
        return True
    return False
