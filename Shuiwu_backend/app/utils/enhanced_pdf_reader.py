"""增强型PDF读取器

支持多种PDF处理库的自动回退机制，能够处理：
- 复杂排版的PDF
- 扫描版PDF（需要OCR）
- 加密PDF
- 损坏的PDF文件
- 包含表格的PDF

处理优先级：
1. PyMuPDF (fitz) - 快速、功能强大
2. pdfplumber - 擅长处理表格和复杂布局
3. pypdf - 当前方案（兜底）
4. 统一OCR服务 - 处理扫描版PDF（RapidOCR -> Tesseract -> Qwen-VL）
"""

import io
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from agno.knowledge.document import Document
from agno.knowledge.reader.base import Reader as BaseReader
from agno.knowledge.types import ContentType


class EnhancedPDFReader(BaseReader):
    """增强型PDF读取器，支持多库回退"""

    def __init__(
        self,
        chunking_strategy=None,
        enable_ocr: bool = True,
        ocr_lang: str = "chi_sim+eng",
        fallback_on_error: bool = True,
        **kwargs
    ):
        """初始化增强型PDF读取器

        Args:
            chunking_strategy: 分块策略（兼容agno接口）
            enable_ocr: 是否启用OCR（处理扫描版PDF）
            ocr_lang: OCR语言，默认中英文
            fallback_on_error: 是否在出错时回退到下一个库
        """
        super().__init__(chunking_strategy=chunking_strategy, **kwargs)
        self.enable_ocr = enable_ocr
        self.ocr_lang = ocr_lang
        self.fallback_on_error = fallback_on_error

        # 检查可用的库
        self.available_readers = self._check_available_readers()

    @classmethod
    def get_supported_content_types(cls) -> List[ContentType]:
        """返回支持的文档类型"""
        return [ContentType.PDF]

    def _check_available_readers(self) -> Dict[str, bool]:
        """检查哪些PDF处理库可用"""
        readers = {
            "pymupdf": False,
            "pdfplumber": False,
            "pypdf": True,  # 默认可用
            "ocr": False,
        }

        # 检查 PyMuPDF
        try:
            import fitz  # PyMuPDF

            self.fitz = fitz
            readers["pymupdf"] = True
        except ImportError:
            pass

        # 检查 pdfplumber
        try:
            import pdfplumber

            self.pdfplumber = pdfplumber
            readers["pdfplumber"] = True
        except ImportError:
            pass

        # 检查 pypdf
        try:
            import pypdf

            self.pypdf = pypdf
            readers["pypdf"] = True
        except ImportError:
            readers["pypdf"] = False

        # 检查 OCR（使用统一OCR服务）
        if self.enable_ocr:
            try:
                from app.utils.ocr_service import get_ocr_service

                self.ocr_service = get_ocr_service()
                readers["ocr"] = True
                readers["ocr_type"] = "unified"
            except ImportError:
                pass

        return readers

    def read(
        self,
        pdf: Union[str, Path, io.BytesIO],
        name: Optional[str] = None,
        password: Optional[str] = None,
    ) -> List[Document]:
        """读取PDF文件

        Args:
            pdf: PDF文件路径、Path对象或字节流
            name: 文档名称（可选）
            password: PDF密码（可选）

        Returns:
            文档列表
        """
        # 诊断：打印传入参数类型和内容
        if isinstance(pdf, (str, Path)):
            print(f"[DEBUG] pdf参数类型: {type(pdf)}, 值: {pdf}")
        else:
            # BytesIO 对象
            try:
                size = len(pdf.read())
                pdf.seek(0)  # 重置指针
                print(f"[DEBUG] pdf参数类型: {type(pdf)}, 值: <BytesIO {size} bytes>")
            except:
                print(f"[DEBUG] pdf参数类型: {type(pdf)}, 值: <BytesIO unknown size>")

        # 首先检查PDF文件大小和页数
        # 保存原始输入用于后续处理（避免BytesIO被消耗）
        original_pdf = pdf
        pdf_for_check = pdf

        try:
            if self.available_readers.get("pymupdf"):
                if isinstance(pdf, (str, Path)):
                    # 验证文件存在且可读
                    pdf_path = str(pdf)
                    if not os.path.exists(pdf_path):
                        print(f"[ERROR] PDF文件不存在: {pdf_path}")
                        raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")

                    file_size = os.path.getsize(pdf_path)
                    print(f"[DEBUG] 打开文件前检查: 路径={pdf_path}, 大小={file_size} 字节")

                    if file_size == 0:
                        print(f"[ERROR] PDF文件为空（0字节）: {pdf_path}")
                        raise ValueError(f"PDF文件为空（0字节）: {pdf_path}")

                    # 尝试打开文件
                    doc = self.fitz.open(pdf)
                    print(f"[DEBUG] fitz.open() 成功, 页数={len(doc)}")
                else:
                    # BytesIO 处理 - 读取内容保存，避免多次读取消耗指针
                    content = pdf.read()
                    if not content or len(content) == 0:
                        print(f"[ERROR] BytesIO为空")
                        raise ValueError(f"PDF字节流为空")
                    print(f"[DEBUG] BytesIO大小: {len(content)} 字节")

                    # 创建新的BytesIO用于后续处理
                    original_pdf = io.BytesIO(content)
                    pdf_for_check = io.BytesIO(content)

                # 根据输入类型获取页数
                if isinstance(pdf, (str, Path)):
                    page_count = len(self.fitz.open(pdf))
                else:
                    # BytesIO 已经被读取并保存为 original_pdf
                    page_count = len(self.fitz.open(stream=pdf_for_check, filetype="pdf"))
                print(f"PDF 信息: {page_count} 页")

                # 检查每一页是否为空白（需要重新打开PDF）
                blank_pages = 0
                try:
                    if isinstance(pdf, (str, Path)):
                        check_doc = self.fitz.open(pdf)
                    else:
                        check_doc = self.fitz.open(stream=original_pdf, filetype="pdf")

                    for i in range(min(page_count, 5)):  # 只检查前5页
                        page = check_doc[i]
                        text = page.get_text("text").strip()
                        if not text:
                            blank_pages += 1

                    check_doc.close()

                    if blank_pages == min(page_count, 5):
                        print(f" PDF 前5页都是空白页，可能是扫描版PDF或纯图片PDF")
                except Exception as check_error:
                    print(f" 检查空白页时出错: {check_error}")
        except Exception as e:
            print(f" 无法检查PDF信息: {e}")
            import traceback
            traceback.print_exc()  # 打印完整堆栈

        # 按优先级尝试不同的读取器
        readers_to_try = []

        if self.available_readers.get("pymupdf"):
            readers_to_try.append(("pymupdf", self._read_with_pymupdf))

        if self.available_readers.get("pdfplumber"):
            readers_to_try.append(("pdfplumber", self._read_with_pdfplumber))

        if self.available_readers.get("pypdf"):
            readers_to_try.append(("pypdf", self._read_with_pypdf))

        if self.available_readers.get("ocr"):
            readers_to_try.append(("ocr", self._read_with_ocr))

        last_error = None

        for reader_name, reader_func in readers_to_try:
            try:
                print(f"尝试使用 {reader_name} 读取PDF...")
                # 使用保存的 original_pdf，避免 BytesIO 被消耗
                documents = reader_func(original_pdf, name, password)

                if documents:
                    print(f"✓ 使用 {reader_name} 成功读取PDF，共 {len(documents)} 个文档块")
                    return documents
                else:
                    print(f"✗ {reader_name} 未能提取到内容")

            except Exception as e:
                last_error = e
                print(f"✗ {reader_name} 读取失败: {str(e)}")

                if not self.fallback_on_error:
                    raise

        # 所有方法都失败
        error_msg = f"所有PDF读取方法都失败。最后错误: {str(last_error) if last_error else '未知错误'}"
        print(f"✗ {error_msg}")
        print(f" 可能的原因:")
        print(f"   1. PDF文件是空白页或损坏的文件")
        print(f"   2. PDF是扫描版但图片质量太差（模糊、分辨率低）")
        print(f"   3. PDF包含特殊字体或加密内容")
        print(f"   4. PDF文件路径或内容不正确")
        return []

    def _read_with_pymupdf(
        self,
        pdf: Union[str, Path, io.BytesIO],
        name: Optional[str] = None,
        password: Optional[str] = None,
    ) -> List[Document]:
        """使用 PyMuPDF (fitz) 读取PDF

        优点：
        - 速度快
        - 支持提取图片、表格
        - 保留元数据（作者、创建日期等）
        - 处理复杂布局能力强
        """
        if not self.available_readers.get("pymupdf"):
            raise ImportError("PyMuPDF 未安装")

        # 打开PDF
        if isinstance(pdf, (str, Path)):
            # 验证文件路径
            pdf_path = str(pdf)
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")

            file_size = os.path.getsize(pdf_path)
            if file_size == 0:
                raise ValueError(f"PDF文件为空（0字节）: {pdf_path}")

            print(f"  [pymupdf] 文件路径: {pdf_path}, 大小: {file_size} 字节")
            doc = self.fitz.open(pdf)
        else:
            # 字节流
            content = pdf.read()
            if not content or len(content) == 0:
                raise ValueError(f"PDF字节流为空")

            print(f"  [pymupdf] 字节流大小: {len(content)} 字节")
            # 创建新的 BytesIO 对象（因为 pdf.read() 后指针已移到末尾）
            doc = self.fitz.open(stream=io.BytesIO(content), filetype="pdf")

        # 处理密码
        if password and doc.needs_password:
            if not doc.authenticate(password):
                raise ValueError("PDF密码错误")

        documents = []

        try:
            for page_num in range(len(doc)):
                page = doc[page_num]

                # 提取文本
                text = page.get_text("text")  # 纯文本

                # 如果文本为空，尝试提取布局
                if not text.strip():
                    text = page.get_text("blocks")  # 按文本块提取
                    if isinstance(text, list):
                        text = "\n".join([block[4] for block in text if block[4]])

                # 提取表格（如果有）
                tables = self._extract_tables_with_pymupdf(page)

                # 构建元数据
                meta_data = {
                    "page": page_num + 1,
                    "total_pages": len(doc),
                    "source": name or str(pdf),
                }

                # 添加PDF元数据
                if doc.metadata:
                    meta_data.update(
                        {
                            "author": doc.metadata.get("author", ""),
                            "title": doc.metadata.get("title", ""),
                            "subject": doc.metadata.get("subject", ""),
                            "creator": doc.metadata.get("creator", ""),
                            "producer": doc.metadata.get("producer", ""),
                        }
                    )

                # 组合内容（只包含实际文本，不包含表格）
                content = text

                # 如果有表格，添加表格内容
                if tables:
                    for i, table in enumerate(tables):
                        content += f"\n\n表格 {i + 1}:\n{table}"

                # 只有当实际文本内容不为空时才添加文档块
                # 如果只是表格而 text 为空，不应该视为成功提取
                if content.strip():
                    documents.append(
                        Document(
                            content=content.strip(),
                            name=name or str(pdf),
                            meta_data=meta_data.copy(),
                        )
                    )

        finally:
            doc.close()

        return documents

    def _extract_tables_with_pymupdf(self, page) -> List[str]:
        """使用 PyMuPDF 提取表格"""
        tables = []

        try:
            # 查找表格（简单的基于位置的检测）
            # 注意：PyMuPDF 不直接支持表格提取，这里需要使用 find_tables
            # 如果安装了 pymupdf4llm，可以使用更强大的表格提取
            try:
                tables_data = page.find_tables()
                for table in tables_data:
                    table_content = []
                    for row in table.extract():
                        table_content.append(" | ".join([str(cell) for cell in row]))
                    tables.append("\n".join(table_content))
            except:
                pass  # 如果 find_tables 不可用，跳过表格提取

        except Exception as e:
            print(f"提取表格失败: {e}")

        return tables

    def _read_with_pdfplumber(
        self,
        pdf: Union[str, Path, io.BytesIO],
        name: Optional[str] = None,
        password: Optional[str] = None,
    ) -> List[Document]:
        """使用 pdfplumber 读取PDF

        优点：
        - 擅长处理表格
        - 处理复杂布局能力强
        - 可以精确控制文本提取区域
        """
        if not self.available_readers.get("pdfplumber"):
            raise ImportError("pdfplumber 未安装")

        # 打开PDF
        if isinstance(pdf, (str, Path)):
            # 验证文件路径
            pdf_path = str(pdf)
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
            file_size = os.path.getsize(pdf_path)
            if file_size == 0:
                raise ValueError(f"PDF文件为空（0字节）: {pdf_path}")
            print(f"  [pdfplumber] 文件路径: {pdf_path}, 大小: {file_size} 字节")
            pdf_doc = self.pdfplumber.open(pdf)
        else:
            # 字节流
            content = pdf.read()
            if not content or len(content) == 0:
                raise ValueError(f"PDF字节流为空")
            print(f"  [pdfplumber] 字节流大小: {len(content)} 字节")
            pdf_doc = self.pdfplumber.open(io.BytesIO(content))

        documents = []

        try:
            for page_num, page in enumerate(pdf_doc.pages):
                # 提取文本
                text = page.extract_text() or ""

                # 提取表格
                tables = page.extract_tables()
                table_content = ""

                if tables:
                    for i, table in enumerate(tables):
                        if table:
                            table_content += f"\n\n表格 {i + 1}:\n"
                            for row in table:
                                table_content += " | ".join(
                                    [str(cell) if cell else "" for cell in row]
                                ) + "\n"

                # 构建元数据
                meta_data = {
                    "page": page_num + 1,
                    "total_pages": len(pdf_doc.pages),
                    "source": name or str(pdf),
                    "width": page.width,
                    "height": page.height,
                }

                content = text + table_content

                if content.strip():
                    documents.append(
                        Document(
                            content=content.strip(),
                            name=name or str(pdf),
                            meta_data=meta_data.copy(),
                        )
                    )

        finally:
            pdf_doc.close()

        return documents

    def _read_with_pypdf(
        self,
        pdf: Union[str, Path, io.BytesIO],
        name: Optional[str] = None,
        password: Optional[str] = None,
    ) -> List[Document]:
        """使用 pypdf 读取PDF（当前方案的改进版）"""
        if not self.available_readers.get("pypdf"):
            raise ImportError("pypdf 未安装")

        # 打开PDF
        if isinstance(pdf, (str, Path)):
            # 验证文件路径
            pdf_path = str(pdf)
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
            file_size = os.path.getsize(pdf_path)
            if file_size == 0:
                raise ValueError(f"PDF文件为空（0字节）: {pdf_path}")
            print(f"  [pypdf] 文件路径: {pdf_path}, 大小: {file_size} 字节")
            pdf_reader = self.pypdf.PdfReader(pdf)
        else:
            # 字节流
            content = pdf.read()
            if not content or len(content) == 0:
                raise ValueError(f"PDF字节流为空")
            print(f"  [pypdf] 字节流大小: {len(content)} 字节")
            pdf_reader = self.pypdf.PdfReader(io.BytesIO(content))

        # 处理密码
        if pdf_reader.is_encrypted:
            if password:
                if not pdf_reader.decrypt(password):
                    raise ValueError("PDF密码错误")
            else:
                # 尝试空密码
                if not pdf_reader.decrypt(""):
                    raise ValueError("PDF已加密，需要密码")

        documents = []

        for page_num, page in enumerate(pdf_reader.pages):
            try:
                # 提取文本
                text = page.extract_text()

                if text and text.strip():
                    meta_data = {
                        "page": page_num + 1,
                        "total_pages": len(pdf_reader.pages),
                        "source": name or str(pdf),
                    }

                    documents.append(
                        Document(
                            content=text.strip(),
                            name=name or str(pdf),
                            meta_data=meta_data.copy(),
                        )
                    )
            except Exception as e:
                print(f"pypdf 读取第 {page_num + 1} 页失败: {e}")
                continue

        return documents

    def _read_with_ocr(
        self,
        pdf: Union[str, Path, io.BytesIO],
        name: Optional[str] = None,
        password: Optional[str] = None,
    ) -> List[Document]:
        """使用统一OCR服务读取扫描版PDF"""
        if not self.available_readers.get("ocr"):
            raise ImportError("OCR 服务未初始化")

        try:
            # 尝试使用 PyMuPDF 将PDF转换为图片，然后OCR
            if self.available_readers.get("pymupdf"):
                return self._ocr_with_pymupdf_unified(pdf, name, password)
            else:
                # 如果没有 PyMuPDF，使用 pdf2image
                return self._ocr_with_pdf2image_unified(pdf, name, password)

        except Exception as e:
            raise Exception(f"OCR读取失败: {e}")

    def _ocr_with_pymupdf_tesseract(
        self,
        pdf: Union[str, Path, io.BytesIO],
        name: Optional[str] = None,
        password: Optional[str] = None,
    ) -> List[Document]:
        """使用 PyMuPDF + Tesseract OCR 读取PDF"""
        # 打开PDF
        if isinstance(pdf, (str, Path)):
            # 验证文件路径
            pdf_path = str(pdf)
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
            file_size = os.path.getsize(pdf_path)
            if file_size == 0:
                raise ValueError(f"PDF文件为空（0字节）: {pdf_path}")
            print(f"  [ocr+tesseract] 文件路径: {pdf_path}, 大小: {file_size} 字节")
            doc = self.fitz.open(pdf)
        else:
            # 字节流
            content = pdf.read()
            if not content or len(content) == 0:
                raise ValueError(f"PDF字节流为空")
            print(f"  [ocr+tesseract] 字节流大小: {len(content)} 字节")
            doc = self.fitz.open(stream=io.BytesIO(content), filetype="pdf")

        # 处理密码
        if password and doc.needs_password:
            if not doc.authenticate(password):
                raise ValueError("PDF密码错误")

        documents = []

        try:
            for page_num in range(len(doc)):
                page = doc[page_num]

                # 将页面转换为图片
                pix = page.get_pixmap(matrix=self.fitz.Matrix(2, 2))  # 2x分辨率
                img_data = pix.tobytes("png")

                # 使用PIL打开图片
                img = self.Image.open(io.BytesIO(img_data))

                # OCR识别
                text = self.pytesseract.image_to_string(img, lang=self.ocr_lang)

                if text.strip():
                    meta_data = {
                        "page": page_num + 1,
                        "total_pages": len(doc),
                        "source": name or str(pdf),
                        "ocr": True,
                    }

                    documents.append(
                        Document(
                            content=text.strip(),
                            name=name or str(pdf),
                            meta_data=meta_data.copy(),
                        )
                    )

        finally:
            doc.close()

        return documents

    def _ocr_with_pymupdf_rapidocr(
        self,
        pdf: Union[str, Path, io.BytesIO],
        name: Optional[str] = None,
        password: Optional[str] = None,
    ) -> List[Document]:
        """使用 PyMuPDF + RapidOCR 读取PDF"""
        # 打开PDF
        if isinstance(pdf, (str, Path)):
            # 验证文件路径
            pdf_path = str(pdf)
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
            file_size = os.path.getsize(pdf_path)
            if file_size == 0:
                raise ValueError(f"PDF文件为空（0字节）: {pdf_path}")
            print(f"  [ocr+rapidocr] 文件路径: {pdf_path}, 大小: {file_size} 字节")
            doc = self.fitz.open(pdf)
        else:
            # 字节流
            content = pdf.read()
            if not content or len(content) == 0:
                raise ValueError(f"PDF字节流为空")
            print(f"  [ocr+rapidocr] 字节流大小: {len(content)} 字节")
            doc = self.fitz.open(stream=io.BytesIO(content), filetype="pdf")

        # 处理密码
        if password and doc.needs_password:
            if not doc.authenticate(password):
                raise ValueError("PDF密码错误")

        documents = []

        try:
            for page_num in range(len(doc)):
                page = doc[page_num]

                # 将页面转换为图片
                pix = page.get_pixmap(matrix=self.fitz.Matrix(2, 2))  # 2x分辨率
                img_data = pix.tobytes("png")

                # 使用 RapidOCR 识别
                # RapidOCR 返回格式可能有多种:
                # 1. [[[[x1,y1],[x2,y2],[x3,y3],[x4,y4]], (text, confidence)], ...]
                # 2. [[[[x1,y1],[x2,y2],[x3,y3],[x4,y4]], text, confidence], ...]
                result = self.rapidocr(img_data)

                if result:
                    # 提取所有识别的文本
                    texts = []
                    for item in result:
                        try:
                            # 尝试不同的格式
                            if isinstance(item, list) and len(item) >= 2:
                                # 格式 1: [[[坐标]], (text, confidence)]
                                if isinstance(item[1], tuple) and len(item[1]) >= 1:
                                    texts.append(str(item[1][0]))
                                # 格式 2: [[[坐标]], text, confidence]
                                elif isinstance(item[1], str):
                                    texts.append(item[1])
                                # 格式 3: [[[坐标]], text]
                                elif len(item) >= 2 and isinstance(item[1], str):
                                    texts.append(item[1])
                        except Exception:
                            # 跳过格式错误的项
                            continue

                    text = "\n".join(texts)

                    if text.strip():
                        meta_data = {
                            "page": page_num + 1,
                            "total_pages": len(doc),
                            "source": name or str(pdf),
                            "ocr": True,
                            "ocr_engine": "rapidocr",
                        }

                        documents.append(
                            Document(
                                content=text.strip(),
                                name=name or str(pdf),
                                meta_data=meta_data.copy(),
                            )
                        )

        finally:
            doc.close()

        return documents

    def _ocr_with_pdf2image_tesseract(
        self,
        pdf: Union[str, Path, io.BytesIO],
        name: Optional[str] = None,
        password: Optional[str] = None,
    ) -> List[Document]:
        """使用 pdf2image + Tesseract OCR 读取PDF（备用方案）"""
        try:
            from pdf2image import convert_from_path, convert_from_bytes
        except ImportError:
            raise ImportError("pdf2image 未安装，请运行: pip install pdf2image")

        # 将PDF转换为图片
        if isinstance(pdf, io.BytesIO):
            pdf_bytes = pdf.read()
            images = convert_from_bytes(pdf_bytes)
        else:
            images = convert_from_path(pdf)

        documents = []

        for page_num, img in enumerate(images):
            # OCR识别
            text = self.pytesseract.image_to_string(img, lang=self.ocr_lang)

            if text.strip():
                meta_data = {
                    "page": page_num + 1,
                    "total_pages": len(images),
                    "source": name or str(pdf),
                    "ocr": True,
                }

                documents.append(
                    Document(
                        content=text.strip(),
                        name=name or str(pdf),
                        meta_data=meta_data.copy(),
                    )
                )

        return documents

    def _ocr_with_pdf2image_rapidocr(
        self,
        pdf: Union[str, Path, io.BytesIO],
        name: Optional[str] = None,
        password: Optional[str] = None,
    ) -> List[Document]:
        """使用 pdf2image + RapidOCR 读取PDF（备用方案）"""
        try:
            from pdf2image import convert_from_path, convert_from_bytes
        except ImportError:
            raise ImportError("pdf2image 未安装，请运行: pip install pdf2image")

        # 将PDF转换为图片
        if isinstance(pdf, io.BytesIO):
            pdf_bytes = pdf.read()
            images = convert_from_bytes(pdf_bytes)
        else:
            images = convert_from_path(pdf)

        documents = []

        for page_num, img in enumerate(images):
            # 将 PIL 图片转换为字节数据
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()

            # 使用 RapidOCR 识别
            result = self.rapidocr(img_byte_arr)

            if result:
                # 提取所有识别的文本（使用与 pymupdf 相同的逻辑）
                texts = []
                for item in result:
                    try:
                        # 尝试不同的格式
                        if isinstance(item, list) and len(item) >= 2:
                            # 格式 1: [[[坐标]], (text, confidence)]
                            if isinstance(item[1], tuple) and len(item[1]) >= 1:
                                texts.append(str(item[1][0]))
                            # 格式 2: [[[坐标]], text, confidence]
                            elif isinstance(item[1], str):
                                texts.append(item[1])
                            # 格式 3: [[[坐标]], text]
                            elif len(item) >= 2 and isinstance(item[1], str):
                                texts.append(item[1])
                    except Exception:
                        # 跳过格式错误的项
                        continue

                text = "\n".join(texts)

                if text.strip():
                    meta_data = {
                        "page": page_num + 1,
                        "total_pages": len(images),
                        "source": name or str(pdf),
                        "ocr": True,
                        "ocr_engine": "rapidocr",
                    }

                    documents.append(
                        Document(
                            content=text.strip(),
                            name=name or str(pdf),
                            meta_data=meta_data.copy(),
                        )
                    )

        return documents

    def _ocr_with_pymupdf_unified(
        self,
        pdf: Union[str, Path, io.BytesIO],
        name: Optional[str] = None,
        password: Optional[str] = None,
    ) -> List[Document]:
        """使用 PyMuPDF + 统一OCR服务读取PDF"""
        # 打开PDF
        if isinstance(pdf, (str, Path)):
            # 验证文件路径
            pdf_path = str(pdf)
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
            file_size = os.path.getsize(pdf_path)
            if file_size == 0:
                raise ValueError(f"PDF文件为空（0字节）: {pdf_path}")
            print(f"  [ocr+unified] 文件路径: {pdf_path}, 大小: {file_size} 字节")
            doc = self.fitz.open(pdf)
        else:
            # 字节流
            content = pdf.read()
            if not content or len(content) == 0:
                raise ValueError(f"PDF字节流为空")
            print(f"  [ocr+unified] 字节流大小: {len(content)} 字节")
            doc = self.fitz.open(stream=io.BytesIO(content), filetype="pdf")

        # 处理密码
        if password and doc.needs_password:
            if not doc.authenticate(password):
                raise ValueError("PDF密码错误")

        documents = []

        try:
            for page_num in range(len(doc)):
                page = doc[page_num]

                # 将页面转换为图片
                pix = page.get_pixmap(matrix=self.fitz.Matrix(2, 2))  # 2x分辨率
                img_data = pix.tobytes("png")

                # 使用统一OCR服务识别
                text, engine = self.ocr_service.recognize_image(img_data, fallback=True)

                if text.strip():
                    meta_data = {
                        "page": page_num + 1,
                        "total_pages": len(doc),
                        "source": name or str(pdf),
                        "ocr": True,
                        "ocr_engine": engine,
                    }

                    documents.append(
                        Document(
                            content=text.strip(),
                            name=name or str(pdf),
                            meta_data=meta_data.copy(),
                        )
                    )

        finally:
            doc.close()

        return documents

    def _ocr_with_pdf2image_unified(
        self,
        pdf: Union[str, Path, io.BytesIO],
        name: Optional[str] = None,
        password: Optional[str] = None,
    ) -> List[Document]:
        """使用 pdf2image + 统一OCR服务读取PDF（备用方案）"""
        try:
            from pdf2image import convert_from_path, convert_from_bytes
        except ImportError:
            raise ImportError("pdf2image 未安装，请运行: pip install pdf2image")

        # 将PDF转换为图片
        if isinstance(pdf, io.BytesIO):
            pdf_bytes = pdf.read()
            images = convert_from_bytes(pdf_bytes)
        else:
            images = convert_from_path(pdf)

        documents = []

        for page_num, img in enumerate(images):
            # 将 PIL 图片转换为字节数据
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()

            # 使用统一OCR服务识别
            text, engine = self.ocr_service.recognize_image(img_byte_arr, fallback=True)

            if text.strip():
                meta_data = {
                    "page": page_num + 1,
                    "total_pages": len(images),
                    "source": name or str(pdf),
                    "ocr": True,
                    "ocr_engine": engine,
                }

                documents.append(
                    Document(
                        content=text.strip(),
                        name=name or str(pdf),
                        meta_data=meta_data.copy(),
                    )
                )

        return documents


# 创建全局实例
_enhanced_pdf_reader = None


def get_enhanced_pdf_reader(
    enable_ocr: bool = True, ocr_lang: str = "chi_sim+eng"
) -> EnhancedPDFReader:
    """获取增强型PDF读取器实例（单例模式）"""
    global _enhanced_pdf_reader

    if _enhanced_pdf_reader is None:
        _enhanced_pdf_reader = EnhancedPDFReader(
            enable_ocr=enable_ocr, ocr_lang=ocr_lang
        )

    return _enhanced_pdf_reader
