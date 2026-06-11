"""
批量使用 OCR 上传 PDF 文档到知识库 kb_user_268_3480c9e3

功能：
1. 使用 PaddleOCR 进行文字识别（处理扫描版 PDF）
2. 多重检查避免重复上传
3. 批量上传文档到 OSS、数据库和知识库

依赖安装：
pip install paddleocr paddlepaddlepillow pymupdf
"""

import os
import sys
import io
import threading
import tempfile
from pathlib import Path
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# Windows 控制台编码设置
if sys.platform == "win32":
    import io as sys_io
    sys.stdout = sys_io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载环境变量
from dotenv import load_dotenv
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"[OK] 已加载环境变量文件: {env_path}")
else:
    print(f"[!] 警告: .env 文件不存在: {env_path}")

from app.services.knowledge.knowledge_service import knowledge_service
from app.services.files.files_service import files_service

# ==================== OCR 配置区域 ====================

# 禁用 ppocr 的详细日志
import logging
logging.getLogger("ppocr").setLevel(logging.WARNING)
logging.getLogger("paddle").setLevel(logging.WARNING)

# 全局锁，确保只初始化一次
_ocr_init_lock = threading.Lock()
_ocr_instance = None


class PaddleOCRProcessor:
    """PaddleOCR 文字识别处理器"""

    def __init__(self, use_gpu: bool = False, lang: str = "ch"):
        """初始化 PaddleOCR 处理器

        Args:
            use_gpu: 是否使用 GPU（默认 False，使用 CPU）
            lang: 语言模式，"ch" 表示中英文混合，"en" 表示英文
        """
        self.use_gpu = use_gpu
        self.lang = lang
        self.ocr = None
        self._paddleocr_imported = False

    def _import_paddleocr(self):
        """延迟导入 PaddleOCR"""
        if self._paddleocr_imported:
            return

        # 设置环境变量以避免 GPU 注册冲突
        os.environ["FLAGS_use_mkldnn"] = "0"
        os.environ["FLAGS_cudnn_frontend_op"] = "0"

        try:
            from paddleocr import PaddleOCR
            self.PaddleOCR = PaddleOCR
            self._paddleocr_imported = True
        except ImportError:
            self.PaddleOCR = None
            self._paddleocr_imported = True
            print("[!] 警告: PaddleOCR 未安装，请运行: pip install paddleocr paddlepaddle")

    def init_ocr(self):
        """初始化 PaddleOCR"""
        global _ocr_instance

        if _ocr_instance is not None:
            self.ocr = _ocr_instance
            return

        with _ocr_init_lock:
            # 双重检查
            if _ocr_instance is not None:
                self.ocr = _ocr_instance
                return

            self._import_paddleocr()

            if self.PaddleOCR is None:
                print("[!] 警告: PaddleOCR 未安装，请运行: pip install paddleocr paddlepaddle")
                return

            try:
                # 初始化 PaddleOCR
                try:
                    # 先尝试 GPU 模式
                    self.ocr = self.PaddleOCR(
                        use_angle_cls=True,
                        lang=self.lang,
                        show_log=False
                    )
                except Exception as gpu_error:
                    # 如果 GPU 模式失败，记录警告并使用 CPU 模式
                    print(f"[!] GPU 模式初始化失败: {str(gpu_error)}, 尝试使用 CPU 模式")
                    # 强制使用 CPU
                    try:
                        import paddle
                        paddle.set_device('cpu')
                    except:
                        pass
                    self.ocr = self.PaddleOCR(
                        use_angle_cls=True,
                        lang=self.lang,
                        show_log=False
                    )

                _ocr_instance = self.ocr
                print("[OK] OCR 引擎初始化完成")
            except Exception as e:
                print(f"[!] OCR 引擎初始化失败: {str(e)}")
                self.ocr = None

    def process_pdf_with_ocr(self, pdf_path: str) -> str:
        """使用 OCR 处理 PDF 文件

        Args:
            pdf_path: PDF 文件路径

        Returns:
            识别的文本内容
        """
        # 如果 OCR 未初始化，尝试初始化
        if self.ocr is None:
            self.init_ocr()

        # 如果初始化仍然失败，抛出异常
        if self.ocr is None:
            raise Exception("OCR 引擎未初始化，请检查 PaddleOCR 是否正确安装")

        try:
            import fitz  # PyMuPDF

            doc = fitz.open(pdf_path)
            all_texts = []

            print(f"     OCR 处理: 共 {len(doc)} 页")

            for page_num in range(len(doc)):
                page = doc[page_num]

                # 首先尝试直接提取文本
                text = page.get_text()
                if text.strip():
                    all_texts.append(f"--- 第 {page_num + 1} 页 ---")
                    all_texts.append(text)
                else:
                    # 如果无法直接提取文本，使用 OCR
                    # 将页面转换为图片（2倍分辨率提高识别率）
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    img_bytes = pix.tobytes("png")

                    # 保存临时图片
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                        tmp.write(img_bytes)
                        tmp.flush()
                        temp_path = tmp.name

                    try:
                        # OCR 识别
                        result = self.ocr.ocr(temp_path)

                        if result and result[0]:
                            # 提取所有文本行
                            page_texts = []
                            for line in result[0]:
                                if line and len(line) > 1:
                                    page_texts.append(line[1][0])

                            page_text = "\n".join(page_texts)
                            all_texts.append(f"--- 第 {page_num + 1} 页 (OCR) ---")
                            all_texts.append(page_text)
                    finally:
                        # 清理临时文件
                        if os.path.exists(temp_path):
                            os.remove(temp_path)

            doc.close()
            return "\n".join(all_texts)

        except Exception as e:
            raise Exception(f"PDF OCR 处理失败: {str(e)}")

    def process_image_with_ocr(self, image_path: str) -> str:
        """使用 OCR 处理图片文件

        Args:
            image_path: 图片文件路径

        Returns:
            识别的文本内容
        """
        # 如果 OCR 未初始化，尝试初始化
        if self.ocr is None:
            self.init_ocr()

        # 如果初始化仍然失败，抛出异常
        if self.ocr is None:
            raise Exception("OCR 引擎未初始化，请检查 PaddleOCR 是否正确安装")

        try:
            result = self.ocr.ocr(image_path)

            if not result or not result[0]:
                return ""

            # 提取所有文本行
            texts = []
            for line in result[0]:
                if line and len(line) > 1:
                    texts.append(line[1][0])

            return "\n".join(texts)

        except Exception as e:
            raise Exception(f"图片 OCR 处理失败: {str(e)}")


