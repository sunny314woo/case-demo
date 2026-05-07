"""
articles.py

文章相关页面和接口。

这里同时包含前台和后台文章功能：
- 前台：首页、文章详情；
- 后台：列表、新建、编辑、删除。

教学版把它们放在一个文件中，是为了让学生更容易追踪“一个业务模块”的完整流程。
"""

import re
from datetime import datetime
from html import unescape

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app import db
from app.auth import require_login


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
PAGE_SIZE = 10


def _read_page(request: Request) -> int:
    """读取分页参数，非法值回退到 1。"""
    try:
        return max(1, int(request.query_params.get("page", 1)))
    except (TypeError, ValueError):
        return 1


def _normalize_status_and_published_at(status: str, published_at: str | None):
    """
    统一处理后台提交的状态和发布时间。
    - draft: published_at 置空
    - published: 无时间则立即发布
    - scheduled: 必须有时间，且存成 SQLite 友好的格式
    """
    status = (status or "draft").strip().lower()
    if status not in {"draft", "published", "scheduled"}:
        status = "draft"

    normalized_time = None
    if published_at:
        raw = published_at.strip()
        if raw:
            try:
                parsed = datetime.strptime(raw, "%Y-%m-%dT%H:%M")
                normalized_time = parsed.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                normalized_time = None

    if status == "draft":
        return status, None
    if status == "published" and normalized_time is None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return status, now
    if status == "scheduled" and normalized_time is None:
        return "draft", None
    return status, normalized_time


def _generate_summary(summary: str, content: str, limit: int = 140) -> str:
    """
    保存时兜底生成摘要：
    - 若用户填写摘要，则直接使用；
    - 否则从正文 HTML 提取纯文本，截断到 limit。
    """
    if summary and summary.strip():
        return summary.strip()

    plain = re.sub(r"<[^>]+>", " ", content or "")
    plain = unescape(re.sub(r"\s+", " ", plain)).strip()
    if not plain:
        return ""
    if len(plain) <= limit:
        return plain
    return f"{plain[:limit].rstrip()}..."


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    """前台首页：展示文章列表。"""
    page = _read_page(request)
    keyword = (request.query_params.get("q") or "").strip()
    category_slug = (request.query_params.get("category") or "").strip()
    tag_slug = (request.query_params.get("tag") or "").strip()
    articles, total = db.list_public_articles(
        page=page,
        page_size=PAGE_SIZE,
        keyword=keyword or None,
        category_slug=category_slug or None,
        tag_slug=tag_slug or None,
    )
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    categories = db.list_categories()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "articles": articles,
            "page": page,
            "total_pages": total_pages,
            "q": keyword,
            "category": category_slug,
            "tag": tag_slug,
            "categories": categories,
        },
    )


@router.get("/articles/{article_id}", response_class=HTMLResponse)
def detail(request: Request, article_id: int):
    """前台文章详情页。"""
    article = db.get_public_article(article_id)
    if article is None:
        return templates.TemplateResponse(
            "detail.html",
            {
                "request": request,
                "article": None,
            },
            status_code=404,
        )

    db.increment_article_view_count(article_id)
    article = db.get_public_article(article_id)
    tags = db.get_article_tags(article_id)
    related_articles = db.list_related_articles(article_id, limit=4)
    seo_title = article["seo_title"] or article["title"]
    seo_description = article["seo_description"] or article["summary"] or article["title"]
    return templates.TemplateResponse(
        "detail.html",
        {
            "request": request,
            "article": article,
            "tags": tags,
            "related_articles": related_articles,
            "seo_title": seo_title,
            "seo_description": seo_description,
            "seo_image": article["cover_image"],
        },
    )


@router.get("/admin/articles", response_class=HTMLResponse)
def admin_list(request: Request):
    """后台文章列表。"""
    redirect = require_login(request)
    if redirect:
        return redirect

    page = _read_page(request)
    articles, total = db.list_admin_articles(page=page, page_size=PAGE_SIZE)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    return templates.TemplateResponse(
        "admin_list.html",
        {
            "request": request,
            "articles": articles,
            "page": page,
            "total_pages": total_pages,
        },
    )


@router.get("/admin/articles/new", response_class=HTMLResponse)
def admin_new_page(request: Request):
    """显示新建文章表单。"""
    redirect = require_login(request)
    if redirect:
        return redirect

    categories = db.list_categories()
    return templates.TemplateResponse(
        "admin_form.html",
        {
            "request": request,
            "mode": "new",
            "article": None,
            "categories": categories,
            "tag_text": "",
        },
    )


@router.post("/admin/articles/new")
def admin_create(
    request: Request,
    title: str = Form(...),
    summary: str = Form(""),
    content: str = Form(...),
    status: str = Form("draft"),
    published_at: str = Form(""),
    category_name: str = Form(""),
    tags: str = Form(""),
    cover_image: str = Form(""),
    seo_title: str = Form(""),
    seo_description: str = Form(""),
):
    """处理新建文章提交。"""
    redirect = require_login(request)
    if redirect:
        return redirect

    normalized_status, normalized_time = _normalize_status_and_published_at(
        status=status, published_at=published_at
    )
    final_summary = _generate_summary(summary=summary, content=content)
    article_id = db.create_article(
        title=title,
        summary=final_summary,
        content=content,
        status=normalized_status,
        published_at=normalized_time,
        category_name=category_name,
        tags_text=tags,
        cover_image=cover_image,
        seo_title=seo_title,
        seo_description=seo_description,
    )
    if normalized_status == "published":
        return RedirectResponse(url=f"/articles/{article_id}", status_code=303)
    return RedirectResponse(url="/admin/articles", status_code=303)


