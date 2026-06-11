"""知识库工具函数

提供知识库相关的通用工具函数，包括：
- 文档读取器创建
- 文档分块配置
- 文件扩展名处理
"""
import os
from typing import Optional, Tuple

from agno.knowledge.chunking.fixed import FixedSizeChunking
from agno.knowledge.chunking.recursive import RecursiveChunking
from agno.knowledge.chunking.semantic import SemanticChunking


def create_chunking_reader(
    file_extension: str,
    chunking_rule: str = "fixed_size",
    chunk_size: int = 5000,
    chunk_overlap: int = 200,
    embedder=None,
):
    """创建带分块功能的文档读取器
    
    Args:
        file_extension: 文件扩展名
        chunking_rule: 分块规则，"fixed_size" 或 "recursive"
        chunk_size: 分块大小
        chunk_overlap: 分块重叠大小
        embedder: 嵌入器实例（用于某些分块策略）
        
    Returns:
        配置好的文档读取器
    """
    # 根据分块规则创建分块策略
    if chunking_rule == "semantic":
        # 语义分块需要 embedder
        chunking_strategy = SemanticChunking(embedder=embedder, chunk_size=chunk_size)
    elif chunking_rule == "recursive":
        chunking_strategy = RecursiveChunking(chunk_size=chunk_size, overlap=chunk_overlap)
    else:
        # 默认使用固定大小分块
        chunking_strategy = FixedSizeChunking(chunk_size=chunk_size, overlap=chunk_overlap)

    # 根据文件扩展名创建对应的 Reader，并注入分块策略
    ext = file_extension.lower()
    if ext == ".pdf":
        # 使用增强版PDF读取器（支持多库回退和OCR）
        from app.utils.enhanced_pdf_reader import EnhancedPDFReader

        return EnhancedPDFReader(chunking_strategy=chunking_strategy)
    if ext in [".txt", ".md"]:
        from agno.knowledge.reader.text_reader import TextReader

        return TextReader(chunking_strategy=chunking_strategy)
    if ext == ".csv":
        from agno.knowledge.reader.csv_reader import CSVReader

        return CSVReader(chunking_strategy=chunking_strategy)
    if ext in [".xlsx", ".xls"]:
        # 使用自定义 Excel Reader，解决 xlsx 二进制格式编码问题
        from app.utils.excel_reader import create_excel_reader

        return create_excel_reader(chunking_strategy=chunking_strategy)
    if ext == ".docx":
        from agno.knowledge.reader.docx_reader import DocxReader

        return DocxReader(chunking_strategy=chunking_strategy)
    if ext == ".doc":
        # 使用 Unstructured 解析旧版 DOC 文件
        from app.utils.doc_reader import DocReader

        return DocReader(chunking_strategy=chunking_strategy)
    if ext == ".pptx":
        from agno.knowledge.reader.pptx_reader import PPTXReader

        return PPTXReader(chunking_strategy=chunking_strategy)
    if ext == ".json":
        from agno.knowledge.reader.json_reader import JSONReader

        return JSONReader(chunking_strategy=chunking_strategy)

    # 默认使用文本读取器
    from agno.knowledge.reader.text_reader import TextReader

    return TextReader(chunking_strategy=chunking_strategy)


def parse_table_name(table_name: str) -> Tuple[str, str]:
    """从表名解析用户ID和知识库名称
    
    Args:
        table_name: 表名，格式为 "kb_{user_id}_{kb_name}"
        
    Returns:
        (user_id, kb_name) 元组
    """
    parts = table_name.split("_", 2)
    if len(parts) >= 3:
        return parts[1], parts[2]
    else:
        return "unknown", table_name


def build_table_name(user_id: str, kb_name: str) -> str:
    """构建知识库表名

    Args:
        user_id: 用户ID
        kb_name: 知识库名称

    Returns:
        表名，格式为 "kb_{user_id}_{short_hash}"

        使用哈希避免 PostgreSQL 标识符 63 字节限制：
        - 中文表名在 UTF-8 下每个字符占 3 字节
        - 索引名格式: idx_{table_name}_column_name
        - 为避免超限，表名控制在 40 字节以内
    """
    import hashlib

    # 使用 MD5 哈希生成短表名（取前 8 位）
    # MD5 足够避免碰撞，且 16 进制字符每字符只占 1 字节
    hash_input = f"{user_id}_{kb_name}".encode('utf-8')
    short_hash = hashlib.md5(hash_input).hexdigest()[:8]

    # 表名格式: kb_{user_id前8位}_{hash}
    # user_id 也可能很长，截取前 8 位
    user_prefix = user_id[:8] if len(user_id) > 8 else user_id

    return f"kb_{user_prefix}_{short_hash}"

