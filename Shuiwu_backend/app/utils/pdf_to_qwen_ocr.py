"""
PDF转图片OCR服务（使用通义千问qwen-vl-ocr模型）

将PDF文件转换为图片，然后调用通义千问视觉模型进行OCR识别。
这是合同审查模块的保底OCR方案。

使用方法：
    from app.utils.pdf_to_qwen_ocr import pdf_to_qwen_ocr
    text = await pdf_to_qwen_ocr(pdf_path_or_bytes)
"""
import base64
import io
import os
from typing import List, Tuple, Union

from openai import OpenAI


def _get_qwen_client() -> OpenAI:
    """获取通义千问API客户端"""
    api_key = os.getenv("OCR_QWEN_VL_API_KEY") or os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OCR_QWEN_VL_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "https://dashscope.aliyuncs.com/compatible-mode/v1"

    if not api_key:
        raise ValueError(
            "未配置通义千问API密钥！请在 .env 文件中设置以下任一环境变量：\n"
            "  1. OCR_QWEN_VL_API_KEY=sk-your-dashscope-key (推荐)\n"
            "  2. DASHSCOPE_API_KEY=sk-your-dashscope-key\n"
            "  3. OPENAI_API_KEY=sk-your-dashscope-key\n"
            "\n获取 API Key: https://dashscope.aliyuncs.com/dashboard"
        )

    return OpenAI(
        api_key=api_key,
        base_url=base_url,
    )


def _image_to_base64_url(image_data: bytes, image_format: str = "png") -> str:
    """将图片数据转换为base64 URL格式"""
    img_base64 = base64.b64encode(image_data).decode("utf-8")
    return f"data:image/{image_format};base64,{img_base64}"


async def ocr_image_with_qwen(image_data: bytes, model_id: str = "qwen-vl-ocr") -> str:
    """
    使用通义千问视觉模型识别单张图片

    Args:
        image_data: 图片二进制数据
        model_id: 模型ID (默认: qwen-vl-ocr)

    Returns:
        识别出的文本内容
    """
    import asyncio

    client = _get_qwen_client()

    # 转换图片为base64 URL
    image_url = _image_to_base64_url(image_data)

    # 构建请求消息
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_url
                    }
                },
                {
                    "type": "text",
                    "text": "请识别图片中的所有文字内容，按原始阅读顺序输出纯文本。要求：1) 只输出文字内容，不要包含任何HTML标签或markdown格式；2) 保持段落换行，但不要添加额外的空行；3) 标题和正文用换行分隔；4) 不要输出任何解释性文字，直接输出识别到的文本。"
                }
            ]
        }
    ]

    # 异步调用API
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=0.1,  # 降低温度获得更稳定的结果
        )
    )

    # 提取识别结果
    if response.choices and len(response.choices) > 0:
        return response.choices[0].message.content or ""

    return ""


