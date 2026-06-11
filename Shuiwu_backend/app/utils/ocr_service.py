"""
统一OCR服务模块

支持多种OCR引擎的自动回退机制：
1. RapidOCR (优先，轻量级，无需系统依赖)
2. Tesseract OCR (需要系统安装)
3. Qwen-VL-OCR (通义千问视觉模型，作为保底方案)

使用环境变量配置：
- OCR_QWEN_VL_MODEL: 通义千问视觉模型ID (默认: qwen-vl-max)
- OCR_QWEN_VL_API_KEY: 通义千问API Key
- OCR_QWEN_VL_BASE_URL: 通义千问API地址 (默认: https://dashscope.aliyuncs.com/compatible-mode/v1)
- OCR_ENABLE_QWEN_FALLBACK: 是否启用Qwen-VL作为保底 (默认: true)
"""
import base64
import io
import os
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path

from PIL import Image as PILImage


class OCREngine:
    """OCR引擎基类"""
    name: str = "base"

    def is_available(self) -> bool:
        """检查引擎是否可用"""
        raise NotImplementedError

    def recognize(self, image_data: bytes) -> str:
        """
        识别图片中的文本

        Args:
            image_data: 图片二进制数据

        Returns:
            识别出的文本内容
        """
        raise NotImplementedError


class RapidOCREngine(OCREngine):
    """RapidOCR引擎 (轻量级，无需系统依赖)"""

    name = "rapidocr"

    def __init__(self):
        self._ocr = None

    def is_available(self) -> bool:
        try:
            from rapidocr_onnxruntime import RapidOCR
            self._ocr = RapidOCR()
            return True
        except ImportError:
            return False

    def recognize(self, image_data: bytes) -> str:
        if not self._ocr:
            raise RuntimeError("RapidOCR未初始化")

        # RapidOCR 支持直接处理图片字节数据
        result = self._ocr(image_data)

        # RapidOCR 返回格式: [[[[x1,y1],[x2,y2],[x3,y3],[x4,y4]], text, confidence], ...]
        # 或者: [[[[x1,y1],[x2,y2],[x3,y3],[x4,y4]], (text, confidence)], ...]
        if not result or not result[0]:
            return ""

        texts = []
        for item in result[0]:
            try:
                if isinstance(item, list) and len(item) >= 2:
                    # 格式1: [[[坐标]], (text, confidence)]
                    if isinstance(item[1], tuple) and len(item[1]) >= 1:
                        texts.append(str(item[1][0]))
                    # 格式2: [[[坐标]], text, confidence]
                    elif isinstance(item[1], str):
                        texts.append(item[1])
            except Exception:
                continue

        return "\n".join(texts)


class TesseractOCREngine(OCREngine):
    """Tesseract OCR引擎 (需要系统安装 tesseract)"""

    name = "tesseract"

    def __init__(self, lang: str = "chi_sim+eng"):
        self.lang = lang
        self._pytesseract = None
        self._Image = None

    def is_available(self) -> bool:
        try:
            import pytesseract
            from PIL import Image
            self._pytesseract = pytesseract
            self._Image = Image
            return True
        except ImportError:
            return False

    def recognize(self, image_data: bytes) -> str:
        if not self._pytesseract or not self._Image:
            raise RuntimeError("Tesseract未初始化")

        # 转换为PIL Image
        pil_image = self._Image.open(io.BytesIO(image_data))
        return self._pytesseract.image_to_string(pil_image, lang=self.lang)


