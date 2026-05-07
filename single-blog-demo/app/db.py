"""
db.py

这个文件专门负责 SQLite 数据库相关操作。

教学版刻意使用“原生 SQL + 普通函数”的写法：
1. 方便学生看到 SQL 到底做了什么；
2. 不引入 ORM，降低第一版理解成本；
3. 不拆 repository/service，避免小 Demo 过度工程化。
"""

import sqlite3
from pathlib import Path
from typing import Optional


# BASE_DIR 指向项目根目录 single-blog-demo/
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据库文件放在 data/ 目录下，便于学生找到。
DB_PATH = BASE_DIR / "data" / "blog.sqlite3"


def get_connection():
    """
    创建并返回一个 SQLite 连接。

    row_factory 的作用：
    默认查询结果是元组，例如 row[0]、row[1]。
    设置为 sqlite3.Row 后，可以像字典一样读取字段：
    row["title"]、row["content"]。
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    初始化数据库。

    FastAPI 启动时会调用这个函数。
    如果 articles 表不存在，就创建它。
    """
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '',
                content TEXT NOT NULL,
                slug TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'draft',
                published_at TEXT,
                cover_image TEXT NOT NULL DEFAULT '',
                seo_title TEXT NOT NULL DEFAULT '',
                seo_description TEXT NOT NULL DEFAULT '',
                view_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        _ensure_article_columns(conn)
        _ensure_taxonomy_tables(conn)
        _ensure_article_category(conn)
        _ensure_article_indexes(conn)


def _ensure_article_columns(conn: sqlite3.Connection):
    """
    兼容旧数据库结构：
    如果列不存在，则按需补齐。
    """
    rows = conn.execute("PRAGMA table_info(articles)").fetchall()
    existing_columns = {row["name"] for row in rows}

    if "slug" not in existing_columns:
        conn.execute("ALTER TABLE articles ADD COLUMN slug TEXT NOT NULL DEFAULT ''")
    if "status" not in existing_columns:
        conn.execute(
            "ALTER TABLE articles ADD COLUMN status TEXT NOT NULL DEFAULT 'draft'"
        )
    if "published_at" not in existing_columns:
        conn.execute("ALTER TABLE articles ADD COLUMN published_at TEXT")
    if "updated_at" not in existing_columns:
        conn.execute(
            "ALTER TABLE articles ADD COLUMN updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"
        )
    if "category_id" not in existing_columns:
        conn.execute("ALTER TABLE articles ADD COLUMN category_id INTEGER")
    if "cover_image" not in existing_columns:
        conn.execute("ALTER TABLE articles ADD COLUMN cover_image TEXT NOT NULL DEFAULT ''")
    if "seo_title" not in existing_columns:
        conn.execute("ALTER TABLE articles ADD COLUMN seo_title TEXT NOT NULL DEFAULT ''")
    if "seo_description" not in existing_columns:
        conn.execute(
            "ALTER TABLE articles ADD COLUMN seo_description TEXT NOT NULL DEFAULT ''"
        )
    if "view_count" not in existing_columns:
        conn.execute("ALTER TABLE articles ADD COLUMN view_count INTEGER NOT NULL DEFAULT 0")


def _ensure_taxonomy_tables(conn: sqlite3.Connection):
    """创建分类、标签及关联表。"""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            slug TEXT NOT NULL UNIQUE
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            slug TEXT NOT NULL UNIQUE
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS article_tags (
            article_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (article_id, tag_id)
        )
        """
    )


def _ensure_article_category(conn: sqlite3.Connection):
    """把旧 summary 中的分类信息迁移留空；这里只保证字段存在。"""
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_articles_category_id
        ON articles(category_id)
        """
    )


