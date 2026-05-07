# Single Blog Demo

这是一个适合课堂教学的 FastAPI 单人博客后台 Demo。

目标是让学生在较短时间内跑通一个完整业务闭环：

```text
管理员登录
  ↓
进入文章列表
  ↓
新建文章
  ↓
使用 Quill 编辑 HTML 正文
  ↓
上传图片到 uploads/
  ↓
保存文章到 SQLite
  ↓
前台首页显示文章
  ↓
点击进入详情页
```

## 技术栈

- FastAPI
- SQLite
- 原生 SQL
- Jinja2 模板
- Quill 富文本编辑器
- 本地图片上传

## 项目结构

```text
single-blog-demo/
├── app/
│   ├── main.py          # FastAPI 入口，注册路由和静态目录
│   ├── db.py            # SQLite 连接、建表、文章 CRUD
│   ├── auth.py          # 单管理员登录、退出、登录检查
│   ├── articles.py      # 前台文章展示和后台文章管理
│   ├── uploads.py       # Quill 图片上传接口
│   ├── templates/       # Jinja2 页面模板
│   └── static/          # CSS 和编辑器 JS
├── uploads/             # 上传图片保存目录
├── data/                # SQLite 数据库保存目录
├── requirements.txt
├── .env.example
└── README.md
```

## 快速开始

进入项目目录：

```bash
cd single-blog-demo
```

创建虚拟环境：

```bash
python3 -m venv .venv
```

激活虚拟环境：

```bash
source .venv/bin/activate
```

先升级 pip。

机房环境里的 pip 版本经常比较旧，可能导致依赖安装失败。
建议先用中国内地镜像源升级 pip：

```bash
python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
```

再安装项目依赖：

```bash
pip install -r requirements.txt
```

如果清华源临时不可用，也可以换成阿里源：

```bash
python -m pip install --upgrade pip -i https://mirrors.aliyun.com/pypi/simple
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple
```

上面的 `-i` 参数只对本次命令生效，不会修改学生电脑上的全局 pip 配置。

复制环境变量示例：

```bash
cp .env.example .env
```

启动项目：

```bash
uvicorn app.main:app --reload
```

浏览器访问：

```text
http://127.0.0.1:8000
```

后台登录地址：

```text
http://127.0.0.1:8000/login
```

默认账号密码：

```text
用户名：admin
密码：password
```

## 文件职责说明

### app/main.py

FastAPI 入口文件。

它负责创建应用、注册路由、挂载静态文件、挂载上传目录，并在启动时初始化数据库。

### app/db.py

SQLite 数据库操作文件。

第一版把 SQL 都放在这里，包含：

- 初始化文章表；
- 新增文章；
- 查询文章列表；
- 查询文章详情；
- 更新文章；
- 删除文章。

这样学生可以直接看到 Python 函数和 SQL 语句之间的对应关系。

### app/auth.py

后台登录逻辑。

教学版只支持一个管理员。用户名、密码从 `.env` 中读取。如果没有 `.env`，会使用默认值。

### app/articles.py

文章业务路由。

包含前台和后台：

- 首页文章列表；
- 文章详情；
- 后台文章列表；
- 新增文章；
- 编辑文章；
- 删除文章。

### app/uploads.py

图片上传接口。

Quill 编辑器上传图片时，会请求 `/admin/uploads/image`。后端把图片保存到 `uploads/` 目录，并返回图片地址。

### app/static/editor.js

Quill 初始化和图片上传逻辑。

表单提交前，它会把 Quill 编辑器里的 HTML 写入隐藏字段 `content`，然后后端把 HTML 保存到 SQLite。

## 数据保存在哪里

文章数据保存在：

```text
data/blog.sqlite3
```

上传图片保存在：

```text
uploads/
```

## 教学说明

这个项目故意没有加入以下内容：

- MySQL；
- repository/service 分层；
- SEO 字段；
- 分类和标签；
- 多用户；
- tests 目录；
- docs 目录；
- 复杂配置系统；
- 复杂权限系统；
- 云存储；
- AI 功能；
- 支付功能；
- 产品化部署结构。

原因是第一版的目标不是产品化，而是帮助学生理解一个最小 Web 后台如何完整跑起来。

## 课堂建议讲解顺序

1. 先从 `app/main.py` 看应用如何启动。
2. 再看 `app/db.py`，理解数据库表和 CRUD。
3. 然后看 `app/auth.py`，理解登录和 session。
4. 接着看 `app/articles.py`，串起文章业务流程。
5. 最后看 `app/uploads.py` 和 `app/static/editor.js`，理解图片上传和富文本保存。

## 安全提醒

这个项目是教学 Demo。

正文 HTML 使用了 `safe` 直接渲染，方便课堂展示富文本效果。真实产品中需要对 HTML 做安全清洗，避免 XSS 攻击。