class QwenVLOCREngine(OCREngine):
    """通义千问视觉模型OCR引擎 (作为保底方案)"""

    name = "qwen-vl-ocr"

    def __init__(self):
        self._model = None
        self._enabled = os.getenv("OCR_ENABLE_QWEN_FALLBACK", "true").lower() == "true"

    def is_available(self) -> bool:
        if not self._enabled:
            return False

        # 检查环境变量配置（支持多个来源）
        api_key = os.getenv("OCR_QWEN_VL_API_KEY") or os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            print(f"[OCR] Qwen-VL-OCR 不可用: 未配置 API Key (OCR_QWEN_VL_API_KEY, DASHSCOPE_API_KEY 或 OPENAI_API_KEY)")
            return False

        # 检查是否支持视觉模型
        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=api_key,
                base_url=os.getenv("OCR_QWEN_VL_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            self._model_id = os.getenv("OCR_QWEN_VL_MODEL", "qwen-vl-max")
            return True
        except ImportError:
            return False

    def recognize(self, image_data: bytes) -> str:
        if not self._client:
            raise RuntimeError("Qwen-VL-OCR未初始化")

        # 将图片转换为base64
        # 检测图片格式
        try:
            pil_image = PILImage.open(io.BytesIO(image_data))
            format_map = {
                "JPEG": "jpeg",
                "PNG": "png",
                "GIF": "gif",
                "BMP": "bmp",
                "WEBP": "webp"
            }
            img_format = format_map.get(pil_image.format, "png")

            # 转换为base64
            buffered = io.BytesIO()
            pil_image.save(buffered, format=img_format.upper())
            img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            data_url = f"data:image/{img_format};base64,{img_base64}"
        except Exception as e:
            # 如果格式检测失败，默认PNG
            img_base64 = base64.b64encode(image_data).decode("utf-8")
            data_url = f"data:image/png;base64,{img_base64}"

        # 调用通义千问视觉API
        response = self._client.chat.completions.create(
            model=self._model_id,
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的OCR文字识别助手。请仔细识别图片中的所有文字内容，保持原有格式和布局。只输出识别出的文字，不要添加任何解释或说明。"
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": data_url
                            }
                        },
                        {
                            "type": "text",
                            "text": "请识别这张图片中的所有文字内容。"
                        }
                    ]
                }
            ],
            temperature=0.1,  # 降低温度以获得更稳定的识别结果
            max_tokens=4096
        )

        # 提取识别结果
        if response.choices and len(response.choices) > 0:
            return response.choices[0].message.content or ""

        return ""

    def recognize_pdf(
        self,
        pdf_path: Union[str, bytes],
        dpi: int = 200
    ) -> str:
        """
        识别整个PDF文件（将PDF转换为多张图片后识别）

        注意：这是一个 CPU 密集型/阻塞型的任务。在 asyncio 环境中调用时，
        应当使用 asyncio.to_thread 包装调用，避免阻塞主事件循环。

        Args:
            pdf_path: PDF文件路径或字节数据
            dpi: PDF转图片的DPI (默认: 200)

        Returns:
            识别出的完整文本内容
        """
        import asyncio
        from app.utils.pdf_to_qwen_ocr import pdf_to_qwen_ocr

        # 同步函数内部如果要运行一个完全独立的异步流程，而且当前线程已有一个运行中的事件循环
        # 会出现 RuntimeError: asyncio.run() cannot be called from a running event loop
        # 在这种场景下最好的做法是新建一个事件循环并在线程中运行，以绝对保证不卡死当前工作线程
        try:
            try:
                loop = asyncio.get_running_loop()
                has_loop = True
            except RuntimeError:
                has_loop = False

            if has_loop:
                import concurrent.futures
                # 这里必须保留 ThreadPoolExecutor 以隔离新的事件循环环境，
                # 但不再直接 future.result() 导致线程硬阻塞（特别是如果这个外层是从 async def 中调过来的情况）。
                # 不过由于本函数是同步签名，最佳实践是在调用这个函数的地方，使用 asyncio.to_thread 进行包装调用。
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    # 在子线程中执行一个全新的 asyncio.run，确保子线程是一个干净的环境
                    future = executor.submit(
                        lambda: asyncio.run(pdf_to_qwen_ocr(pdf_path, model_id=self._model_id, dpi=dpi))
                    )
                    return future.result()
            else:
                return asyncio.run(pdf_to_qwen_ocr(pdf_path, model_id=self._model_id, dpi=dpi))
        except Exception as e:
            raise RuntimeError(f"Qwen-VL-OCR PDF识别失败: {e}")