# ==================== 配置区域 ====================

# Articles 文件夹路径
ARTICLES_DIR = r"C:\Users\yan\Downloads\咨询问答-咨询答复260130止"

# 目标知识库表名
TARGET_TABLE_NAME = "kb_user_268_0697300c"

# 用户ID（根据实际需要修改）
USER_ID = "user_2689ea75e1114ec4"

# 并发线程数
MAX_WORKERS = 5  # OCR 处理较慢，建议降低并发数

# 分块配置
CHUNKING_RULE = "recursive"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# OCR 配置
OCR_USE_GPU = False  # 是否使用 GPU（需要安装 GPU 版本的 paddlepaddle）
OCR_LANG = "ch"  # "ch" 表示中英文混合


# ==================== 工具函数 ====================

def get_all_pdf_files(folder_path: str) -> List[Path]:
    """获取文件夹下所有 .pdf 文件"""
    folder = Path(folder_path)
    if not folder.exists():
        print(f"⚠️  文件夹不存在: {folder_path}")
        return []

    files = list(folder.glob("*.pdf"))
    return files


def get_file_record_from_registry(table_name: str, filename: str) -> Optional[Dict]:
    """从 registry 的 document_ids 中获取 file_id，然后查询 business.file 表

    Args:
        table_name: 知识库表名
        filename: 文件名

    Returns:
        文件记录字典，包含 file_id, file_url 等，如果不存在返回 None
    """
    try:
        from sqlalchemy import text
        from app.infra.db import get_sync_engine

        engine = get_sync_engine()
        with engine.connect() as conn:
            # 先从 registry 的 document_ids 中获取 file_id
            registry_sql = text("""
                SELECT document_ids
                FROM knowledge.knowledge_base_registry
                WHERE table_name = :table_name
            """)
            result = conn.execute(registry_sql, {"table_name": table_name}).fetchone()

            if not result or not result[0]:
                return None

            document_ids = result[0]
            if not isinstance(document_ids, list):
                return None

            # 查找匹配的文件名，获取 file_id
            file_id = None
            for doc in document_ids:
                if isinstance(doc, dict) and doc.get('filename') == filename:
                    file_id = doc.get('file_id')
                    break

            if not file_id:
                return None

            # 用 file_id 从 business.file 表查询完整记录
            file_sql = text("""
                SELECT file_id, file_name, file_url, file_path, file_size
                FROM business.files
                WHERE file_id = :file_id AND is_deleted = FALSE
            """)
            file_record = conn.execute(file_sql, {"file_id": file_id}).fetchone()

            if file_record:
                return {
                    'file_id': file_record[0],
                    'file_name': file_record[1],
                    'file_url': file_record[2],
                    'file_path': file_record[3],
                    'file_size': file_record[4],
                }
            return None

    except Exception as e:
        print(f"查询文件记录失败: {e}")
        return None


