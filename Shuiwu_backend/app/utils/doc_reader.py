"""DOC 文件读取器（专用于 .doc，基于 antiword）

说明：
- 仅针对传统 Word 97-2003 二进制格式的 `.doc` 文件
- 主路径：调用系统命令行工具 `antiword` 提取纯文本
- 备用路径：在没有 antiword 时，可以扩展为使用纯 Python 库做简单解析

依赖（推荐在服务器上安装）：
- 系统包：antiword  （Ubuntu/Debian: `apt-get install -y antiword`）
"""

import io
import os
import subprocess
from pathlib import Path
from typing import List, Union, Optional

from agno.knowledge.document import Document
from agno.knowledge.reader.base import Reader as BaseReader


class DocReader(BaseReader):
    """基于 antiword 的 DOC 文件读取器"""

    def __init__(self, chunking_strategy=None, **kwargs):
        """初始化 DOC 读取器

        Args:
            chunking_strategy: 分块策略（兼容 agno 接口）
        """
        super().__init__(chunking_strategy=chunking_strategy, **kwargs)

        # 标记解析组件是否已初始化（目前仅作为防御性标志）
        self.unstructured_available = True

    def _check_unstructured(self):
        """兼容旧接口，目前仅保留占位，实际逻辑全部在 _read_with_unstructured 中实现。"""
        self.unstructured_available = True

    def read(
        self,
        doc: Union[str, Path, io.BytesIO],
        name: Optional[str] = None,
    ) -> List[Document]:
        """读取 DOC 文件

        Args:
            doc: DOC 文件路径、Path 对象或字节流
            name: 文档名称（可选）

        Returns:
            文档列表
        """
        if not self.unstructured_available:
            # 理论上不会触发，保留防御性错误信息
            raise ImportError("DOC 解析组件未正确初始化，请检查 DocReader._check_unstructured 实现")

        # 准备文件路径
        if isinstance(doc, (str, Path)):
            doc_path = str(doc)
            if not os.path.exists(doc_path):
                raise FileNotFoundError(f"DOC 文件不存在: {doc_path}")

            file_size = os.path.getsize(doc_path)
            if file_size == 0:
                raise ValueError(f"DOC 文件为空（0字节）: {doc_path}")

            print(f"  [DOC] 文件路径: {doc_path}, 大小: {file_size} 字节")
            return self._read_with_unstructured(doc_path, name)
        else:
            # 字节流 - 需要先保存为临时文件
            content = doc.read()
            if not content or len(content) == 0:
                raise ValueError(f"DOC 字节流为空")

            print(f"  [DOC] 字节流大小: {len(content)} 字节")

            # 创建临时文件
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=".doc") as tmp:
                tmp.write(content)
                temp_path = tmp.name

            try:
                return self._read_with_unstructured(temp_path, name)
            finally:
                # 清理临时文件
                if os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                    except:
                        pass

    def _read_with_unstructured(
        self,
        file_path: str,
        name: Optional[str] = None,
    ) -> List[Document]:
        """使用 antiword 解析 DOC 文件

        主路径：
            - 调用系统命令 `antiword` 直接输出纯文本
        说明：
            - antiword 专门支持 Word 97-2003 `.doc` 二进制格式
            - 不依赖 LibreOffice，不需要 GUI
        """
        try:
            # 1. 主路径：调用 antiword
            try:
                print(f"  [antiword] 尝试解析 DOC 文档: {file_path}")
                result = subprocess.run(
                    ["antiword", file_path],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.returncode != 0:
                    # antiword 有错误输出时打印日志，交给后续逻辑处理
                    stderr = (result.stderr or "").strip()
                    print(f"  ⚠️  antiword 返回码 {result.returncode}, 错误信息: {stderr}")
                    raise RuntimeError(f"antiword 解析失败, code={result.returncode}, error={stderr}")

                text_content = (result.stdout or "").strip()
                if not text_content:
                    print("  ⚠️  antiword 输出内容为空")
                    return []

                print(f"  ✅ antiword 成功解析 DOC 文档，文本长度: {len(text_content)} 字符")

            except FileNotFoundError:
                # 系统未安装 antiword
                raise RuntimeError(
                    "未找到 antiword 命令，请在服务器上先安装：apt-get install -y antiword"
                )
            except subprocess.TimeoutExpired:
                raise RuntimeError("antiword 解析 DOC 文档超时")

            # 2. 包装为 Document
            full_content = text_content.strip()

            if not full_content:
                print("  ⚠️  提取的内容为空")
                return []

            meta_data = {
                "source": name or file_path,
                "method": "antiword",
                "num_elements": 1,
            }

            if name:
                meta_data["filename"] = name

            document = Document(
                content=full_content,
                name=name or file_path,
                meta_data=meta_data,
            )

            # 3. 应用分块策略
            if self.chunking_strategy:
                try:
                    chunked_docs = self.chunking_strategy.chunk(document)
                    print(f"  ✅ DOC 文档解析成功，已分块为 {len(chunked_docs)} 个部分")
                    return chunked_docs
                except Exception as e:
                    print(f"  ⚠️  分块失败，使用原始文档: {e}")
                    return [document]
            else:
                print(f"  ✅ DOC 文档解析成功，共 {len(full_content)} 个字符")
                return [document]

        except Exception as e:
            print(f"  ❌ DOC 文档解析失败: {str(e)}")
            raise


def create_doc_reader(chunking_strategy=None) -> DocReader:
    """
    创建 DOC Reader 实例的工厂函数

    Args:
        chunking_strategy: 分块策略

    Returns:
        DocReader 实例
    """
    return DocReader(chunking_strategy=chunking_strategy)
