"""
文件用途：
学生成绩管理系统主程序
当前文件包含功能：
1. 成绩列表
2. 新增学生成绩
3. 编辑学生成绩
4. 删除学生成绩
最近一次修改：
完成 FastAPI + SQLite 教学 CRUD Demo
"""
# 【MODIFIED】引入 FastAPI 与模板系统
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pathlib import Path

from .db import get_connection, init_db

app = FastAPI()
# 【MODIFIED】挂载静态资源目录
_BASE = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(_BASE / "static")), name="static")
templates = Jinja2Templates(directory=str(_BASE / "templates"))
# 【MODIFIED】程序启动时初始化数据库
init_db()


@app.get("/")
def index(request: Request):
    """
    首页成绩列表
    输入：
    request
    输出：
    HTML 页面
    """
    conn = get_connection()
    students = conn.execute("""
        SELECT *,
               (chinese + math + english) AS total,
               ROUND((chinese + math + english) / 3, 2) AS average
        FROM students
        ORDER BY total DESC
    """).fetchall()
    conn.close()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "students": students
        }
    )


@app.get("/students/new")
def create_page(request: Request):
    """
    新增页面
    输入：
    request
    输出：
    HTML 页面
    """
    return templates.TemplateResponse(
        "create.html",
        {
            "request": request
        }
    )


@app.post("/students/new")
def create_student(
    student_no: str = Form(...),
    name: str = Form(...),
    chinese: float = Form(...),
    math: float = Form(...),
    english: float = Form(...)
):
    """
    新增学生成绩
    输入：
    学生表单数据
    输出：
    重定向首页
    副作用：
    写入数据库
    """
    conn = get_connection()
    conn.execute("""
        INSERT INTO students (
            student_no,
            name,
            chinese,
            math,
            english
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        student_no,
        name,
        chinese,
        math,
        english
    ))
    conn.commit()
    conn.close()
    return RedirectResponse("/", status_code=303)


@app.get("/students/{student_id}/edit")
def edit_page(request: Request, student_id: int):
    """
    编辑页面
    输入：
    student_id
    输出：
    HTML 页面
    """
    conn = get_connection()
    student = conn.execute("""
        SELECT * FROM students
        WHERE id = ?
    """, (student_id,)).fetchone()
    conn.close()
    if student is None:
        raise HTTPException(status_code=404, detail="未找到该学生")
    return templates.TemplateResponse(
        "edit.html",
        {
            "request": request,
            "student": student
        }
    )


@app.post("/students/{student_id}/edit")
def update_student(
    student_id: int,
    student_no: str = Form(...),
    name: str = Form(...),
    chinese: float = Form(...),
    math: float = Form(...),
    english: float = Form(...)
):
    """
    更新学生成绩
    输入：
    学生表单数据
    输出：
    重定向首页
    副作用：
    更新数据库
    """
    conn = get_connection()
    cur = conn.execute("""
        UPDATE students
        SET
            student_no = ?,
            name = ?,
            chinese = ?,
            math = ?,
            english = ?
        WHERE id = ?
    """, (
        student_no,
        name,
        chinese,
        math,
        english,
        student_id
    ))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="未找到该学生")
    return RedirectResponse("/", status_code=303)


@app.get("/students/{student_id}/delete")
def delete_student(student_id: int):
    """
    删除学生成绩
    输入：
    student_id
    输出：
    重定向首页
    副作用：
    删除数据库记录
    """
    conn = get_connection()
    conn.execute("""
        DELETE FROM students
        WHERE id = ?
    """, (student_id,))
    conn.commit()
    conn.close()
    return RedirectResponse("/", status_code=303)