def process_single_file(file_path: Path, ocr_processor: PaddleOCRProcessor, kb, table_name: str, stats: Dict, lock: threading.Lock, index: int) -> bool:
    """
    处理单个文件的上传

    Args:
        file_path: 文件路径
        ocr_processor: OCR 处理器
        kb: 知识库实例
        table_name: 知识库表名
        stats: 统计字典
        lock: 线程锁
        index: 文件索引

    Returns:
        是否成功
    """
    temp_txt_path = None
    try:
        filename = file_path.name

        # ============== 检查避免重复上传 ==============

        # 只检查知识库表中是否真正存在该文档的数据
        # 如果只在 document_ids 中但表中没有数据，说明之前上传失败，需要重新上传
        if knowledge_service.repository.check_document_exists(table_name, filename):
            with lock:
                stats['skipped'] += 1
            print(f"   [⊘] [{index}] {filename}: 知识库表已存在，跳过")
            return True

        # 检查是否已有文件记录（在 business.file 表中）
        existing_file_record = None
        if knowledge_service.repository.check_document_in_registry(table_name, filename):
            existing_file_record = get_file_record_from_registry(table_name, filename)
            if existing_file_record:
                print(f"   [♻] [{index}] {filename}: 复用已有文件记录，跳过OSS上传")
            else:
                print(f"   [!] [{index}] {filename}: registry已存在但file表无记录，重新上传")

        # ============== 使用 OCR 处理 PDF ==============

        print(f"   [1/3] [{index}] OCR处理: {filename}")

        try:
            # 使用 PaddleOCR 提取文本
            text_content = ocr_processor.process_pdf_with_ocr(str(file_path))

            if not text_content or not text_content.strip():
                with lock:
                    stats['failed'] += 1
                print(f"   [X] [{index}] {filename}: OCR 未能提取到文本")
                return False

            print(f"        提取文本长度: {len(text_content)} 字符")

        except Exception as e:
            with lock:
                stats['failed'] += 1
            print(f"   [X] [{index}] {filename}: OCR处理失败 - {str(e)[:100]}")
            return False

        # ============== 上传到 OSS（如果没有已有记录）=============

        file_id_to_use = None
        if not existing_file_record:
            print(f"   [2/3] [{index}] 上传到OSS")
            file_record = files_service.upload_file_from_path(
                user_id=USER_ID,
                file_path=str(file_path),
                folder_path="ocr_articles",
                kb_name=None
            )

            if not file_record:
                with lock:
                    stats['failed'] += 1
                print(f"        [X] OSS上传失败")
                return False

            file_id_to_use = file_record.get('file_id')
            file_url = file_record.get('file_url', '')
            print(f"        OSS成功 -> {file_url}")
        else:
            print(f"   [2/3] [{index}] 跳过OSS（复用已有记录）")
            file_id_to_use = existing_file_record.get('file_id')
            print(f"        复用file_id: {file_id_to_use}")

        # ============== 创建临时文本文件并上传到知识库 ==============

        print(f"   [3/3] [{index}] 上传到知识库")

        # 创建临时文本文件（使用 .txt 扩展名）
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(text_content)
            temp_txt_path = f.name

        # 直接使用 agno 的 add_content 方法添加文本内容
        try:
            from agno.knowledge.chunking.recursive import RecursiveChunking
            from agno.knowledge.chunking.fixed import FixedSizeChunking
            from agno.knowledge.reader.text_reader import TextReader

            # 创建分块策略
            if CHUNKING_RULE == "recursive":
                chunking_strategy = RecursiveChunking(chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
            else:
                chunking_strategy = FixedSizeChunking(chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)

            # 创建 TextReader
            reader = TextReader(chunking_strategy=chunking_strategy)

            # 构建元数据
            from datetime import datetime
            doc_metadata = {
                "user_id": USER_ID,
                "filename": filename,
                "source": str(file_path),
                "ocr_processed": True,
                "chunking_rule": CHUNKING_RULE,
                "chunk_size": CHUNK_SIZE,
                "uploaded_at": datetime.utcnow().isoformat(),
            }

            # 如果有已有文件记录，添加 file_url 到元数据
            if existing_file_record:
                doc_metadata["file_url"] = existing_file_record.get('file_url')
                doc_metadata["file_id"] = existing_file_record.get('file_id')

            # 直接添加内容到知识库
            kb.add_content(path=temp_txt_path, reader=reader, metadata=doc_metadata)

            # 只在没有已有记录时才更新 document_ids（避免重复添加）
            if not existing_file_record:
                knowledge_service._add_document_to_registry(table_name, file_id_to_use, filename)

            with lock:
                stats['success'] += 1
            print(f"        [OK] 知识库导入成功")
            return True

        except Exception as e:
            with lock:
                stats['failed'] += 1
            print(f"        [X] 知识库导入失败: {str(e)[:100]}")
            import traceback
            traceback.print_exc()
            return False

    except Exception as e:
        with lock:
            stats['failed'] += 1
        print(f"   [X] [{index}] {file_path.name}: {type(e).__name__}: {str(e)[:100]}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理临时文件
        if temp_txt_path and os.path.exists(temp_txt_path):
            try:
                os.remove(temp_txt_path)
            except:
                pass


def batch_upload_ocr_files() -> Dict[str, int]:
    """批量使用 OCR 上传 PDF 文件"""
    stats = {
        "total": 0,
        "success": 0,
        "failed": 0,
        "skipped": 0,
    }
    lock = threading.Lock()

    try:
        # ============== 初始化 OCR 处理器 ==============
        print(f"\n{'='*60}")
        print(f"初始化 OCR 引擎 (PaddleOCR)")
        print(f"{'='*60}")

        ocr_processor = PaddleOCRProcessor(use_gpu=OCR_USE_GPU, lang=OCR_LANG)
        ocr_processor.init_ocr()

        if ocr_processor.ocr is None:
            print("[X] OCR 引擎初始化失败，请检查 PaddleOCR 安装")
            return stats

        # ============== 获取知识库实例 ==============
        print(f"\n{'='*60}")
        print(f"获取知识库实例: {TARGET_TABLE_NAME}")
        print(f"{'='*60}")

        # 从 registry 获取知识库信息
        kb_info = knowledge_service.repository.get_knowledge_base_registry(TARGET_TABLE_NAME)

        if not kb_info:
            print(f"[X] 知识库 {TARGET_TABLE_NAME} 不存在于注册表中")
            return stats

        kb_name = kb_info.get('kb_name')
        kb_user_id = kb_info.get('user_id')
        embedder_model = kb_info.get('embedder_model', 'text-embedding-3-small')

        print(f"[OK] 找到知识库:")
        print(f"     表名: {TARGET_TABLE_NAME}")
        print(f"     知识库名: {kb_name}")
        print(f"     用户ID: {kb_user_id}")
        print(f"     嵌入模型: {embedder_model}")

        # 加载知识库实例
        kb = knowledge_service.get_or_load_knowledge(
            user_id=kb_user_id,
            kb_name=kb_name,
            embedder_model=embedder_model
        )

        # ============== 获取所有文件 ==============
        print(f"\n{'='*60}")
        print(f"扫描文件: {ARTICLES_DIR}")
        print(f"{'='*60}")

        files = get_all_pdf_files(ARTICLES_DIR)
        print(f"找到 {len(files)} 个 .pdf 文件")

        if not files:
            print("[!] 没有找到任何 .pdf 文件")
            return stats

        stats['total'] = len(files)

        # ============== 开始批量上传 ==============
        print(f"\n{'='*60}")
        print(f"开始批量 OCR 上传")
        print(f"{'='*60}")
        print(f"并发线程数: {MAX_WORKERS}")
        print(f"分块规则: {CHUNKING_RULE}, 大小: {CHUNK_SIZE}, 重叠: {CHUNK_OVERLAP}")
        print(f"OCR 模式: {'GPU' if OCR_USE_GPU else 'CPU'}, 语言: {OCR_LANG}")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(
                    process_single_file,
                    file_path, ocr_processor, kb, TARGET_TABLE_NAME, stats, lock, idx + 1
                ): file_path
                for idx, file_path in enumerate(files)
            }

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    with lock:
                        stats['failed'] += 1
                    print(f"   [X] {futures[future].name}: 未知错误 - {str(e)}")

    except Exception as e:
        print(f"\n[X] 批量上传失败: {str(e)}")
        import traceback
        traceback.print_exc()

    return stats


def main():
    """主函数"""
    print("="*80)
    print("OCR 批量上传工具 (PaddleOCR)")
    print("="*80)

    # 检查目录
    if not os.path.exists(ARTICLES_DIR):
        print(f"[X] 目录不存在: {ARTICLES_DIR}")
        return

    print(f"\n[DIR] 目标目录: {ARTICLES_DIR}")
    print(f"[KB]  目标知识库表: {TARGET_TABLE_NAME}")
    print(f"[USER] 用户ID: {USER_ID}")

    # 执行批量上传
    stats = batch_upload_ocr_files()

    # 打印统计信息
    print(f"\n{'='*60}")
    print(f"上传统计:")
    print(f"  总计: {stats['total']} 个文件")
    print(f"  成功: {stats['success']} 个")
    print(f"  失败: {stats['failed']} 个")
    print(f"  跳过: {stats['skipped']} 个")
    print(f"{'='*60}")

    print("\n[OK] 批量上传完成！")


if __name__ == "__main__":
    main()