def _ensure_article_indexes(conn: sqlite3.Connection):
    """创建常用查询索引。"""
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_articles_slug
        ON articles(slug)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_articles_status_published_at
        ON articles(status, published_at DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_articles_updated_at
        ON articles(updated_at DESC)
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_categories_slug
        ON categories(slug)
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_tags_slug
        ON tags(slug)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_article_tags_tag
        ON article_tags(tag_id)
        """
    )


def _build_slug(title: str, article_id: Optional[int] = None) -> str:
    """
    生成简单 slug：
    - 仅保留字母数字和连字符；
    - 为空时回退到 article-{id}。
    """
    normalized = "".join(ch.lower() if ch.isalnum() else "-" for ch in title).strip("-")
    while "--" in normalized:
        normalized = normalized.replace("--", "-")

    if normalized:
        return normalized
    if article_id is not None:
        return f"article-{article_id}"
    return "article"


def _ensure_unique_slug(
    conn: sqlite3.Connection, base_slug: str, article_id: Optional[int] = None
) -> str:
    """为 slug 追加后缀，直到在 articles 中唯一。"""
    slug = base_slug
    suffix = 2
    while True:
        if article_id is None:
            existing = conn.execute(
                "SELECT id FROM articles WHERE slug = ?",
                (slug,),
            ).fetchone()
        else:
            existing = conn.execute(
                "SELECT id FROM articles WHERE slug = ? AND id != ?",
                (slug, article_id),
            ).fetchone()

        if existing is None:
            return slug
        slug = f"{base_slug}-{suffix}"
        suffix += 1


def _ensure_unique_taxonomy_slug(
    conn: sqlite3.Connection, table_name: str, base_slug: str
) -> str:
    slug = base_slug
    suffix = 2
    while True:
        existing = conn.execute(
            f"SELECT id FROM {table_name} WHERE slug = ?",
            (slug,),
        ).fetchone()
        if existing is None:
            return slug
        slug = f"{base_slug}-{suffix}"
        suffix += 1


def _get_or_create_category(conn: sqlite3.Connection, category_name: str | None):
    if not category_name:
        return None
    trimmed = category_name.strip()
    if not trimmed:
        return None

    row = conn.execute(
        "SELECT id FROM categories WHERE name = ?",
        (trimmed,),
    ).fetchone()
    if row:
        return row["id"]

    base_slug = _build_slug(trimmed)
    slug = _ensure_unique_taxonomy_slug(conn, "categories", base_slug)
    cursor = conn.execute(
        "INSERT INTO categories (name, slug) VALUES (?, ?)",
        (trimmed, slug),
    )
    return cursor.lastrowid


def _upsert_tags(conn: sqlite3.Connection, article_id: int, tags_text: str | None):
    raw_tags = []
    if tags_text:
        raw_tags = [item.strip() for item in tags_text.split(",")]
    tag_names = []
    seen = set()
    for name in raw_tags:
        if not name:
            continue
        lowered = name.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        tag_names.append(name)

    conn.execute("DELETE FROM article_tags WHERE article_id = ?", (article_id,))
    for tag_name in tag_names:
        row = conn.execute("SELECT id FROM tags WHERE name = ?", (tag_name,)).fetchone()
        if row is None:
            base_slug = _build_slug(tag_name)
            slug = _ensure_unique_taxonomy_slug(conn, "tags", base_slug)
            cursor = conn.execute(
                "INSERT INTO tags (name, slug) VALUES (?, ?)",
                (tag_name, slug),
            )
            tag_id = cursor.lastrowid
        else:
            tag_id = row["id"]
        conn.execute(
            "INSERT INTO article_tags (article_id, tag_id) VALUES (?, ?)",
            (article_id, tag_id),
        )


def create_article(
    title: str,
    summary: str,
    content: str,
    status: str,
    published_at: Optional[str],
    category_name: str | None,
    tags_text: str | None,
    cover_image: str | None,
    seo_title: str | None,
    seo_description: str | None,
):
    """新增一篇文章。"""
    with get_connection() as conn:
        category_id = _get_or_create_category(conn, category_name)
        cursor = conn.execute(
            """
            INSERT INTO articles (
                title, summary, content, slug, status, published_at, category_id,
                cover_image, seo_title, seo_description
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                summary,
                content,
                "",
                status,
                published_at,
                category_id,
                (cover_image or "").strip(),
                (seo_title or "").strip(),
                (seo_description or "").strip(),
            ),
        )
        article_id = cursor.lastrowid
        base_slug = _build_slug(title, article_id)
        slug = _ensure_unique_slug(conn, base_slug, article_id)
        conn.execute(
            """
            UPDATE articles
            SET slug = ?
            WHERE id = ?
            """,
            (slug, article_id),
        )
        _upsert_tags(conn, article_id=article_id, tags_text=tags_text)
        return article_id


