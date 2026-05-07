# 学生成绩管理教学 Demo（方案 B）

FastAPI + Jinja2 SSR + SQLite（`sqlite3` 原生 SQL）的课堂用 CRUD 示例：列表、新增、编辑、删除；列表中自动显示总分与平均分。

## 环境要求

- Python 3.10+（建议与课堂环境一致）

## 安装与运行

在项目根目录 `student-grade-demo/` 下执行：

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

浏览器访问：<http://127.0.0.1:8000>

## 目录说明

| 路径 | 说明 |
|------|------|
| `app/main.py` | 路由、CRUD、页面渲染 |
| `app/db.py` | 连接与建表初始化 |
| `app/schema.sql` | 建表 SQL |
| `app/templates/` | Jinja2 模板 |
| `app/static/style.css` | 简单样式 |
| `data/grades.db` | SQLite 数据文件（首次启动后自动生成） |

## 课堂说明

- 无登录、无权限、无部署约束，便于随时回滚与讲解。
- 删除使用 GET 链接仅为演示简单流程，生产环境应改为 POST 并做确认。
