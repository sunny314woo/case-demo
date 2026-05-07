# 导入操作系统相关功能模块，用于读取环境变量
import os
# 导入类型提示工具，用于定义字典类型注解
from typing import Dict

# 导入环境变量加载工具，用于读取 .env 文件中的配置
from dotenv import load_dotenv
# 导入 FastAPI 核心框架，用于构建 Web 服务
from fastapi import FastAPI, Form, Request
# 导入 HTML 响应类，用于返回网页内容
from fastapi.responses import HTMLResponse
# 导入模板引擎，用于渲染 HTML 页面
from fastapi.templating import Jinja2Templates
# 导入 OpenAI 客户端，用于对接大模型 API
from openai import OpenAI

# 加载项目根目录下的 .env 环境变量文件
load_dotenv()

# 创建 FastAPI 应用实例，设置应用标题
app = FastAPI(title="DeepSeek Teaching Demo")
# 初始化模板引擎，指定 HTML 模板存放目录为 templates
templates = Jinja2Templates(directory="templates")

# 定义写作风格选项字典，key 为风格名称，value 为风格描述
STYLE_OPTIONS: Dict[str, str] = {
    "正式": "语言规范、逻辑清楚、适合书面表达",
    "小学生": "句子短一些、词语简单一些、像小学生写作",
    "高考作文": "语言流畅、有文采、结构完整，像高考作文片段",
    "鲁迅风": "文字较为冷峻，善用讽刺与对比，但避免生硬模仿",
}

# 定义功能模式选项字典，key 为模式标识，value 为模式名称
MODE_OPTIONS: Dict[str, str] = {
    "rewrite": "文本改写",
    "style_generate": "风格生成",
}

# 设置默认的输入文本，当用户未输入内容时使用
DEFAULT_TEXT = "春天到了，校园里的花开了，同学们在操场上活动，整个学校很热闹。"


def build_default_prompt(mode: str, source_text: str, style: str) -> str:
    """根据当前模式、原文和风格，生成默认 Prompt 模板。"""
    # 获取选中风格对应的描述信息
    style_desc = STYLE_OPTIONS.get(style, style)
    # 清理用户输入的文本，为空则使用默认文本
    clean_text = source_text.strip() or DEFAULT_TEXT

    # 判断是否为【风格生成】模式
    if mode == "style_generate":
        return (
            "你是一名语文写作助手。\n"
            f"请围绕下面主题，生成一段“{style}”风格的中文内容。\n"
            f"风格要求：{style_desc}\n"
            "要求：\n"
            "1. 内容通顺自然\n"
            "2. 字数控制在120字左右\n"
            "3. 不要分点，直接输出正文\n"
            f"主题：{clean_text}"
        )

    # 默认执行【文本改写】模式
    return (
        "你是一名语文写作助手。\n"
        f"请把下面这段文字改写成“{style}”风格。\n"
        f"风格要求：{style_desc}\n"
        "要求：\n"
        "1. 保留原意\n"
        "2. 语言更符合指定风格\n"
        "3. 直接输出改写后的结果，不要解释\n"
        f"原文：{clean_text}"
    )


def call_deepseek(prompt: str) -> str:
    """调用 DeepSeek API，返回模型生成的文本结果。"""
    # 从环境变量中获取 DeepSeek API Key
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    # 校验 API Key 是否存在，不存在则返回提示信息
    if not api_key:
        return "还没有配置 DEEPSEEK_API_KEY，请先在环境变量或 .env 文件中设置。"

    # 从环境变量中获取 API 地址，无配置则使用默认地址
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()
    # 从环境变量中获取模型名称，无配置则使用默认模型
    model_name = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()

    # 创建 OpenAI 兼容格式的 API 客户端
    client = OpenAI(api_key=api_key, base_url=base_url)
    # 发送请求调用大模型
    response = client.chat.completions.create(
        model=model_name,  # 指定使用的模型
        messages=[
            {"role": "system", "content": "你是一个中文写作教学助手。"},  # 系统角色设定
            {"role": "user", "content": prompt},  # 用户输入的提示词
        ],
        temperature=0.8,  # 控制生成内容的随机性
        max_tokens=512,   # 限制生成内容的最大长度
    )
    # 返回模型生成的结果内容，为空则返回空字符串
    return response.choices[0].message.content or ""


def build_page_data(
    source_text: str = DEFAULT_TEXT,
    style: str = "正式",
    mode: str = "rewrite",
    prompt: str = "",
    result: str = "",
    error_message: str = "",
) -> Dict[str, str]:
    """统一准备页面渲染数据，避免路由函数里重复拼装字典。"""
    # 处理输入文本，为空则使用默认值
    source_text = source_text.strip() or DEFAULT_TEXT
    # 校验并修正风格参数，非法值则使用默认风格
    style = style if style in STYLE_OPTIONS else "正式"
    # 校验并修正模式参数，非法值则使用默认模式
    mode = mode if mode in MODE_OPTIONS else "rewrite"
    # 处理提示词，为空则自动生成默认提示词
    prompt = prompt.strip() or build_default_prompt(mode, source_text, style)

    # 组装并返回渲染页面需要的所有数据
    return {
        "source_text": source_text,
        "style": style,
        "mode": mode,
        "prompt": prompt,
        "result": result,
        "error_message": error_message,
        "style_options": STYLE_OPTIONS,
        "mode_options": MODE_OPTIONS,
    }


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """渲染首页，展示默认示例文本和 Prompt 模板。"""
    # 构建页面默认数据
    page_data = build_page_data()
    # 渲染 index.html 模板并返回给前端
    return templates.TemplateResponse("index.html", {"request": request, **page_data})


@app.post("/generate", response_class=HTMLResponse)
async def generate(
    request: Request,
    source_text: str = Form(""),  # 接收前端表单提交的原文
    style: str = Form("正式"),     # 接收前端表单提交的风格选项
    mode: str = Form("rewrite"),   # 接收前端表单提交的模式选项
    prompt: str = Form(""),        # 接收前端表单提交的提示词
) -> HTMLResponse:
    """接收表单数据，调用 DeepSeek，再把结果返回到同一个页面。"""
    # 根据表单数据构建页面渲染数据
    page_data = build_page_data(
        source_text=source_text,
        style=style,
        mode=mode,
        prompt=prompt,
    )

    try:
        # 调用 API 生成写作结果
        result = call_deepseek(page_data["prompt"])
        # 将生成结果存入页面数据
        page_data["result"] = result
    except Exception as exc:
        # 捕获调用异常，存入错误信息
        page_data["error_message"] = f"调用失败：{exc}"

    # 渲染页面并返回结果
    return templates.TemplateResponse("index.html", {"request": request, **page_data})