def list_public_articles(
    page: int,
    page_size: int,
    keyword: str | None = None,
    category_slug: str | None = None,
    tag_slug: str | None = None,
):
    """前台文章分页列表：仅展示已发布且发布时间已到的文章。"""
    offset = (page - 1) * page_size
    with get_connection() as conn:
        where_sql, args = _build_public_list_filters(keyword, category_slug, tag_slug)
        total = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM articles
            LEFT JOIN categories ON categories.id = articles.category_id
            WHERE status = 'published'
              AND (published_at IS NULL OR published_at <= CURRENT_TIMESTAMP)
              AND """
            + where_sql,
            args,
        ).fetchone()["count"]

        rows = conn.execute(
            """
            SELECT
                articles.id,
                articles.title,
                articles.slug,
                articles.summary,
                articles.status,
                articles.published_at,
                articles.created_at,
                articles.updated_at,
                articles.view_count,
                categories.name AS category_name,
                categories.slug AS category_slug
            FROM articles
            LEFT JOIN categories ON categories.id = articles.category_id
            WHERE status = 'published'
              AND (published_at IS NULL OR published_at <= CURRENT_TIMESTAMP)
              AND """
            + where_sql
            + """
            ORDER BY COALESCE(articles.published_at, articles.created_at) DESC, articles.id DESC
            LIMIT ? OFFSET ?
            """,
            [*args, page_size, offset],
        ).fetchall()
        return rows, total


def list_admin_articles(page: int, page_size: int):
    """后台文章分页列表：展示全部状态。"""
    offset = (page - 1) * page_size
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) AS count FROM articles").fetchone()["count"]
        rows = conn.execute(
            """
            SELECT
                articles.id,
                articles.title,
                articles.slug,
                articles.summary,
                articles.status,
                articles.published_at,
                articles.created_at,
                articles.updated_at,
                articles.view_count,
                categories.name AS category_name
            FROM articles
            LEFT JOIN categories ON categories.id = articles.category_id
            ORDER BY articles.updated_at DESC, articles.id DESC
            LIMIT ? OFFSET ?
            """,
            (page_size, offset),
        ).fetchall()
        return rows, total


def get_article(article_id: int):
    """根据 id 查询单篇文章；如果不存在，返回 None。"""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                articles.id,
                articles.title,
                articles.slug,
                articles.summary,
                articles.content,
                articles.status,
                articles.published_at,
                articles.created_at,
                articles.updated_at,
                articles.cover_image,
                articles.seo_title,
                articles.seo_description,
                articles.view_count,
                categories.name AS category_name,
                categories.slug AS category_slug
            FROM articles
            LEFT JOIN categories ON categories.id = articles.category_id
            WHERE articles.id = ?
            """,
            (article_id,),
        ).fetchone()
        return row