class UnifiedOCRService:
    """统一OCR服务，支持多引擎自动回退"""

    def __init__(
        self,
        lang: str = "chi_sim+eng",
        enable_rapidocr: bool = True,
        enable_tesseract: bool = False,
        enable_qwen_fallback: Optional[bool] = None,
        preferred_engine: Optional[str] = None
    ):
        """
        初始化统一OCR服务

        Args:
            lang: OCR语言 (默认: chi_sim+eng 中英文)
            enable_rapidocr: 是否启用RapidOCR (默认: True)
            enable_tesseract: 是否启用Tesseract (默认: False)
            enable_qwen_fallback: 是否启用Qwen-VL保底 (默认: 根据环境变量)
            preferred_engine: 首选引擎 ("rapidocr", "tesseract", "qwen-vl")
        """
        self.lang = lang

        # 构建引擎回退链
        self._engines: List[OCREngine] = []
        self._available_engines: Dict[str, OCREngine] = {}

        # 初始化各引擎
        if enable_rapidocr:
            rapidocr = RapidOCREngine()
            if rapidocr.is_available():
                self._engines.append(rapidocr)
                self._available_engines["rapidocr"] = rapidocr

        if enable_tesseract:
            tesseract = TesseractOCREngine(lang=lang)
            if tesseract.is_available():
                self._engines.append(tesseract)
                self._available_engines["tesseract"] = tesseract

        # Qwen-VL作为保底方案
        qwen_enabled = enable_qwen_fallback if enable_qwen_fallback is not None else (
            os.getenv("OCR_ENABLE_QWEN_FALLBACK", "true").lower() == "true"
        )
        if qwen_enabled:
            qwen = QwenVLOCREngine()
            if qwen.is_available():
                self._engines.append(qwen)
                self._available_engines["qwen-vl"] = qwen

        # 如果指定了首选引擎，调整顺序
        if preferred_engine and preferred_engine in self._available_engines:
            engine = self._available_engines[preferred_engine]
            if engine in self._engines:
                self._engines.remove(engine)
                self._engines.insert(0, engine)

    @property
    def available_engines(self) -> List[str]:
        """获取可用的OCR引擎列表"""
        return [engine.name for engine in self._engines]

    def recognize_image(
        self,
        image_data: bytes,
        fallback: bool = True,
        engine: Optional[str] = None
    ) -> Tuple[str, Optional[str]]:
        """
        识别图片中的文本

        Args:
            image_data: 图片二进制数据
            fallback: 是否在失败时回退到下一个引擎 (默认: True)
            engine: 指定使用的引擎，None表示按优先级自动选择

        Returns:
            (识别出的文本, 使用的引擎名称)

        Raises:
            RuntimeError: 当所有引擎都失败时
        """
        if engine and engine in self._available_engines:
            # 使用指定引擎
            selected_engine = self._available_engines[engine]
            try:
                text = selected_engine.recognize(image_data)
                if text and text.strip():
                    return text.strip(), engine
                else:
                    return "", engine
            except Exception as e:
                if not fallback:
                    raise RuntimeError(f"OCR引擎 {engine} 识别失败: {e}")
                return "", None

        # 按优先级尝试各引擎
        last_error = None
        for ocr_engine in self._engines:
            try:
                text = ocr_engine.recognize(image_data)
                if text and text.strip():
                    return text.strip(), ocr_engine.name
            except Exception as e:
                last_error = e
                continue

        # 所有引擎都失败
        error_msg = f"所有OCR引擎都失败"
        if last_error:
            error_msg += f"。最后错误: {last_error}"
        raise RuntimeError(error_msg)

    def recognize_image_file(
        self,
        image_path: Union[str, Path],
        fallback: bool = True,
        engine: Optional[str] = None
    ) -> Tuple[str, Optional[str]]:
        """
        识别图片文件中的文本

        Args:
            image_path: 图片文件路径
            fallback: 是否在失败时回退到下一个引擎
            engine: 指定使用的引擎

        Returns:
            (识别出的文本, 使用的引擎名称)
        """
        with open(image_path, 'rb') as f:
            image_data = f.read()
        return self.recognize_image(image_data, fallback=fallback, engine=engine)

    def recognize_pdf_file(
        self,
        pdf_path: Union[str, Path],
        engine: Optional[str] = None,
        dpi: int = 200,
    ) -> Tuple[str, Optional[str]]:
        """
        识别整个PDF文件中的文本（将PDF转换为多张图片后识别）

        Args:
            pdf_path: PDF文件路径
            engine: 指定使用的OCR引擎，如果指定了"qwen-vl"则使用Qwen-VL处理PDF
            dpi: PDF转图片的DPI (默认: 200)

        Returns:
            (识别出的文本, 使用的引擎名称)
        """
        # 如果指定使用qwen-vl引擎，直接调用PDF处理方法
        if engine == "qwen-vl" and "qwen-vl" in self._available_engines:
            qwen_engine = self._available_engines["qwen-vl"]
            try:
                text = qwen_engine.recognize_pdf(str(pdf_path), dpi=dpi)
                if text and text.strip():
                    return text.strip(), "qwen-vl"
                else:
                    return "", "qwen-vl"
            except Exception as e:
                return "", None

        # 否则，按页转换后使用常规OCR引擎
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError("PDF处理需要 PyMuPDF: pip install PyMuPDF")

        doc = fitz.open(str(pdf_path))
        all_texts = []
        used_engine = None

        for page_num in range(len(doc)):
            page = doc[page_num]
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")

            # 使用常规OCR引擎识别每一页
            text, eng = self.recognize_image(img_data, fallback=True, engine=engine)
            if eng:
                used_engine = eng
            if text and text.strip():
                all_texts.append(f"--- 第 {page_num + 1} 页 ---\n{text.strip()}")

        doc.close()
        return "\n\n".join(all_texts), used_engine


# 全局单例实例
_ocr_service: Optional[UnifiedOCRService] = None


def get_ocr_service(
    lang: str = "chi_sim+eng",
    force_refresh: bool = False
) -> UnifiedOCRService:
    """
    获取统一OCR服务实例 (单例模式)

    Args:
        lang: OCR语言
        force_refresh: 是否强制重新创建实例

    Returns:
        UnifiedOCRService实例
    """
    global _ocr_service

    if _ocr_service is None or force_refresh:
        _ocr_service = UnifiedOCRService(lang=lang)

    return _ocr_service


async def recognize_image_async(
    image_data: bytes,
    engine: Optional[str] = None
) -> Tuple[str, Optional[str]]:
    """
    异步识别图片中的文本

    Args:
        image_data: 图片二进制数据
        engine: 指定使用的OCR引擎

    Returns:
        (识别出的文本, 使用的引擎名称)
    """
    import asyncio
    ocr_service = get_ocr_service()
    return await asyncio.to_thread(
        ocr_service.recognize_image,
        image_data,
        fallback=True,
        engine=engine
    )
