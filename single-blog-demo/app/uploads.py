"""
uploads.py

图片上传接口。

Quill 编辑器选择图片后，会把图片文件 POST 到 /admin/uploads/image。
后端保存到 uploads/ 目录，并返回图片访问地址。
"""

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse

from app.auth import is_logged_in


router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"


def get_safe_filename(filename: str) -> str:
    """
    生成安全的文件名。

    浏览器上传的原始文件名可能重复，也可能包含奇怪字符。
    教学版用 uuid 生成随机文件名，只保留原始后缀，例如 .png。
    """
    suffix = Path(filename).suffix.lower()
    if suffix not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
        suffix = ".png"
    return f"{uuid4().hex}{suffix}"


@router.post("/admin/uploads/image")
async def upload_image(request: Request, image: UploadFile = File(...)):
    """
    接收图片上传。

    返回格式：
    {
        "url": "/uploads/xxx.png"
    }
    editor.js 会把这个 url 插入到 Quill 正文中。
    """
    if not is_logged_in(request):
        return JSONResponse({"error": "请先登录"}, status_code=401)

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = get_safe_filename(image.filename or "image.png")
    save_path = UPLOAD_DIR / filename

    content = await image.read()
    save_path.write_bytes(content)

    return {"url": f"/uploads/{filename}"}
