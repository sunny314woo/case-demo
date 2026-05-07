# 魔法链接登录（Magic Link）演示项目

基于 **FastAPI + Redis + SQLite + Resend** 的极简邮箱魔法链接登录 / 注册 Demo，前端为单页 `static/index.html`。适用于教学演示或后续接入真实支付与账号体系的雏形。

---

## 功能概览


| 功能      | 说明                                            |
| ------- | --------------------------------------------- |
| 魔法链接登录  | 用户提交邮箱后收到一次性链接，点击即登录或注册                       |
| Session | 登录态存 Redis，Cookie 携带 `session_id`（HttpOnly）   |
| 身份      | 默认 FREE；登录后可「模拟支付」升级为 PRO（写 SQLite）           |
| 登出      | 删除 Redis session，并清除浏览器中的 `session_id` Cookie |


---

## 技术栈

- **Web**：FastAPI、Uvicorn  
- **缓存 / 会话**：Redis（魔法 token、session）  
- **持久化**：SQLite（用户邮箱、`is_pro`、时间戳）  
- **邮件**：Resend HTTP API（`requests`）  
- **前端**：单 HTML + 内联 CSS / JS（Fetch）

> **说明**：仓库 `.env` 中的 Paddle（沙箱 URL、API Key、Webhook Secret）为**预留配置**，当前业务代码**尚未接入** Paddle；接入 Checkout / Webhook 时可沿用同一 `.env` 结构。

---

## 环境要求

- Python **3.9+**（建议使用 3.10+）  
- **Redis** 运行于 `localhost:6379`（或通过环境变量指定主机与端口）  
- 可选：**Resend** 账号与 API Key（未配置有效 Key 时，可在控制台打印调试链接，见下文）

---

## 快速开始

### 1. 克隆并进入目录

```bash
cd login-pay-pro
```

### 2. 创建虚拟环境（推荐）

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

依赖包含：`fastapi`、`uvicorn`、`redis`、`python-dotenv`、`sqlalchemy`、`requests`、`email-validator`。

### 4. 启动 Redis

**macOS（Homebrew）示例：**

```bash
brew services start redis
redis-cli ping   # 期望输出 PONG
```

### 5. 配置环境变量

复制或编辑项目根目录 `.env`（可参考下方「环境变量说明」）。**请勿将真实密钥提交到 Git**；建议将 `.env`、`users.db` 加入 `.gitignore`。

### 6. 启动应用

```bash
python main.py
```

或使用 Uvicorn：

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

