# -*- coding: utf-8 -*-
"""
用户数据持久化（SQLite + SQLAlchemy）

首次编辑：2026-05-07
最近修改：2026-05-07

说明：
- 单文件演示用 SQLite；迁生产时可仅替换 DATABASE_URL 与引擎参数；
- `is_pro` 使用整型 0/1，便于与 SQLite 默认类型兼容。
"""

from sqlalchemy import create_engine, Column, Integer, String, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from config import DATABASE_URL
from datetime import datetime

Base = declarative_base()

class User(Base):
    """用户表：仅保存演示所需的最小字段。"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False)
    is_pro = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, default=datetime.now)
    last_login_at = Column(TIMESTAMP)

# SQLite 默认不允许跨线程共享连接；FastAPI 多为多线程 worker，故关闭 check_same_thread。
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """初始化数据库表结构（不存在则创建）。"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """FastAPI 依赖：为每个请求提供独立 DB Session。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_or_create_user(db: Session, email: str):
    """按邮箱查用户；不存在则创建（首次魔法链接登录即注册）。"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, is_pro=0)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def get_user_by_id(db: Session, user_id: int):
    """按主键查询用户。"""
    return db.query(User).filter(User.id == user_id).first()

def upgrade_to_pro(db: Session, user_id: int):
    """将用户升级为 PRO。"""
    user = get_user_by_id(db, user_id)
    if user:
        user.is_pro = 1
        db.commit()
        db.refresh(user)
        return True
    return False

def update_last_login(db: Session, user_id: int):
    """更新用户最近登录时间。"""
    user = get_user_by_id(db, user_id)
    if user:
        user.last_login_at = datetime.now()
        db.commit()
        return True
    return False
