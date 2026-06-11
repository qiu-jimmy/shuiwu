"""
Pandoc 模式文档生成器
直接使用 Pandoc 将完整的 Markdown 文档转换为 Word
"""
from pathlib import Path
from docx import Document
from .base import BaseDocumentGenerator
from .markdown_handler import MarkdownHandler


class PandocDocumentGenerator:
    """Pandoc 模式文档生成器
    
    直接将完整的 Markdown 文档（包含所有标题和内容）转换为 Word 文档
    """
    
    @staticmethod
    def generate_document_from_markdown(markdown_content: str, output_path: str, 
                                       project_name: str = "XXX项目", quote_number: str = "", 
                                       date: str = "", logo_path: str = None):
        """直接从完整 Markdown 文档生成 Word 文档（Pandoc 模式）
        
        Args:
            markdown_content: 完整的 Markdown 格式文档内容
            output_path: 输出文件路径
            project_name: 项目名称
            quote_number: 报告编号
            date: 日期
            logo_path: logo图片路径（可选）
        """
        if not markdown_content or not markdown_content.strip():
            raise ValueError("Markdown 内容不能为空")
        
        # 检查 Pandoc 是否可用
        if not MarkdownHandler.ensure_pandoc():
            raise RuntimeError("Pandoc 不可用，无法使用 Pandoc 模式生成文档。请安装 Pandoc 或使用模板模式。")
        
        # 如果输出文件已存在，先删除
        output_file = Path(output_path)
        if output_file.exists():
            try:
                output_file.unlink()
            except Exception as e:
                pass
        
        # 使用 Pandoc 将 Markdown 转换为 docx
        generated_doc = MarkdownHandler.convert_markdown_to_docx_via_pandoc(
            markdown_content, 
            str(output_path)
        )
        
        # 设置文档基本格式
        base_gen = BaseDocumentGenerator()
        base_gen._setup_document_for_existing_doc(generated_doc)
        
        # 保存修改后的文档
        generated_doc.save(output_path)

