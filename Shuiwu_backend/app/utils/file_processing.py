"""
文件处理工具函数

这是一个跨层通用的基础设施模块，提供文件处理能力。

依赖关系：
API/Services/Agno → utils (file_processing) → agno.knowledge.reader

职责：
- 封装 agno 的文件读取能力
- 提供统一的文件处理接口
- 处理多种文件格式（PDF, DOCX, PPTX, CSV, TXT等）
"""
import asyncio
import base64
import os
import tempfile
from typing import Dict, List, Optional

from agno.media import File, Image


class FilePreprocessingService:
    """文件预处理服务，用于从文档中提取文本内容"""

    @staticmethod
    def detect_file_type(file_content: bytes, filename: str) -> str:
        """
        检测真实文件类型（基于文件头魔数）

        Args:
            file_content: 文件二进制内容
            filename: 文件名

        Returns:
            检测到的文件扩展名（如 '.docx', '.pdf' 等）
        """
        # 先检查文件扩展名
        file_ext = os.path.splitext(filename)[1].lower()

        # 如果扩展名已经明确，直接使用
        if file_ext in ['.pdf', '.xlsx', '.xls', '.pptx', '.json', '.csv']:
            return file_ext

        # 检查文件头魔数来识别真实类型
        if len(file_content) >= 4:
            header = file_content[:4]

            # ZIP 格式（DOCX, XLSX, PPTX 都是 ZIP 格式）
            if header == b'PK\x03\x04':
                # 根据扩展名优先判断，如果没有则默认为 docx
                if file_ext in ['.docx', '.xlsx', '.pptx']:
                    return file_ext
                return '.docx'  # 默认当作 DOCX 处理

            # PDF 格式
            if file_content.startswith(b'%PDF'):
                return '.pdf'

        # 默认返回原扩展名或 .txt
        return file_ext if file_ext else '.txt'

    @staticmethod
    def extract_text_from_file(file_base64: str, filename: str) -> str:
        """从文件中提取文本内容"""
        try:
            file_content = base64.b64decode(file_base64)

            # 调试：打印文件信息
            # print(f"\n[文件处理] 文件名: {filename}")
            # print(f"[文件处理] 解码后文件大小: {len(file_content)} 字节")

            # 检测真实文件类型
            detected_ext = FilePreprocessingService.detect_file_type(file_content, filename)
            file_ext = detected_ext

            # print(f"[文件处理] 检测到文件类型: {file_ext}")

            # 创建临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
                tmp.write(file_content)
                temp_path = tmp.name

            # print(f"[文件处理] 临时文件路径: {temp_path}")

            # 验证文件是否正确写入
            if not os.path.exists(temp_path):
                print(f"[错误] 临时文件未创建: {temp_path}")
                return f"[错误] 临时文件未创建"

            actual_size = os.path.getsize(temp_path)
            # print(f"[文件处理] 实际文件大小: {actual_size} 字节")

            if actual_size == 0:
                print(f"[错误] 临时文件为空!")
                return f"[错误] 文件内容为空"

            try:
                # 根据文件类型选择对应的 reader
                if file_ext == ".pdf":
                    # 对于 PDF，直接使用 Qwen-VL-OCR 处理（优先，更准确）
                    from app.utils.pdf_to_qwen_ocr import ocr_pdf_file_sync

                    # 直接调用 Qwen-VL-OCR，不再尝试常规 reader
                    text_content = ocr_pdf_file_sync(temp_path, model_id="qwen-vl-ocr")

                    # 如果 Qwen-VL-OCR 返回空，说明确实无法识别
                    if not text_content or not text_content.strip():
                        text_content = f"[错误] 无法从 PDF {filename} 提取文本内容"

                    # PDF 已处理完毕，直接返回结果
                    return text_content

                if file_ext in [".txt", ".md"]:
                    from agno.knowledge.reader.text_reader import TextReader
                    reader = TextReader()
                elif file_ext == ".csv":
                    from agno.knowledge.reader.csv_reader import CSVReader
                    reader = CSVReader()
                elif file_ext in [".xlsx", ".xls"]:
                    # 使用自定义 Excel Reader，解决 xlsx 二进制格式编码问题
                    from app.utils.excel_reader import create_excel_reader
                    reader = create_excel_reader()
                elif file_ext == ".docx":
                    # .docx 是基于ZIP的XML格式，使用 DocxReader
                    from agno.knowledge.reader.docx_reader import DocxReader
                    reader = DocxReader()
                elif file_ext == ".doc":
                    # .doc 是旧的二进制格式（OLE格式），使用 DocReader（基于Unstructured）
                    from app.utils.doc_reader import DocReader
                    reader = DocReader()
                elif file_ext == ".pptx":
                    from agno.knowledge.reader.pptx_reader import PPTXReader
                    reader = PPTXReader()
                elif file_ext == ".json":
                    from agno.knowledge.reader.json_reader import JSONReader
                    reader = JSONReader()
                else:
                    # 默认使用文本读取器
                    from agno.knowledge.reader.text_reader import TextReader
                    reader = TextReader()

                # 读取文件内容
                # .doc 文件需要直接传递文件路径，因为 DocReader 不接受文件对象
                if file_ext == ".doc":
                    documents = reader.read(temp_path, name=filename)
                else:
                    with open(temp_path, 'rb') as f:
                        documents = reader.read(f)

                # 提取文本
                text_content = ""
                if documents:
                    if isinstance(documents, list):
                        text_content = "\n\n".join([str(doc.content) if hasattr(doc, 'content') else str(doc) for doc in documents])
                    else:
                        text_content = str(documents.content) if hasattr(documents, 'content') else str(documents)

                # 如果 PDF 文本提取失败或为空，尝试使用 OCR
                if file_ext == ".pdf" and (not documents or not text_content.strip()):
                    # print(f"[文件处理] PDF 文本提取失败，尝试使用 OCR 处理...")
                    text_content = FilePreprocessingService._ocr_pdf_file(temp_path)

                # 打印 PDF 解析结果（用于调试）
                # print(f"\n{'='*60}")
                # print(f"PDF 文件解析: {filename}")
                # print(f"{'='*60}")
                # print(f"提取到的文档数量: {len(documents) if isinstance(documents, list) else 1}")
                # print(f"提取到的文本长度: {len(text_content)} 字符")
                # print(f"前 500 字符预览:\n{text_content[:500]}")
                # print(f"{'='*60}\n")

                return text_content
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        except Exception as e:
            print(f"提取文档文本失败: {e}")
            return f"[无法解析文件 {filename}，错误: {str(e)}]"

    @staticmethod
    def _ocr_pdf_file(pdf_path: str) -> str:
        """优先使用 Qwen-VL-OCR 处理扫描版 PDF"""
        try:
            # 优先使用 Qwen-VL-OCR 直接处理整个 PDF（更准确）
            from app.utils.pdf_to_qwen_ocr import ocr_pdf_file_sync

            print(f"[OCR] 使用 Qwen-VL-OCR 直接处理 PDF...")
            result_text = ocr_pdf_file_sync(pdf_path, model_id="qwen-vl-ocr")
            print(f"[OCR] Qwen-VL-OCR 处理完成，总文本长度: {len(result_text)}")
            return result_text

        except ImportError:
            error_msg = f"Qwen-VL-OCR 处理失败: 需要 PyMuPDF: pip install PyMuPDF"
            print(f"[OCR] {error_msg}")
            return f"[错误] {error_msg}"
        except Exception as e:
            import traceback
            error_msg = f"Qwen-VL-OCR 处理失败: {e}\n{traceback.format_exc()}"
            print(f"[OCR] {error_msg}")
            return f"[错误] {error_msg}"

    @staticmethod
    async def preprocess_files_async(files_data: Optional[List[Dict[str, str]]]) -> Optional[str]:
        """
        异步预处理多个文件，返回合并的文本内容

        使用 asyncio.to_thread 将同步的文件处理操作放到线程池中执行，
        避免阻塞事件循环
        """
        if not files_data:
            return None

        texts = []
        for file_data in files_data:
            filename = file_data.get("filename", "未知文件")
            file_base64 = file_data.get("file_base64", "")
            if file_base64:
                # 将同步的文件处理操作放到线程池中执行
                text = await asyncio.to_thread(
                    FilePreprocessingService.extract_text_from_file,
                    file_base64,
                    filename
                )
                if text:
                    texts.append(f"=== {filename} ===\n{text}")

        return "\n\n".join(texts) if texts else None

    @staticmethod
    def preprocess_files(files_data: Optional[List[Dict[str, str]]]) -> Optional[str]:
        """
        预处理多个文件，返回合并的文本内容（同步版本，兼容旧代码）

        注意：此方法是同步的，会阻塞事件循环。
        建议使用 preprocess_files_async 代替。
        """
        if not files_data:
            return None

        texts = []
        for file_data in files_data:
            filename = file_data.get("filename", "未知文件")
            file_base64 = file_data.get("file_base64", "")
            if file_base64:
                text = FilePreprocessingService.extract_text_from_file(file_base64, filename)
                if text:
                    texts.append(f"=== {filename} ===\n{text}")

        return "\n\n".join(texts) if texts else None


def process_base64_images(images_data: Optional[List[Dict[str, str]]]) -> Optional[List[Image]]:
    """
    处理 base64 图片数据（用于 Agent）

    Args:
        images_data: 图片数据列表，每个元素包含 filename 和 file_base64
                     例如: [{"filename": "image.jpg", "file_base64": "base64编码内容"}]

    Returns:
        处理后的图片列表
    """
    if not images_data:
        return None

    images = []
    import base64
    for img_data in images_data:
        try:
            # 获取 file_base64 字段
            base64_content = img_data.get("file_base64", "")

            if not base64_content:
                print(f"警告: 图片数据缺少 file_base64 字段: {img_data.get('filename', '未知')}")
                continue

            # 移除可能存在的 data URL 前缀
            if "," in base64_content and base64_content.startswith("data:"):
                base64_content = base64_content.split(",", 1)[1]

            # Agent 直接使用 Image.content，期望是原始图片二进制数据
            # 所以需要 base64.b64decode() 得到实际图片
            content = base64.b64decode(base64_content)

            image = Image(content=content)
            images.append(image)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"处理图片失败: {e}", exc_info=True)
            print(f"处理图片失败: {e}")

    return images if images else None

