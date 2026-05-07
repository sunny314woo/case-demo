"""
文件用途：
数据库初始化与连接管理
当前文件包含功能：
1. SQLite 数据库连接
2. 初始化数据表
最近一次修改：
初始化学生成绩数据库
"""
# 【MODIFIED】初始化 SQLite 数据库连接功能
import sqlite3
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = _BASE_DIR / "data" / "grades.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_connection():
    """
    获取 SQLite 数据库连接
    输入：
    无
    输出：
    sqlite3.Connection
    是否影响全局状态：
    否
    """
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    初始化数据库表
    输入：
    无
    输出：
    无
    副作用：
    如果数据表不存在，则创建 students 表
    """
    conn = get_connection()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as file:
        schema_sql = file.read()
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()