def get_public_article(article_id: int):
    """根据 id 获取对前台可见的文章。"""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                articles.id,
                articles.title,
                articles.slug,
                articles.summary,
                articles.content,
                articles.status,
                articles.published_at,
                articles.created_at,
                articles.updated_at,
                articles.cover_image,
                articles.seo_title,
                articles.seo_description,
                articles.view_count,
                categories.name AS category_name,
                categories.slug AS category_slug
            FROM articles
            LEFT JOIN categories ON categories.id = articles.category_id
            WHERE articles.id = ?
              AND articles.status = 'published'
              AND (articles.published_at IS NULL OR articles.published_at <= CURRENT_TIMESTAMP)
            """,
            (article_id,),
        ).fetchone()
        return row


def update_article(
    article_id: int,
    title: str,
    summary: str,
    content: str,
    status: str,
    published_at: Optional[str],
    category_name: str | None,
    tags_text: str | None,
    cover_image: str | None,
    seo_title: str | None,
    seo_description: str | None,
):
    """更新一篇文章。"""
    with get_connection() as conn:
        base_slug = _build_slug(title, article_id)
        slug = _ensure_unique_slug(conn, base_slug, article_id)
        category_id = _get_or_create_category(conn, category_name)
        conn.execute(
            """
            UPDATE articles
            SET title = ?,
                slug = ?,
                summary = ?,
                content = ?,
                status = ?,
                published_at = ?,
                category_id = ?,
                cover_image = ?,
                seo_title = ?,
                seo_description = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                title,
                slug,
                summary,
                content,
                status,
                published_at,
                category_id,
                (cover_image or "").strip(),
                (seo_title or "").strip(),
                (seo_description or "").strip(),
                article_id,
            ),
        )
        _upsert_tags(conn, article_id=article_id, tags_text=tags_text)


def increment_article_view_count(article_id: int):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE articles
            SET view_count = view_count + 1
            WHERE id = ?
              AND status = 'published'
              AND (published_at IS NULL OR published_at <= CURRENT_TIMESTAMP)
            """,
            (article_id,),
        )


def list_related_articles(article_id: int, limit: int = 4):
    with get_connection() as conn:
        article = conn.execute(
            """
            SELECT id, category_id
            FROM articles
            WHERE id = ?
            """,
            (article_id,),
        ).fetchone()
        if article is None:
            return []

        rows = conn.execute(
            """
            SELECT
                a.id,
                a.title,
                a.summary,
                a.published_at,
                a.created_at
            FROM articles a
            WHERE a.id != ?
              AND a.status = 'published'
              AND (a.published_at IS NULL OR a.published_at <= CURRENT_TIMESTAMP)
              AND (
                (a.category_id IS NOT NULL AND a.category_id = ?)
                OR EXISTS (
                    SELECT 1
                    FROM article_tags t1
                    JOIN article_tags t2 ON t1.tag_id = t2.tag_id
                    WHERE t1.article_id = ?
                      AND t2.article_id = a.id
                )
              )
            ORDER BY COALESCE(a.published_at, a.created_at) DESC
            LIMIT ?
            """,
            (article_id, article["category_id"], article_id, limit),
        ).fetchall()
        return rows


def _build_public_list_filters(
    keyword: str | None, category_slug: str | None, tag_slug: str | None
):
    clauses = ["1 = 1"]
    args = []
    if keyword:
        like_keyword = f"%{keyword.strip()}%"
        clauses.append("(articles.title LIKE ? OR articles.summary LIKE ? OR articles.content LIKE ?)")
        args.extend([like_keyword, like_keyword, like_keyword])
    if category_slug:
        clauses.append("categories.slug = ?")
        args.append(category_slug.strip())
    if tag_slug:
        clauses.append(
            """
            EXISTS (
                SELECT 1
                FROM article_tags
                JOIN tags ON tags.id = article_tags.tag_id
                WHERE article_tags.article_id = articles.id
                  AND tags.slug = ?
            )
            """
        )
        args.append(tag_slug.strip())
    return " AND ".join(clauses), args


def list_categories():
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT id, name, slug
            FROM categories
            ORDER BY name ASC
            """
        ).fetchall()


def get_article_tags(article_id: int):
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT tags.id, tags.name, tags.slug
            FROM article_tags
            JOIN tags ON tags.id = article_tags.tag_id
            WHERE article_tags.article_id = ?
            ORDER BY tags.name ASC
            """,
            (article_id,),
        ).fetchall()


def delete_article(article_id: int):
    """删除一篇文章。"""
    with get_connection() as conn:
        conn.execute("DELETE FROM article_tags WHERE article_id = ?", (article_id,))
        conn.execute("DELETE FROM articles WHERE id = ?", (article_id,))