@router.get("/admin/articles/{article_id}/edit", response_class=HTMLResponse)
def admin_edit_page(request: Request, article_id: int):
    """显示编辑文章表单。"""
    redirect = require_login(request)
    if redirect:
        return redirect

    article = db.get_article(article_id)
    if article is None:
        return RedirectResponse(url="/admin/articles", status_code=303)
    categories = db.list_categories()
    tags = db.get_article_tags(article_id)
    tag_text = ", ".join(tag["name"] for tag in tags)

    return templates.TemplateResponse(
        "admin_form.html",
        {
            "request": request,
            "mode": "edit",
            "article": article,
            "categories": categories,
            "tag_text": tag_text,
        },
    )


@router.post("/admin/articles/{article_id}/edit")
def admin_update(
    request: Request,
    article_id: int,
    title: str = Form(...),
    summary: str = Form(""),
    content: str = Form(...),
    status: str = Form("draft"),
    published_at: str = Form(""),
    category_name: str = Form(""),
    tags: str = Form(""),
    cover_image: str = Form(""),
    seo_title: str = Form(""),
    seo_description: str = Form(""),
):
    """处理编辑文章提交。"""
    redirect = require_login(request)
    if redirect:
        return redirect

    normalized_status, normalized_time = _normalize_status_and_published_at(
        status=status, published_at=published_at
    )
    final_summary = _generate_summary(summary=summary, content=content)
    db.update_article(
        article_id=article_id,
        title=title,
        summary=final_summary,
        content=content,
        status=normalized_status,
        published_at=normalized_time,
        category_name=category_name,
        tags_text=tags,
        cover_image=cover_image,
        seo_title=seo_title,
        seo_description=seo_description,
    )
    if normalized_status == "published":
        return RedirectResponse(url=f"/articles/{article_id}", status_code=303)
    return RedirectResponse(url="/admin/articles", status_code=303)


@router.post("/admin/articles/autosave")
def admin_autosave(
    request: Request,
    article_id: int = Form(0),
    title: str = Form("未命名草稿"),
    summary: str = Form(""),
    content: str = Form(""),
    category_name: str = Form(""),
    tags: str = Form(""),
    cover_image: str = Form(""),
    seo_title: str = Form(""),
    seo_description: str = Form(""),
):
    """自动保存草稿（新建时自动创建草稿并切换到编辑 URL）。"""
    redirect = require_login(request)
    if redirect:
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)

    safe_title = (title or "").strip() or "未命名草稿"
    final_summary = _generate_summary(summary=summary, content=content)
    if article_id > 0:
        db.update_article(
            article_id=article_id,
            title=safe_title,
            summary=final_summary,
            content=content,
            status="draft",
            published_at=None,
            category_name=category_name,
            tags_text=tags,
            cover_image=cover_image,
            seo_title=seo_title,
            seo_description=seo_description,
        )
        target_id = article_id
    else:
        target_id = db.create_article(
            title=safe_title,
            summary=final_summary,
            content=content,
            status="draft",
            published_at=None,
            category_name=category_name,
            tags_text=tags,
            cover_image=cover_image,
            seo_title=seo_title,
            seo_description=seo_description,
        )

    return JSONResponse(
        {
            "ok": True,
            "article_id": target_id,
            "edit_url": f"/admin/articles/{target_id}/edit",
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )


@router.post("/admin/articles/preview", response_class=HTMLResponse)
def admin_preview(
    request: Request,
    title: str = Form("预览文章"),
    summary: str = Form(""),
    content: str = Form(""),
    category_name: str = Form(""),
    tags: str = Form(""),
    cover_image: str = Form(""),
    seo_title: str = Form(""),
    seo_description: str = Form(""),
):
    """后台预览：不落库，直接渲染详情模板。"""
    redirect = require_login(request)
    if redirect:
        return HTMLResponse("请先登录后台。", status_code=401)

    final_summary = _generate_summary(summary=summary, content=content)
    seo_final_title = (seo_title or "").strip() or (title or "预览文章")
    seo_final_description = (
        (seo_description or "").strip()
        or final_summary
        or (title or "预览文章")
    )
    tag_items = []
    seen = set()
    for item in (tags or "").split(","):
        name = item.strip()
        if not name:
            continue
        lowered = name.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        tag_items.append({"name": name, "slug": re.sub(r"\s+", "-", lowered)})

    article = {
        "id": 0,
        "title": title or "预览文章",
        "summary": final_summary,
        "content": content or "<p>暂无正文</p>",
        "published_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "view_count": 0,
        "category_name": category_name.strip() if category_name else "",
    }

    return templates.TemplateResponse(
        "detail.html",
        {
            "request": request,
            "article": article,
            "tags": tag_items,
            "related_articles": [],
            "seo_title": seo_final_title,
            "seo_description": seo_final_description,
            "seo_image": (cover_image or "").strip(),
        },
    )


@router.post("/admin/articles/{article_id}/delete")
def admin_delete(request: Request, article_id: int):
    """删除文章。"""
    redirect = require_login(request)
    if redirect:
        return redirect

    db.delete_article(article_id)
    return RedirectResponse(url="/admin/articles", status_code=303)
