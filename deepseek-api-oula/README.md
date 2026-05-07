# DeepSeek FastAPI 教学 Demo

这是一个适合课堂演示的极简 Web Demo，用来展示：

1. 学生输入原文或主题
2. 选择写作风格
3. 观察默认 Prompt
4. 手动修改 Prompt
5. 调用 DeepSeek API 比较生成结果

## 项目结构

```text
deepseek-api-oula/
├── app.py                    # FastAPI 主程序
├── templates/
│   └── index.html            # 页面模板
├── .env.example              # 环境变量示例
├── requirements-demo.txt     # Python 依赖
├── install_demo_prereqs.sh   # openEuler 前置依赖安装脚本
└── start_demo.sh             # 启动脚本
```

## 第一步：安装依赖

```bash
chmod +x install_demo_prereqs.sh
./install_demo_prereqs.sh .
```

上面的 `.` 表示把虚拟环境和依赖装到当前项目目录。

## 第二步：配置 Key

```bash
cp .env .env
```

然后编辑 `.env`，填入你的 DeepSeek API Key。

## 第三步：启动项目

```bash
chmod +x start_demo.sh
./start_demo.sh
```

默认以稳定演示模式启动，不开启热重载。

如果你在本机调试代码，想要启用自动重载，可以手动执行：

```bash
source .venv/bin/activate
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

## 浏览器访问

如果你的 openEuler 虚拟机 IP 是 `192.168.1.20`，那么在 Windows 浏览器中访问：

```text
http://192.168.1.20:8000
```

## 关键教学点

1. `build_default_prompt()`：演示 Prompt 模板是怎么拼出来的
2. `/generate` 路由：演示表单数据如何流向 API 调用
3. `call_deepseek()`：演示如何通过 OpenAI SDK 调用 DeepSeek
4. 页面里的 Prompt 文本框：演示“Prompt 改一点，结果就会变”

## 脚本说明

1. `install_demo_prereqs.sh` 现在会显式使用虚拟环境里的 Python 安装依赖，不依赖系统的 `python` 命令别名。
2. 安装依赖时会通过命令行参数使用国内 pip 镜像，不会改写全局 `~/.pip/pip.conf`。
3. `start_demo.sh` 会自动检查 `.env` 和 `DEEPSEEK_API_KEY`，更适合课堂演示。