浏览器访问：**[http://localhost:8000](http://localhost:8000)**

---

## 环境变量说明（`.env`）


| 变量名                    | 必填  | 默认值 / 说明                                                   |
| ---------------------- | --- | ---------------------------------------------------------- |
| `REDIS_HOST`           | 否   | `localhost`                                                |
| `REDIS_PORT`           | 否   | `6379`                                                     |
| `REDIS_DB`             | 否   | `0`                                                        |
| `DATABASE_URL`         | 否   | `sqlite:///./users.db`，SQLite 数据库文件路径                      |
| `RESEND_API_KEY`       | 否   | Resend API Key；为空或为占位符时走调试输出（见「邮件行为」）                      |
| `FROM_EMAIL`           | 否   | 发件人地址，需与 Resend 账号 / 已验证域名一致                               |
| `FORCE_TEST_RECIPIENT` | 否   | **本地测试用**：若填写邮箱，则**无论用户输入什么收件邮箱**，实际发信都只发到该地址；留空则发到用户提交的邮箱 |


**Resend 测试账号限制（常见）：**

- 未验证自有域名前，Resend 往往只允许向**账号关联的测试邮箱**发信。  
- 此时可设置 `FORCE_TEST_RECIPIENT=你的测试邮箱`，避免接口因收件人不合法而失败。  
- 正式对外发信：在 Resend 完成域名验证，将 `FROM_EMAIL` 改为该域名下的地址，并**清空** `FORCE_TEST_RECIPIENT`。

**Paddle（预留，当前代码未读取）：**

可在 `.env` 中保留如下结构，便于后续接入结账与 Webhook：

```env
# ================================
# Paddle API 配置
# ================================
# 沙箱: https://sandbox-api.paddle.com
# 生产: https://api.paddle.com
PADDLE_API_URL=https://sandbox-api.paddle.com
PADDLE_API_KEY=pdl_sdbx_apikey_xxxxxxxx
PADDLE_WEBHOOK_SECRET=pdl_ntfset_xxxxxxxx
```

---

## 邮件行为说明

1. `**RESEND_API_KEY` 未配置或为占位 `re_xxxxxxxxxxxx**`
  - 不会调用 Resend。  
  - 服务端会在控制台打印魔法链接 URL（便于开发调试）。
2. `**RESEND_API_KEY` 已配置**
  - 调用 `https://api.resend.com/emails` 发送邮件。  
  - 若配置了 `FORCE_TEST_RECIPIENT`，实际收件人为该变量指定的邮箱。  
  - 发送失败时接口返回 `500` 及 JSON 错误提示（不会假装发送成功）。

邮件正文中的登录链接形如：

`http://localhost:8000/api/auth/verify?token={token}`

生产环境请改为你的公网域名与 HTTPS。

---

## Redis 键设计


| Key 模式                 | 含义               | TTL             |
| ---------------------- | ---------------- | --------------- |
| `magic:{token}`        | 魔法链接对应的用户邮箱（一次性） | 900 秒（15 分钟）    |
| `session:{session_id}` | 登录用户 ID          | 2592000 秒（30 天） |


验证链接成功后，`magic:{token}` 会被删除；访问 `/api/user/me` 时会刷新 session 的过期时间。

---

## SQLite 数据表（`users`）


| 字段              | 说明               |
| --------------- | ---------------- |
| `id`            | 主键               |
| `email`         | 唯一邮箱             |
| `is_pro`        | `0` FREE，`1` PRO |
| `created_at`    | 创建时间             |
| `last_login_at` | 最近登录时间           |


首次启动会通过 SQLAlchemy `create_all` 自动建表；数据库文件默认 `./users.db`。

---

## API 一览

除特别说明外，JSON 响应均包含 `success` 字段。


| 方法     | 路径                           | 说明                                            |
| ------ | ---------------------------- | --------------------------------------------- |
| `GET`  | `/`                          | 返回单页 `static/index.html`                      |
| `POST` | `/api/auth/send-magic-link`  | Body: `{"email":"..."}`，发送魔法链接                |
| `GET`  | `/api/auth/verify?token=...` | 校验 token，`302` 跳转 `/`，Set-Cookie `session_id` |
| `GET`  | `/api/user/me`               | 需 Cookie `session_id`；未登录 `401`               |
| `POST` | `/api/user/upgrade-to-pro`   | Body: `{"order_id":"..."}`，模拟升级为 PRO          |
| `POST` | `/api/auth/logout`           | 登出，删除 session 与 Cookie                        |


**HTTP 状态码约定（节选）：**

- `200`：业务成功  
- `302`：魔法链接验证成功后的重定向  
- `400`：参数错误（如邮箱格式、无效 token）  
- `401`：未登录  
- `500`：邮件发送失败等服务端错误  
- `503`：Redis 等依赖不可用时的兜底

---

## 支付现状说明（模拟 vs Paddle）

为避免误解，这里单独说明当前版本的支付能力边界：

### 1) 当前已实现：模拟支付（可用）

- 接口：`POST /api/user/upgrade-to-pro`
- 前置条件：用户已登录（需有效 `session_id`）
- 入参：`order_id`（任意字符串）
- 行为：直接将当前用户 `is_pro` 更新为 `1`
- 备注：不校验订单真伪、不请求第三方支付、不落订单表

### 2) 当前未实现：真实 Paddle 支付（未接入）

- `.env` 中的 `PADDLE_API_URL` / `PADDLE_API_KEY` / `PADDLE_WEBHOOK_SECRET` 目前仅为预留配置
- 后端尚未提供以下能力：
  - 创建 Paddle Checkout / Transaction
  - 接收并校验 Paddle Webhook 签名
  - 依据支付成功事件自动升级 PRO
  - 订单持久化与对账

### 3) 测试结论（当前版本）

- **模拟支付链路：可成功**
- **真实支付链路：未测试（因代码未接入）**

---

## 手动测试清单

建议在 Redis、SQLite、（可选）Resend 均就绪后按顺序验证：

1. **未登录**：打开首页，应显示邮箱输入与「发送魔法链接」。
2. **发送链接**：输入合法邮箱 → 接口成功；检查邮箱或控制台调试输出中的链接。
3. **点击链接**：应跳转首页并进入已登录视图；Redis 中对应 `magic:`* 已删除。
4. **刷新页面**：仍保持登录。
5. **FREE → PRO**：输入任意订单号升级 → 界面变为 PRO；刷新仍为 PRO。
6. **登出**：回到未登录视图；Redis 中 `session:`* 已删除。
7. **重复使用同一魔法链接**：应提示链接无效或已过期。

---

## 一键 `curl` 测试脚本

下面脚本可在本地一键跑完整后端流程：发送链接 → 从 Redis 取 token → 校验登录 → 查询用户 → 升级 PRO → 登出。

> 适用前提：应用已在 `http://localhost:8000` 启动，且本机 `redis-cli` 可用。

```bash
#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
EMAIL="${EMAIL:-curl-test-$(date +%s)@example.com}"
COOKIE_JAR="${COOKIE_JAR:-/tmp/login-pay-pro.cookies.txt}"

echo "== 1) 发送魔法链接 =="
curl -sS -X POST "$BASE_URL/api/auth/send-magic-link" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\"}"
echo

echo "== 2) 从 Redis 提取该邮箱对应 token =="
TOKEN="$(python3 - <<'PY' "$EMAIL"
import subprocess, sys
email = sys.argv[1]
keys = subprocess.check_output(["redis-cli", "--scan", "--pattern", "magic:*"], text=True).strip().splitlines()
for key in keys:
    value = subprocess.check_output(["redis-cli", "get", key], text=True).strip()
    if value == email:
        print(key.split(":", 1)[1])
        break
PY
)"

if [ -z "${TOKEN:-}" ]; then
  echo "未在 Redis 中找到 token，请检查发送接口返回或 Redis 状态。"
  exit 1
fi
echo "TOKEN=${TOKEN}"

echo "== 3) 校验 token（应返回 302，并写入 session cookie） =="
curl -sS -i -c "$COOKIE_JAR" "$BASE_URL/api/auth/verify?token=$TOKEN" | sed -n '1,10p'
echo

echo "== 4) 获取当前用户信息 =="
curl -sS -b "$COOKIE_JAR" "$BASE_URL/api/user/me"
echo

echo "== 5) 升级为 PRO =="
curl -sS -X POST "$BASE_URL/api/user/upgrade-to-pro" \
  -H "Content-Type: application/json" \
  -b "$COOKIE_JAR" \
  -d '{"order_id":"ORDER-CURL-001"}'
echo

echo "== 6) 再次获取用户信息（is_pro 应为 true） =="
curl -sS -b "$COOKIE_JAR" "$BASE_URL/api/user/me"
echo

echo "== 7) 登出 =="
curl -sS -X POST -b "$COOKIE_JAR" "$BASE_URL/api/auth/logout"
echo

echo "== 8) 登出后再次查询（应返回未登录） =="
curl -sS -b "$COOKIE_JAR" "$BASE_URL/api/user/me"
echo

echo "完成。Cookie 文件：$COOKIE_JAR"
```

将上面的脚本保存为 `curl_e2e.sh` 后，可这样执行（指定目标地址或邮箱）：

```bash
BASE_URL="http://127.0.0.1:8000" EMAIL="your-test@example.com" bash ./curl_e2e.sh
```

---

## 常见问题（FAQ）

**Q：`send-magic-link` 返回邮件发送失败？**  
A：检查 `RESEND_API_KEY`、`FROM_EMAIL` 是否与 Resend 控制台一致；未验证域名时只能用测试收件人，可临时设置 `FORCE_TEST_RECIPIENT`。

**Q：连接 Redis 失败？**  
A：确认 `redis-cli ping` 为 `PONG`，且 `REDIS_HOST` / `REDIS_PORT` 与本地一致。

**Q：魔法链接里的域名仍是 localhost？**  
A：当前写死在发信逻辑中，上线前需改为可配置的 **公开 Base URL**（例如环境变量 `PUBLIC_BASE_URL`），并在文档与邮件模板中统一使用。

---

## 当前已知问题

以下问题不影响本地演示主流程，但会影响可维护性或生产可用性：

- **邮件发送受账号限制**：Resend 未完成域名验证时，通常只能向测试邮箱发送；当前依赖 `FORCE_TEST_RECIPIENT` 兜底。  
- **魔法链接域名写死**：邮件正文中的链接固定为 `http://localhost:8000`，无法直接适配测试/生产多环境。  
- **异常处理粒度偏粗**：部分 `except Exception` 直接兜底，缺少错误分类与可观测性（日志字段、错误码映射）。  
- **缺少自动化测试**：当前以手动验证和 `curl` 脚本为主，尚无 pytest 级别的单元测试 / 集成测试。  
- **安全策略未完全生产化**：尚未内置限流、防刷、登录告警、IP/UA 风险识别等机制。  
- **配置安全边界较弱**：未强制校验关键环境变量，容易因误配导致运行期报错。

---

## 后续完善方向

建议按“先稳定、后扩展”的顺序推进：

1. **配置与环境分层**
  - 引入 `PUBLIC_BASE_URL` 统一生成邮件链接。  
  - 区分 `dev/test/prod` 配置模板，增加启动时配置自检。
2. **认证链路增强**
  - 增加发送频率限制（邮箱/IP 双维度）。  
  - 对 token 发送与校验增加审计日志（脱敏邮箱、请求来源、结果）。  
  - 增加会话管理策略（多端会话、主动失效、异地提醒）。
3. **支付链路接入（Paddle）**
  - 对接 Checkout，完成真实订单创建与回调处理。  
  - 使用 `PADDLE_WEBHOOK_SECRET` 做签名校验。  
  - PRO 升级改为“支付成功事件驱动”，替换当前模拟升级接口。
4. **测试与质量保障**
  - 建立 pytest 用例：邮箱校验、token 一次性、session 刷新、升级与登出。  
  - 增加关键接口的集成测试（含 Redis、SQLite、邮件 mock）。  
  - 在 CI 中加入 lint + test + 安全扫描。
5. **生产安全与运维**
  - 强制 HTTPS，Cookie 加 `Secure` 与合适的 `SameSite`。  
  - 接入结构化日志与告警（如 Sentry / ELK / Datadog）。  
  - 数据备份与迁移方案（SQLite -> PostgreSQL）及回滚预案。

---

## 生产环境注意事项（必读）

魔法链接与 Cookie 涉及安全边界，上线前建议至少：

- 全站 **HTTPS**，Cookie 设置 `Secure`、`SameSite`（按业务跨域需求选择）  
- 对 `/api/auth/send-magic-link` 做 **速率限制**，防止邮件轰炸  
- 轮换密钥，**不要将 `.env` 提交到版本库**  
- 将 SQLite 替换为 PostgreSQL / MySQL 等托管数据库（如需要）

---

## 项目结构

```
login-pay-pro/
├── main.py              # FastAPI 应用与路由
├── database.py          # SQLite / SQLAlchemy 模型与 CRUD
├── redis_client.py      # Redis：魔法 token 与 session
├── config.py            # 环境变量与常量（TTL 等）
├── static/
│   └── index.html       # 单页前端
├── .env                 # 本地配置（勿提交）
├── requirements.txt
├── users.db             # SQLite（运行后生成，勿提交）
└── README.md
```

---

## 许可证与用途

本项目定位为 **演示 / 教学**，商业使用前请自行完成安全审计、合规与支付对接。

如有问题，可对照仓库内《魔法链接登录系统 - 完整需求分析文档.md》与本文档一并阅读。