async def pdf_to_qwen_ocr(
    pdf_input: Union[str, bytes, io.BytesIO],
    model_id: str = "qwen-vl-ocr",
    dpi: int = 200,
) -> str:
    """
    将PDF转换为图片并使用通义千问qwen-vl-ocr模型进行OCR识别

    Args:
        pdf_input: PDF输入，可以是文件路径、字节数据或BytesIO对象
        model_id: 通义千问模型ID (默认: qwen-vl-ocr)
        dpi: PDF转图片的DPI，影响图片清晰度 (默认: 200)

    Returns:
        OCR识别出的完整文本内容
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError("需要安装 PyMuPDF: pip install PyMuPDF")

    # 打开PDF
    if isinstance(pdf_input, str):
        doc = fitz.open(pdf_input)
    elif isinstance(pdf_input, bytes):
        doc = fitz.open(stream=io.BytesIO(pdf_input), filetype="pdf")
    elif isinstance(pdf_input, io.BytesIO):
        doc = fitz.open(stream=pdf_input, filetype="pdf")
    else:
        raise TypeError(f"不支持的PDF输入类型: {type(pdf_input)}")

    page_count = len(doc)
    print(f"[PDF转OCR] PDF共 {page_count} 页，开始转换...")

    # 将每页转换为图片并进行OCR
    all_texts: List[str] = []

    for page_num in range(page_count):
        page = doc[page_num]

        # 转换为图片 (使用指定DPI提高清晰度)
        mat = fitz.Matrix(dpi / 72, dpi / 72)  # 72是默认DPI
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")

        print(f"[PDF转OCR] 正在OCR第 {page_num + 1}/{page_count} 页...")

        # 调用qwen-vl-ocr进行识别
        try:
            text = await ocr_image_with_qwen(img_data, model_id)
            if text and text.strip():
                all_texts.append(f"--- 第 {page_num + 1} 页 ---\n{text.strip()}")
                print(f"[PDF转OCR] 第 {page_num + 1} 页识别成功，文本长度: {len(text)}")
            else:
                print(f"[PDF转OCR] 第 {page_num + 1} 页识别结果为空")
        except Exception as e:
            print(f"[PDF转OCR] 第 {page_num + 1} 页识别失败: {e}")
            # 继续处理下一页，不中断整个流程
            all_texts.append(f"--- 第 {page_num + 1} 页 ---\n[OCR识别失败: {str(e)}]")

    doc.close()

    result = "\n\n".join(all_texts)
    return result


async def pdf_to_qwen_ocr_with_retry(
    pdf_input: Union[str, bytes, io.BytesIO],
    model_id: str = "qwen-vl-ocr",
    max_retries: int = 2,
    dpi: int = 200,
) -> Tuple[str, bool]:
    """
    将PDF转换为图片并使用qwen-vl-ocr进行识别（支持重试）

    Args:
        pdf_input: PDF输入
        model_id: 通义千问模型ID
        max_retries: 最大重试次数
        dpi: PDF转图片的DPI

    Returns:
        (识别文本, 是否全部成功)
    """
    last_error = None
    failed_pages = []

    try:
        import fitz
    except ImportError:
        raise ImportError("需要安装 PyMuPDF: pip install PyMuPDF")

    # 打开PDF
    if isinstance(pdf_input, str):
        doc = fitz.open(pdf_input)
    elif isinstance(pdf_input, bytes):
        doc = fitz.open(stream=io.BytesIO(pdf_input), filetype="pdf")
    elif isinstance(pdf_input, io.BytesIO):
        doc = fitz.open(stream=pdf_input, filetype="pdf")
    else:
        raise TypeError(f"不支持的PDF输入类型: {type(pdf_input)}")

    page_count = len(doc)
    all_texts: List[str] = []

    for page_num in range(page_count):
        page = doc[page_num]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")

        # 支持重试
        text = None
        for attempt in range(max_retries):
            try:
                text = await ocr_image_with_qwen(img_data, model_id)
                if text and text.strip():
                    all_texts.append(f"--- 第 {page_num + 1} 页 ---\n{text.strip()}")
                    break
                else:
                    if attempt < max_retries - 1:
                        continue
                    else:
                        all_texts.append(f"--- 第 {page_num + 1} 页 ---\n[识别结果为空]")
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    continue
                else:
                    failed_pages.append(page_num + 1)
                    all_texts.append(f"--- 第 {page_num + 1} 页 ---\n[识别失败: {str(e)}]")

    doc.close()

    result = "\n\n".join(all_texts)
    all_success = len(failed_pages) == 0

    if not all_success:
        print(f"[PDF转OCR] 警告: 以下页码识别失败: {failed_pages}")

    return result, all_success


# 便捷函数
async def ocr_pdf_file_async(pdf_path: str, model_id: str = "qwen-vl-ocr") -> str:
    """
    异步OCR识别PDF文件（便捷函数）

    Args:
        pdf_path: PDF文件路径
        model_id: 通义千问模型ID

    Returns:
        识别出的文本
    """
    return await pdf_to_qwen_ocr(pdf_path, model_id)


def ocr_pdf_file_sync(pdf_path: str, model_id: str = "qwen-vl-ocr") -> str:
    """
    同步OCR识别PDF文件（便捷函数）

    Args:
        pdf_path: PDF文件路径
        model_id: 通义千问模型ID

    Returns:
        识别出的文本
    """
    import asyncio
    return asyncio.run(pdf_to_qwen_ocr(pdf_path, model_id))
