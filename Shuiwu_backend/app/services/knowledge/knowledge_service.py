"""知识库业务逻辑层

协调各层，提供完整的知识库服务，包括：
- 创建知识库
- 列出知识库
- 上传文档
- 搜索知识库
- 删除知识库
"""
import base64
import json
import os
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from agno.knowledge.knowledge import Knowledge

from app.agno.tools.knowledge.knowledge_client import create_knowledge_base_instance
from app.infra.db import get_db_url, get_sync_engine
from app.services.files.files_repository import files_repository
from app.services.knowledge.knowledge_repository import knowledge_repository
from app.utils.knowledge_utils import build_table_name, create_chunking_reader


class KnowledgeService:
    """知识库服务类"""
    
    def __init__(self):
        self.db_schema = "knowledge"
        self.db_url = get_db_url()
        self.repository = knowledge_repository
        # 知识库缓存
        self.knowledge_bases: Dict[str, Knowledge] = {}
    
    def create_knowledge_base(
        self,
        name: str,
        description: str,
        user_id: str,
        chunking_rule: str = "fixed_size",
        chunk_size: int = 5000,
        chunk_overlap: int = 200,
        embedder_model: str = "text-embedding-3-small",
        type_id: Optional[str] = None,
        is_system: bool = False,
    ) -> Knowledge:
        """创建知识库

        Args:
            name: 知识库名称
            description: 知识库描述
            user_id: 用户ID
            chunking_rule: 分块规则
            chunk_size: 分块大小
            chunk_overlap: 分块重叠大小
            embedder_model: 嵌入模型ID
            type_id: 知识库类型ID（可选）
            is_system: 是否为系统知识库（默认false）

        Returns:
            Knowledge 实例
        """
        kb_key = f"{user_id}_{name}"
        if kb_key in self.knowledge_bases:
            raise Exception("知识库已存在")

        # 检查表是否已存在
        table_name = build_table_name(user_id, name)
        if self.repository.check_knowledge_base_exists(table_name):
            raise Exception("知识库表已存在")

        # 清理可能残留的索引（防止之前删除不干净导致冲突）
        self._cleanup_orphaned_indexes(table_name)

        # 创建知识库实例
        knowledge = create_knowledge_base_instance(
            name=name,
            description=description,
            user_id=user_id,
            db_url=self.db_url,
            embedder_model=embedder_model,
            schema=self.db_schema,
        )

        # 确保物理表创建
        knowledge.vector_db.create()

        # 注册到知识库注册表（与类型关联）
        # 将空字符串 type_id 转换为 None，避免外键约束失败
        actual_type_id = type_id if type_id else None

        self.repository.register_knowledge_base(
            table_name=table_name,
            kb_name=name,
            user_id=user_id,
            type_id=actual_type_id,
            description=description,
            chunking_rule=chunking_rule,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            embedder_model=embedder_model,
            is_system=is_system
        )

        # 缓存知识库实例
        self.knowledge_bases[kb_key] = knowledge
        return knowledge
    
    def get_or_load_knowledge(
        self,
        user_id: str,
        kb_name: str,
        embedder_model: str = "text-embedding-3-small",
    ) -> Knowledge:
        """获取或加载知识库实例

        Args:
            user_id: 用户ID
            kb_name: 知识库名称
            embedder_model: 嵌入模型ID

        Returns:
            Knowledge 实例
        """
        # 先检查是否为系统知识库（通过知识库名称直接查询）
        system_kb_info = self.repository.get_system_knowledge_by_name(kb_name)

        if system_kb_info:
            # 系统知识库：使用系统知识库的配置
            # 系统知识库的缓存键使用 "system_{kb_name}" 格式，避免与用户知识库冲突
            kb_key = f"system_{kb_name}"

            # 检查缓存
            if kb_key in self.knowledge_bases:
                return self.knowledge_bases[kb_key]

            # 从系统知识库信息中获取必要的字段
            table_name = system_kb_info["table_name"]
            system_user_id = system_kb_info["user_id"]
            description = system_kb_info.get("description", "")
            actual_embedder_model = system_kb_info.get("embedder_model", embedder_model)

            # 创建知识库实例（连接到已存在的表）
            # 必须传入 registry 中存储的 table_name，避免重新生成导致不一致
            knowledge = create_knowledge_base_instance(
                name=kb_name,
                description=description,
                user_id=system_user_id,
                db_url=self.db_url,
                table_name=table_name,  # 使用 registry 中存储的表名
                embedder_model=actual_embedder_model,
                schema=self.db_schema,
            )

            # 初始化向量数据库连接（create() 有幂等性，表存在时不会重复创建）
            # 这一步很关键：它会初始化 PgVector 的内部状态，使其能够访问已存在的表
            knowledge.vector_db.create()

            # 缓存知识库实例
            self.knowledge_bases[kb_key] = knowledge
            return knowledge
        else:
            # 用户知识库：使用原有逻辑
            kb_key = f"{user_id}_{kb_name}"

            # 检查缓存
            if kb_key in self.knowledge_bases:
                return self.knowledge_bases[kb_key]

            # 检查表是否存在
            table_name = build_table_name(user_id, kb_name)
            if not self.repository.check_knowledge_base_exists(table_name):
                raise Exception(f"知识库 '{kb_name}' 不存在")

            # 从 repository 获取知识库信息
            kb_info = self.repository.get_knowledge_base_info(table_name)
            if not kb_info:
                raise Exception(f"无法获取知识库 '{kb_name}' 信息")

            # 创建知识库实例（连接到已存在的表）
            # 必须传入 registry 中存储的 table_name，避免重新生成导致不一致
            knowledge = create_knowledge_base_instance(
                name=kb_name,
                description=kb_info.get("description", ""),
                user_id=user_id,
                db_url=self.db_url,
                table_name=table_name,  # 使用 registry 中存储的表名
                embedder_model=embedder_model,
                schema=self.db_schema,
            )

            # 初始化向量数据库连接（create() 有幂等性，表存在时不会重复创建）
            # 这一步很关键：它会初始化 PgVector 的内部状态，使其能够访问已存在的表
            knowledge.vector_db.create()

            # 缓存知识库实例
            self.knowledge_bases[kb_key] = knowledge
            return knowledge
    
    def list_knowledge_bases(
        self,
        user_id: Optional[str] = None,
        type_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """列出知识库

        Args:
            user_id: 用户ID，如果提供则只返回该用户的知识库
            type_id: 知识库类型ID，如果提供则只返回该类型的知识库

        Returns:
            知识库信息列表
        """
        # 如果指定了类型，从注册表查询
        if type_id:
            return self.repository.list_knowledge_bases_by_type(
                user_id=user_id,
                type_id=type_id
            )

        # 否则返回所有知识库（兼容旧逻辑）
        return self.repository.list_knowledge_bases(user_id)
    
    def list_documents_by_table_name(
        self,
        table_name: str,
        current_user_id: str,
        is_admin: bool = False,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """通过 table_name 获取知识库的文档列表（带权限检查、分页和搜索）

        Args:
            table_name: 知识库表名
            current_user_id: 当前请求的用户ID（从token获取）
            is_admin: 当前用户是否是管理员
            page: 页码（默认1）
            page_size: 每页数量（默认20）
            search: 搜索关键词（可选，用于搜索文件名）

        Returns:
            包含文档列表和分页信息的字典

        Raises:
            ValueError: 知识库不存在或无权访问
        """
        if not table_name:
            raise ValueError("table_name 不能为空")

        if not current_user_id:
            raise ValueError("current_user_id 不能为空")

        try:
            # 从 registry 表中查询知识库信息（用于权限检查）
            kb_info = self.repository.get_knowledge_base_registry(table_name)

            if not kb_info:
                raise ValueError(f"知识库表 '{table_name}' 不存在")

            kb_owner_id = kb_info.get("user_id")
            is_system = kb_info.get("is_system", False)
            kb_name = kb_info.get("kb_name", "")

            # 权限检查：管理员可以访问所有知识库，普通用户只能访问自己的或系统知识库
            if not is_admin and kb_owner_id != current_user_id and not is_system:
                raise ValueError(f"无权访问知识库 '{kb_name}'")

            # 直接获取原始 DBAPI 连接
            engine = get_sync_engine()
            raw_conn = engine.raw_connection()

            try:
                # 转义 table_name 中的单引号
                safe_table_name = table_name.replace("'", "''")

                # 使用原始 DBAPI 连接执行 SQL
                cursor = raw_conn.cursor()
                cursor.execute(
                    """
                        SELECT document_ids
                        FROM knowledge.knowledge_base_registry
                        WHERE table_name = %s
                    """,
                    (safe_table_name,)
                )
                row = cursor.fetchone()

                if not row:
                    raise ValueError(f"知识库 {kb_name} 不存在")

                # cursor.fetchone() 返回元组，document_ids 是第一个字段（索引 0）
                document_ids = row[0] if isinstance(row[0], list) else []

            finally:
                cursor.close()
                raw_conn.close()

            # 收集所有 file_id 用于批量查询下载链接
            # 清理 file_id 中的多余单引号（某些旧数据可能包含）
            file_ids = []
            for doc in document_ids:
                if isinstance(doc, dict) and doc.get("file_id"):
                    file_id = doc.get("file_id")
                    # 去除可能存在的首尾单引号
                    if isinstance(file_id, str):
                        file_id = file_id.strip().strip("'").strip('"')
                    file_ids.append(file_id)

            print(f"[DEBUG] 清理后的 file_ids 数量={len(file_ids)}")

            # 管理员可以查看所有文件的下载链接，普通用户只能查看自己的
            file_info_map = files_repository.get_files_by_ids(
                file_ids,
                user_id=current_user_id,
                is_admin=is_admin
            ) if file_ids else {}

            # 直接返回 document_ids 中的信息（已包含 filename 和 created_at）
            documents_list = []
            for doc in document_ids:
                if isinstance(doc, dict):
                    file_id = doc.get("file_id")
                    # 同样清理 file_id 用于匹配
                    if isinstance(file_id, str):
                        file_id = file_id.strip().strip("'").strip('"')
                    file_info = file_info_map.get(file_id, {})
                    documents_list.append({
                        "filename": doc.get("filename", "未知文件"),
                        "file_id": file_id,
                        "created_at": doc.get("created_at"),
                        "parse_status": "已解析",  # 只有成功导入才会记录到 document_ids
                        "download_url": file_info.get("file_url", "")  # 从 business.files 获取下载链接
                    })

            # 按 created_at 倒序排序
            documents_list.sort(
                key=lambda x: x.get("created_at") or "",
                reverse=True
            )

            # 搜索过滤（按文件名）
            if search:
                search_lower = search.lower()
                documents_list = [
                    doc for doc in documents_list
                    if search_lower in doc.get("filename", "").lower()
                ]

            # 计算分页
            total_documents = len(documents_list)
            total_pages = (total_documents + page_size - 1) // page_size if total_documents > 0 else 0

            # 确保页码在有效范围内
            page = max(1, min(page, total_pages)) if total_pages > 0 else 1

            # 计算起始和结束索引
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size

            # 获取当前页的文档
            paginated_documents = documents_list[start_idx:end_idx]

            # 打印前3个文档的匹配情况（仅第一次调用时）
            if page == 1:
                print(f"[DEBUG] 返回给前端的前3个文档:")
                for i, doc in enumerate(paginated_documents[:3]):
                    file_id = doc.get('file_id')
                    matched = file_id in file_info_map
                    has_url = bool(doc.get('download_url'))
                    print(f"[DEBUG]   [{i+1}] matched={matched}, has_url={has_url}, filename={doc.get('filename')[:30]}...")

            return {
                "status": "success",
                "kb_name": kb_name,
                "user_id": kb_owner_id,  # 返回知识库所有者的 user_id
                "table_name": table_name,
                "total_documents": total_documents,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "documents": paginated_documents,
            }

        except Exception as e:
            import traceback
            error_detail = f"{str(e)}\n{traceback.format_exc()}"
            raise Exception(error_detail)

    def _add_document_to_registry(
        self,
        table_name: str,
        file_id: str,
        filename: str
    ):
        """将成功的文档添加到 knowledge_base_registry 的 document_ids 数组

        Args:
            table_name: 知识库表名（可能包含 schema 前缀）
            file_id: 文件ID
            filename: 文件名
        """

        try:
            from datetime import datetime

            # 直接获取原始 DBAPI 连接，不使用 SQLAlchemy Connection
            engine = get_sync_engine()
            raw_conn = engine.raw_connection()

            try:
                # 构建新的文档 JSON 对象
                doc_json = json.dumps({
                    "file_id": file_id,
                    "filename": filename,
                    "created_at": datetime.utcnow().isoformat()
                })

                # 处理 table_name：如果包含 schema 前缀（如 "knowledge.table_name"），则去掉前缀
                # knowledge_base_registry.table_name 字段存储的是不带 schema 的表名
                if "." in str(table_name):
                    # 包含 schema 前缀，提取纯表名
                    registry_table_name = str(table_name).split(".")[-1]
                else:
                    # 不包含 schema 前缀，直接使用
                    registry_table_name = str(table_name)

                # 转义 table_name 中的单引号
                safe_table_name = registry_table_name.replace("'", "''")

                # 使用原始 DBAPI 连接执行 SQL
                cursor = raw_conn.cursor()
                cursor.execute(
                    """
                        UPDATE knowledge.knowledge_base_registry
                        SET document_ids = document_ids || %s::jsonb,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE table_name = %s
                    """,
                    (doc_json, safe_table_name)
                )

                # 提交事务 - 使用原始连接的 commit
                raw_conn.commit()

            finally:
                # 确保关闭 cursor 和连接
                cursor.close()
                raw_conn.close()

        except Exception as e:
            # 静默失败，不影响主流程
            print(f"更新 document_ids 失败（非关键错误）: {e}")

    def _remove_document_from_registry(
        self,
        table_name: str,
        file_id: str
    ):
        """从 knowledge_base_registry 的 document_ids 数组中移除文档

        Args:
            table_name: 知识库表名（可能包含 schema 前缀）
            file_id: 要移除的文件ID
        """
        try:
            # 直接获取原始 DBAPI 连接
            engine = get_sync_engine()
            raw_conn = engine.raw_connection()

            try:
                # 处理 table_name：如果包含 schema 前缀（如 "knowledge.table_name"），则去掉前缀
                # knowledge_base_registry.table_name 字段存储的是不带 schema 的表名
                if "." in str(table_name):
                    # 包含 schema 前缀，提取纯表名
                    registry_table_name = str(table_name).split(".")[-1]
                else:
                    # 不包含 schema 前缀，直接使用
                    registry_table_name = str(table_name)

                # 转义参数中的单引号
                safe_table_name = registry_table_name.replace("'", "''")
                safe_file_id = file_id.replace("'", "''")

                # 使用原始 DBAPI 连接执行 SQL
                cursor = raw_conn.cursor()
                cursor.execute(
                    """
                        UPDATE knowledge.knowledge_base_registry
                        SET document_ids = (
                            SELECT jsonb_agg(doc)
                            FROM jsonb_array_elements(document_ids) AS doc
                            WHERE doc->>'file_id' != %s
                        ),
                        updated_at = CURRENT_TIMESTAMP
                        WHERE table_name = %s
                    """,
                    (safe_file_id, safe_table_name)
                )

                # 提交事务
                raw_conn.commit()

            finally:
                cursor.close()
                raw_conn.close()

        except Exception as e:
            # 静默失败，不影响主流程
            print(f"从 document_ids 移除失败（非关键错误）: {e}")

    def upload_document_from_base64(
        self,
        knowledge: Knowledge,
        file_base64: str,
        filename: str,
        user_id: str,
        chunking_rule: str = "fixed_size",
        chunk_size: int = 5000,
        chunk_overlap: int = 200,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        从 base64 编码上传文档到知识库（核心文档处理函数）

        完整流程：base64解码 → 写入临时文件 → 文档分块 → 向量化嵌入 → 存储到PgVector

        调用链路：
            POST /api/knowledge-base/upload (API层)
              → upload_document() (路由处理)
                → _run_sync(upload_document_from_base64) (异步转同步)
                  → 本函数 (业务逻辑)

        Args:
            knowledge: Knowledge 实例（Agno框架的知识库对象，包含vector_db配置）
            file_base64: 前端传来的 base64 编码文件内容（如 "JVBERi0xLjQK..."）
            filename: 原始文件名（如 "增值税政策.pdf"）
            user_id: 上传者的用户ID（用于权限控制和元数据记录）
            chunking_rule: 分块策略
                - "fixed_size": 固定大小分块（默认，适合结构化文档）
                - "semantic": 语义分块（根据内容智能切分）
                - "recursive": 递归分块（多层嵌套结构）
            chunk_size: 每个分块的最大字符数（默认5000）
            chunk_overlap: 相邻分块之间的重叠字符数（默认200，保证上下文连续性）
            metadata: 额外的自定义元数据（可选，会合并到doc_metadata中）

        Returns:
            Dict[str, Any]: 上传结果字典，包含以下字段：
                - status: "success" 或 "error"
                - message: 结果描述信息
                - filename: 文件名（成功时返回）
                - file_id: 系统生成的唯一文件ID（成功时返回，UUID格式）
                - user_id: 用户ID（成功时返回）
        """

        # ════════════════════════════════════════════════════════
        # 第1步：Base64 解码
        # 将前端传来的 base64 字符串还原为原始二进制文件内容
        # ════════════════════════════════════════════════════════
        file_content = base64.b64decode(file_base64)

        # 诊断日志：记录解码前后的数据大小，便于排查问题
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[DEBUG] base64解码: 原始长度={len(file_base64)}, 解码后={len(file_content)} 字节")

        # 验证文件大小（防止空文件导致PDF读取器等下游组件报错崩溃）
        if not file_content or len(file_content) == 0:
            logger.error(f"[ERROR] base64解码后内容为空! 原始base64长度={len(file_base64)}")
            return {"status": "error", "message": f"文件 {filename} 为空，无法上传"}

        # ════════════════════════════════════════════════════════
        # 第2步：创建临时文件
        # Agno 的 add_content() 接收的是文件路径而非内存中的内容，
        # 所以需要先将解码后的字节写入磁盘临时文件
        # ════════════════════════════════════════════════════════
        file_ext = os.path.splitext(filename)[1]  # 提取文件扩展名（如 .pdf, .docx），用于决定使用哪种文档解析器

        # 使用固定的上传临时目录（避免 /tmp 在某些系统上的权限或清理问题）
        upload_temp_dir = os.path.join(os.getcwd(), "temp_uploads")  # 项目根目录下的 temp_uploads 文件夹
        os.makedirs(upload_temp_dir, exist_ok=True)  # 如果目录不存在则自动创建（exist_ok=True 防止已存在时报错）

        # 创建命名临时文件并写入解码后的文件内容
        with tempfile.NamedTemporaryFile(
            delete=False,          # 不自动删除（手动在 finally 中清理，确保异常时也能清理）
            suffix=file_ext,       # 保留原始扩展名（Agno 根据扩展名选择 PDFReader/DocxReader 等解析器）
            dir=upload_temp_dir    # 指定临时文件的存储目录
        ) as tmp:
            tmp.write(file_content)           # 将二进制内容写入临时文件
            tmp.flush()                       # 显式刷新 Python 缓冲区，确保数据从内存写入操作系统缓冲区
            os.fsync(tmp.fileno())            # 强制操作系统将缓冲区数据刷入磁盘（防止断电/崩溃导致数据丢失）

            temp_path = tmp.name  # 保存临时文件的完整路径，后续传递给 Agno 使用

        logger.info(f"[DEBUG] 临时文件创建: path={temp_path}, 预期大小={len(file_content)} 字节")

        # ════════════════════════════════════════════════════════
        # 第3步：验证临时文件完整性
        # 多重检查确保文件确实写入成功，避免后续 Agno 处理时报莫名其妙的错误
        # ════════════════════════════════════════════════════════
        if not os.path.exists(temp_path):  # 检查文件是否真的存在于文件系统中
            logger.error(f"[ERROR] 临时文件不存在: {temp_path}")
            return {"status": "error", "message": f"临时文件创建失败"}

        actual_size = os.path.getsize(temp_path)  # 获取文件实际占用的磁盘空间大小（字节数）
        logger.info(f"[DEBUG] 临时文件验证: exists={os.path.exists(temp_path)}, size={actual_size} 字节")

        if actual_size == 0:  # 文件存在但大小为0（可能是磁盘满、权限问题等）
            logger.error(f"[ERROR] 临时文件为空! path={temp_path}")
            return {"status": "error", "message": f"临时文件写入后为空（期望 {len(file_content)} 字节）"}

        if actual_size != len(file_content):  # 大小不匹配（罕见情况，但值得记录警告）
            logger.warning(f"[WARNING] 临时文件大小不匹配! 预期={len(file_content)}, 实际={actual_size}")

        try:
            # ════════════════════════════════════════════════════════
            # 第4步：验证嵌入器（Embedder）配置
            # 嵌入器负责将文本转换为向量（如 text-embedding-3-small 模型），
            # 如果配置有误，提前报错比让下游 Agno 报晦涩的错误更友好
            # ════════════════════════════════════════════════════════
            embedder = knowledge.vector_db.embedder  # 从知识库的向量数据库配置中获取嵌入器实例
            if not embedder or not hasattr(embedder, 'id') or not embedder.id:
                return {"status": "error", "message": "嵌入器配置错误：模型名称为空，请检查 embedder_model 参数"}

            # ════════════════════════════════════════════════════════
            # 第5步：创建文档分块读取器（Reader）
            # Reader 负责：
            #   1. 根据文件扩展名选择对应的解析器（PDF→PyPDF2, DOCX→python-docx, ...）
            #   2. 按照指定的规则将文档切分成多个文本块（chunk）
            #   3. 每个chunk 后续会被独立向量化
            # ════════════════════════════════════════════════════════
            reader = create_chunking_reader(
                file_extension=file_ext,     # 文件扩展名，决定使用哪种文档解析器
                chunking_rule=chunking_rule, # 分块策略（fixed_size / semantic / recursive）
                chunk_size=chunk_size,       # 每块最大字符数
                chunk_overlap=chunk_overlap, # 块间重叠字符数（保持上下文连贯性）
                embedder=embedder,           # 传入嵌入器实例（语义分块时需要用到向量计算）
            )

            # ════════════════════════════════════════════════════════
            # 第6步：构建文档元数据（Metadata）
            # 元数据会随每个向量记录一起存入 PgVector 数据库，
            # 用于后续检索时的过滤、溯源和展示
            # ════════════════════════════════════════════════════════
            doc_metadata = {
                "user_id": user_id,                    # 上传者ID（用于权限隔离：用户只能搜索自己的文档）
                "filename": filename,                  # 原始文件名（展示给用户看，也用于去重判断）
                "chunking_rule": chunking_rule,        # 记录使用的分块规则（便于排查问题）
                "chunk_size": chunk_size,              # 记录分块大小参数
                "uploaded_at": datetime.utcnow().isoformat(),  # ISO格式上传时间（UTC）
            }
            if metadata:  # 如果调用方传入额外的自定义元数据，合并到基础元数据中
                doc_metadata.update(metadata)

            # ════════════════════════════════════════════════════════
            # 第7步：调用 Agno 框架添加文档（核心步骤！）
            #
            # knowledge.add_content() 内部执行流程：
            #   ① Reader 读取临时文件 → 解析文档内容
            #   ② 按 chunking_rule 切分成多个文本块
            #   ③ 对每个文本块调用 Embedder API → 生成向量（如384维浮点数组）
            #   ④ 将 (文本, 向量, 元数据) 作为一条记录 INSERT 到 PgVector 表
            #   ⑤ 自动创建 vector 列的 IVFFlat 索引（加速相似度搜索）
            #
            # 注意：这一步是耗时最长的操作（取决于文档大小和API响应速度）
            # 一个10页PDF可能产生20-50个chunk，每个chunk都需要一次Embedding API调用
            # ════════════════════════════════════════════════════════
            try:
                # 在调用 agno 前再次确认文件存在（防御性编程，防止极端情况下文件被意外删除）
                if not os.path.exists(temp_path):
                    logger.error(f"[ERROR] agno调用前文件不存在! path={temp_path}")
                    return {"status": "error", "message": f"临时文件在传递给agno前丢失: {temp_path}"}

                logger.info(f"[DEBUG] 调用 knowledge.add_content: path={temp_path}, reader={reader.__class__.__name__}")

                # 🚀 核心调用：将文档内容导入知识库向量数据库
                knowledge.add_content(
                    path=temp_path,     # 临时文件路径（Agno 内部会打开这个文件进行读取）
                    reader=reader,      # 配置好的文档分块读取器
                    metadata=doc_metadata,  # 附加到每条向量记录上的元数据
                )

                # 调用后再次检查文件状态（某些 Reader 实现可能会删除源文件）
                if not os.path.exists(temp_path):
                    logger.warning(f"[WARNING] agno调用后文件被删除: {temp_path}")
                else:
                    logger.info(f"[DEBUG] agno调用后文件仍存在: {temp_path}")

            except ValueError as ve:
                # 捕获 Agno 抛出的维度校验错误
                error_msg = str(ve)
                if "dimensions" in error_msg.lower():
                    # 维度错误通常意味着 Embedding API 返回了空向量或错误格式的向量
                    return {"status": "error", "message": f"文档 {filename} 上传失败：嵌入API调用失败，返回了空向量。请检查 OPENAI_API_KEY、OPENAI_BASE_URL 和 embedder_model 配置。错误详情: {ve}"}
                raise  # 其他 ValueError 继续向上抛出
            except Exception as api_err:
                # 捕获其他 API 相关错误（403无权限、网络超时、配额不足等）
                error_msg = str(api_err)
                if "403" in error_msg or "api" in error_msg.lower():
                    return {"status": "error", "message": f"文档 {filename} 上传失败：嵌入API调用失败 ({error_msg})，请检查API配置"}
                raise  # 非API错误继续向上抛出，由外层统一捕获

            # ════════════════════════════════════════════════════════
            # 第8步：更新 filters 字段（增强检索能力）
            # PgVector 表的 filters 列是 JSONB 类型，存储过滤条件
            # 这里将 filename 写入 filters，使得后续可以按文件名精确过滤搜索结果
            # 例如："找出《增值税政策.pdf》中关于税率的所有段落"
            # ════════════════════════════════════════════════════════
            table_name = knowledge.vector_db.table_name  # 获取当前知识库对应的PgVector表名
            self._update_filters_with_filename(table_name, filename, user_id)  # 批量更新该文件所有chunk的filters字段

            # ════════════════════════════════════════════════════════
            # 第9步：生成 file_id 并更新注册表
            # file_id 是系统内部对这份上传文档的唯一标识符（UUID格式），
            # 用于关联 file_manager 表和 knowledge_base_registry 表
            # ════════════════════════════════════════════════════════
            import uuid
            file_id = str(uuid.uuid4())  # 生成 UUID v4 格式的唯一标识符（如 "a3f8b2c1-d4e5-4a6b-8c9d-0e1f2a3b4c5d"）

            # 更新 knowledge_base_registry 表的 document_ids 数组
            # （记录该知识库下包含了哪些文档，用于展示和管理）
            self._add_document_to_registry(table_name, file_id, filename)

            # ════════════════════════════════════════════════════════
            # 第10步：返回成功结果
            # ════════════════════════════════════════════════════════
            return {
                "status": "success",                                    # 状态标记
                "message": f"文档 {filename} 已成功上传到知识库",         # 用户友好的提示消息
                "filename": filename,                                   # 回传文件名（前端可能需要显示）
                "file_id": file_id,                                     # 文件唯一标识（后续可用于查询/删除）
                "user_id": user_id,                                     # 回传用户ID
            }
        except Exception as exc:
            # 兜底异常捕获：任何未预料到的错误都会在这里被捕获并返回友好的错误信息
            # 而不是让异常直接抛出到 FastAPI 层导致 500 Internal Server Error
            return {"status": "error", "message": f"上传失败: {exc}"}
        finally:
            # ════════════════════════════════════════════════════════
            # 第11步（无论成功失败都执行）：清理临时文件
            # 防止临时文件堆积占用磁盘空间
            # ════════════════════════════════════════════════════════
            if os.path.exists(temp_path):
                os.unlink(temp_path)  # 删除临时文件

    async def upload_documents_batch_async(
        self,
        knowledge: Knowledge,
        files: List[Dict[str, str]],
        user_id: str,
        chunking_rule: str = "fixed_size",
        chunk_size: int = 5000,
        chunk_overlap: int = 200,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """批量上传文档（异步），对齐 Back 项目的实现"""
        contents: List[Dict[str, Any]] = []
        temp_paths: List[str] = []
        results: List[Dict[str, Any]] = []

        try:
            for f in files:
                try:
                    filename = f["filename"]
                    file_content = base64.b64decode(f["file_base64"])

                    # 验证文件大小（防止空文件导致PDF读取器报错）
                    if not file_content or len(file_content) == 0:
                        results.append(
                            {
                                "status": "error",
                                "message": f"文件 {filename} 为空，无法上传",
                                "filename": filename,
                                "user_id": user_id,
                            }
                        )
                        continue

                    suffix = os.path.splitext(filename)[1]

                    # 使用固定的上传临时目录
                    upload_temp_dir = os.path.join(os.getcwd(), "temp_uploads")
                    os.makedirs(upload_temp_dir, exist_ok=True)

                    with tempfile.NamedTemporaryFile(
                        delete=False,
                        suffix=suffix,
                        dir=upload_temp_dir
                    ) as tmp:
                        tmp.write(file_content)
                        tmp.flush()  # 显式刷新缓冲区
                        os.fsync(tmp.fileno())  # 强制写入磁盘
                        temp_path = tmp.name

                    # 验证临时文件
                    if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                        results.append(
                            {
                                "status": "error",
                                "message": f"临时文件创建失败或为空",
                                "filename": filename,
                                "user_id": user_id,
                            }
                        )
                        continue

                    temp_paths.append(temp_path)

                    reader = create_chunking_reader(
                        file_extension=suffix,
                        chunking_rule=chunking_rule,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        embedder=knowledge.vector_db.embedder,
                    )

                    doc_metadata = {
                        "user_id": user_id,
                        "filename": filename,
                        "chunking_rule": chunking_rule,
                        "chunk_size": chunk_size,
                        "uploaded_at": datetime.utcnow().isoformat(),
                    }
                    if metadata:
                        doc_metadata.update(metadata)

                    contents.append({"path": temp_path, "reader": reader, "metadata": doc_metadata})
                except Exception as e:
                    results.append(
                        {
                            "status": "error",
                            "message": f"文件准备失败: {str(e)}",
                            "filename": f.get("filename", "unknown"),
                            "user_id": user_id,
                        }
                    )

            if not contents:
                return results

            # 调用 agno 的异步批量添加
            await knowledge.add_contents_async(contents)

            # 确保 filters 字段包含 filename（用于后续检索）
            table_name = knowledge.vector_db.table_name
            for c in contents:
                filename = c["metadata"]["filename"]
                self._update_filters_with_filename(table_name, filename, user_id)

            for c in contents:
                filename = c["metadata"]["filename"]
                results.append(
                    {
                        "status": "success",
                        "message": f"文档 {filename} 已成功上传到知识库",
                        "filename": filename,
                        "user_id": user_id,
                    }
                )

            return results
        except Exception as e:
            # 如果还没有结果，为所有文件返回错误
            if not results:
                return [
                    {
                        "status": "error",
                        "message": f"批量上传失败: {str(e)}",
                        "filename": f.get("filename", "unknown"),
                        "user_id": user_id,
                    }
                    for f in files
                ]
            return results
        finally:
            for p in temp_paths:
                if os.path.exists(p):
                    os.unlink(p)

    def _update_filters_with_filename(self, table_name: str, filename: str, user_id: str):
        """更新 filters 字段，确保包含 filename"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                sql = text(f"""
                    UPDATE {self.db_schema}."{table_name}"
                    SET filters = jsonb_build_object('filename', :filename)
                    WHERE meta_data->>'filename' = :filename
                    AND meta_data->>'user_id' = :user_id
                """)
                conn.execute(sql, {"filename": filename, "user_id": user_id})
                conn.commit()
        except Exception as e:
            print(f"更新 filters 字段失败: {e}")

    def _get_existing_filenames_in_knowledge_base(self, table_name: str, user_id: str) -> set:
        """获取知识库中已存在的文件名集合（用于检查重名）

        Args:
            table_name: 知识库表名
            user_id: 用户ID

        Returns:
            文件名集合
        """
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                # 只查询有实际内容的记录（content 不为空且 embedding 不为空）
                # 排除之前上传失败时留下的空记录
                sql = text(f"""
                    SELECT DISTINCT
                        COALESCE(
                            (meta_data->>'filename')::text,
                            (filters->>'filename')::text,
                            name
                        ) AS filename
                    FROM "{self.db_schema}"."{table_name}"
                    WHERE meta_data->>'user_id' = :user_id
                    AND length(content) > 0
                    AND embedding IS NOT NULL
                """)
                result = conn.execute(sql, {"user_id": user_id})
                filenames = {row[0] for row in result if row[0]}
                print(f"[DEBUG] 查询到有内容的文件名: {filenames}")
                return filenames
        except Exception as e:
            print(f"获取知识库已存在文件名失败: {e}")
            import traceback
            traceback.print_exc()
            return set()

    def search_knowledge_base(
        self,
        user_id: str,
        kb_name: str,
        query: str,
        top_k: int = 5,
        search_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """在知识库中搜索
        
        Args:
            user_id: 用户ID
            kb_name: 知识库名称
            query: 搜索查询
            top_k: 返回结果数量
            search_type: 搜索类型（"similarity", "keyword", "hybrid"）
            
        Returns:
            搜索结果字典
        """
        try:
            # 获取知识库实例
            kb = self.get_or_load_knowledge(user_id=user_id, kb_name=kb_name)
            
            # 使用 hybrid 搜索（默认）
            search_type = search_type or "hybrid"
            results = kb.search(query=query, max_results=top_k, search_type=search_type)
            
            search_results = []
            for result in results:
                ref_id = getattr(result, "id", None)
                ref_name = getattr(result, "name", None)
                content = getattr(result, "content", "")
                score = getattr(result, "score", 0.0)
                meta_data = getattr(result, "meta_data", {})
                filters = getattr(result, "filters", {})
                
                # 尝试从数据库补全 filters（用于获取真实文件名）
                if not filters or "filename" not in filters:
                    filters = self._load_filters_from_db(kb.vector_db.table_name, ref_id, ref_name)
                
                filename = (
                    filters.get("filename") if isinstance(filters, dict) else
                    meta_data.get("filename") if isinstance(meta_data, dict) else
                    ref_name
                )
                
                search_results.append({
                    "id": ref_id,
                    "name": ref_name,
                    "content": content,
                    "score": score,
                    "filename": filename,
                    "meta_data": meta_data,
                })
            
            return {
                "status": "success",
                "results": search_results,
                "count": len(search_results),
            }
        except Exception as e:
            raise Exception(f"搜索失败: {str(e)}")
    
    def _load_filters_from_db(self, table_name: str, ref_id: Optional[str], ref_name: Optional[str]) -> Dict[str, Any]:
        """从数据库加载 filters"""
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                if ref_id:
                    sql = text(f"""
                        SELECT filters
                        FROM {self.db_schema}."{table_name}"
                        WHERE id = :ref_id
                        LIMIT 1
                    """)
                    row = conn.execute(sql, {"ref_id": ref_id}).fetchone()
                elif ref_name:
                    sql = text(f"""
                        SELECT filters
                        FROM {self.db_schema}."{table_name}"
                        WHERE name = :ref_name
                        LIMIT 1
                    """)
                    row = conn.execute(sql, {"ref_name": ref_name}).fetchone()
                else:
                    return {}
                
                if row and row.filters:
                    return row.filters if isinstance(row.filters, dict) else {}
        except Exception as e:
            print(f"从数据库加载 filters 失败: {e}")
        
        return {}
    
    def delete_knowledge_base(self, user_id: str, kb_name: str, hard_delete: bool = False, is_admin: bool = False) -> bool:
        """删除知识库

        Args:
            user_id: 当前用户ID
            kb_name: 知识库名称
            hard_delete: 是否硬删除（默认False）
                - False: 软删除，只更新状态为 deleted，保留数据和表
                - True: 硬删除，物理删除表和记录（管理员操作）
            is_admin: 当前用户是否是管理员（用于权限判断）

        Returns:
            是否删除成功
        """
        try:
            # 先从注册表查询知识库信息（获取实际的表名和所属用户）
            kb_info = self.repository.get_knowledge_base_by_kb_name(kb_name)

            if not kb_info:
                print(f"知识库不存在: {kb_name}")
                return False

            # 获取实际的表名和所属用户
            actual_table_name = kb_info.get("table_name")
            actual_user_id = kb_info.get("user_id")

            # 权限检查：普通用户只能删除自己的知识库，管理员可以删除任何知识库
            if not is_admin and actual_user_id != user_id:
                print(f"权限不足：用户 {user_id} 无权删除用户 {actual_user_id} 的知识库")
                return False

            # 从缓存中移除
            kb_key = f"{actual_user_id}_{kb_name}"
            if kb_key in self.knowledge_bases:
                del self.knowledge_bases[kb_key]

            if hard_delete:
                # 硬删除：从注册表物理删除 + 删除表
                self.repository.unregister_knowledge_base(actual_table_name, soft_delete=False)
                return self.repository.delete_knowledge_base_table(actual_table_name)
            else:
                # 软删除：只更新注册表状态，保留数据和表
                self.repository.unregister_knowledge_base(actual_table_name, soft_delete=True)
                return True
        except Exception as e:
            print(f"删除知识库失败: {e}")
            return False

    def import_files_from_file_system(
        self,
        user_id: str,
        kb_name: str,
        file_ids: List[str],
        chunking_rule: str = "fixed_size",
        chunk_size: int = 5000,
        chunk_overlap: int = 200,
        metadata: Optional[Dict[str, Any]] = None,
        is_admin: bool = False,
    ) -> List[Dict[str, Any]]:
        """从文件系统导入文件到知识库

        Args:
            user_id: 用户ID
            kb_name: 知识库名称
            file_ids: 文件ID列表
            chunking_rule: 分块规则
            chunk_size: 分块大小
            chunk_overlap: 分块重叠
            metadata: 额外的元数据
            is_admin: 是否是管理员（管理员可以导入任何用户的文件）

        Returns:
            导入结果列表
        """
        import requests
        from app.services.files.files_repository import files_repository

        # 获取知识库实例
        knowledge = self.get_or_load_knowledge(user_id=user_id, kb_name=kb_name)

        # 获取知识库中已存在的文件名列表（用于检查重名）
        existing_filenames = self._get_existing_filenames_in_knowledge_base(knowledge.vector_db.table_name, user_id)
        print(f"[DEBUG] 知识库中已存在的文件名: {existing_filenames}")

        results = []
        temp_paths = []

        try:
            # 遍历文件ID列表
            for file_id in file_ids:
                try:
                    # 从数据库获取文件信息
                    file_info = files_repository.get_file_by_id(file_id)

                    if not file_info:
                        results.append({
                            "status": "error",
                            "message": f"文件不存在或无权访问",
                            "file_id": file_id,
                            "user_id": user_id,
                        })
                        continue

                    # 验证文件所有者（管理员可以导入任何文件）
                    file_owner_id = file_info.get('user_id')
                    if not is_admin and file_owner_id != user_id:
                        results.append({
                            "status": "error",
                            "message": "文件不存在或无权访问",
                            "file_id": file_id,
                            "user_id": user_id,
                        })
                        continue

                    # 获取文件URL和文件名
                    file_url = file_info.get('file_url')
                    filename = file_info.get('file_name')

                    print(f"[DEBUG] 检查文件: {filename}, 在已存在列表中: {filename in existing_filenames}")

                    if not file_url or not filename:
                        results.append({
                            "status": "error",
                            "message": "文件信息不完整",
                            "file_id": file_id,
                            "user_id": user_id,
                        })
                        continue

                    # 检查同名文件（包括扩展名）
                    if filename in existing_filenames:
                        results.append({
                            "status": "error",
                            "message": f"文件名 '{filename}' 已存在于知识库中，不能重名",
                            "file_id": file_id,
                            "filename": filename,
                            "user_id": user_id,
                        })
                        continue

                    # 从OSS下载文件内容
                    response = requests.get(file_url, timeout=30)
                    if response.status_code != 200:
                        results.append({
                            "status": "error",
                            "message": f"从OSS下载文件失败，状态码: {response.status_code}",
                            "file_id": file_id,
                            "filename": filename,
                            "user_id": user_id,
                        })
                        continue

                    file_content = response.content

                    # 创建临时文件
                    file_ext = os.path.splitext(filename)[1]
                    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
                        tmp.write(file_content)
                        temp_path = tmp.name
                    temp_paths.append(temp_path)

                    # 验证嵌入器配置
                    embedder = knowledge.vector_db.embedder
                    if not embedder or not hasattr(embedder, 'id') or not embedder.id:
                        results.append({
                            "status": "error",
                            "message": "嵌入器配置错误：模型名称为空，请检查 embedder_model 参数",
                            "file_id": file_id,
                            "user_id": user_id,
                        })
                        continue

                    # 创建带分块的读取器
                    reader = create_chunking_reader(
                        file_extension=file_ext,
                        chunking_rule=chunking_rule,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        embedder=embedder,
                    )

                    # 构建文档元数据
                    doc_metadata = {
                        "user_id": user_id,
                        "filename": filename,
                        "file_id": file_id,
                        "chunking_rule": chunking_rule,
                        "chunk_size": chunk_size,
                        "uploaded_at": datetime.utcnow().isoformat(),
                        "source": "file_system",  # 标记来源为文件系统
                    }
                    if metadata:
                        doc_metadata.update(metadata)

                    # 添加文档到知识库（捕获嵌入API调用失败的错误）
                    try:
                        knowledge.add_content(path=temp_path, reader=reader, metadata=doc_metadata)
                    except ValueError as ve:
                        # 捕获向量维度错误（通常是嵌入API调用失败导致的）
                        error_msg = str(ve)
                        if "dimensions" in error_msg.lower():
                            results.append({
                                "status": "error",
                                "message": f"嵌入API调用失败，返回了空向量。请检查 OPENAI_API_KEY、OPENAI_BASE_URL 和 embedder_model 配置。错误详情: {ve}",
                                "file_id": file_id,
                                "user_id": user_id,
                            })
                            continue
                        raise
                    except Exception as api_err:
                        # 捕获其他API相关错误
                        error_msg = str(api_err)
                        if "403" in error_msg or "api" in error_msg.lower():
                            results.append({
                                "status": "error",
                                "message": f"嵌入API调用失败 ({error_msg})，请检查API配置",
                                "file_id": file_id,
                                "user_id": user_id,
                            })
                            continue
                        raise

                    # 更新文件的 kb_name 关联
                    files_repository.update_file(file_id, {"kb_name": kb_name})

                    # 确保 filters 字段包含 filename（用于后续检索）
                    table_name = knowledge.vector_db.table_name
                    self._update_filters_with_filename(table_name, filename, user_id)

                    # 成功导入后，更新 knowledge_base_registry 的 document_ids 数组
                    self._add_document_to_registry(table_name, file_id, filename)

                    results.append({
                        "status": "success",
                        "message": f"文档 {filename} 已成功导入知识库",
                        "filename": filename,
                        "file_id": file_id,
                        "user_id": user_id,
                    })

                except requests.exceptions.Timeout:
                    results.append({
                        "status": "error",
                        "message": "下载文件超时",
                        "file_id": file_id,
                        "user_id": user_id,
                    })
                except requests.exceptions.RequestException as e:
                    results.append({
                        "status": "error",
                        "message": f"下载文件失败: {str(e)}",
                        "file_id": file_id,
                        "user_id": user_id,
                    })
                except Exception as e:
                    results.append({
                        "status": "error",
                        "message": f"导入文件失败: {str(e)}",
                        "file_id": file_id,
                        "user_id": user_id,
                    })

            return results

        finally:
            # 清理临时文件
            for temp_path in temp_paths:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

    def _cleanup_orphaned_indexes(self, table_name: str):
        """清理可能残留的索引，防止创建新表时索引名冲突

        Args:
            table_name: 表名
        """
        try:
            # 直接获取原始 DBAPI 连接
            engine = get_sync_engine()
            raw_conn = engine.raw_connection()

            try:
                # 查找并删除所有与该表相关的残留索引
                # 索引命名模式通常是: idx_{table_name}_*
                # 注意：PostgreSQL 标识符限制 63 字节，长表名会导致索引名被截断
                safe_schema = self.db_schema.replace("'", "''")
                safe_pattern = f"idx_{table_name}%".replace("'", "''")

                # 使用原始 DBAPI 连接执行 SQL
                cursor = raw_conn.cursor()

                # 首先检查表是否存在，如果存在则不需要清理索引
                cursor.execute(
                    """
                        SELECT EXISTS (
                            SELECT 1
                            FROM information_schema.tables
                            WHERE table_schema = %s
                            AND table_name = %s
                        )
                    """,
                    (safe_schema, table_name)
                )
                table_exists = cursor.fetchone()[0]

                if table_exists:
                    # 表存在，不需要清理
                    print(f"表 {table_name} 已存在，跳过索引清理")
                    return

                # 表不存在，查找可能残留的孤儿索引
                cursor.execute(
                    """
                        SELECT indexname
                        FROM pg_indexes
                        WHERE schemaname = %s
                        AND indexname LIKE %s
                    """,
                    (safe_schema, safe_pattern)
                )

                indexes_to_drop = cursor.fetchall()

                for index_row in indexes_to_drop:
                    index_name = index_row[0]
                    try:
                        cursor.execute(
                            f'DROP INDEX IF EXISTS "{self.db_schema}"."{index_name}"'
                        )
                        raw_conn.commit()
                        print(f"清理残留索引: {index_name}")
                    except Exception as e:
                        print(f"清理索引 {index_name} 失败: {e}")

            finally:
                cursor.close()
                raw_conn.close()

        except Exception as e:
            print(f"清理残留索引过程出错: {e}")

    def remove_documents_from_knowledge_base(
        self,
        user_id: str,
        kb_name: str,
        file_ids: Optional[List[str]] = None,
        filenames: Optional[List[str]] = None,
        delete_from_file_system: bool = False,
    ) -> List[Dict[str, Any]]:
        """从知识库中删除文档（管理员专用）

        Args:
            user_id: 知识库所属用户ID
            kb_name: 知识库名称
            file_ids: 要删除的文件ID列表（与filenames二选一）
            filenames: 要删除的文件名列表（与file_ids二选一）
            delete_from_file_system: 是否同时从文件系统删除（business.files表）

        Returns:
            删除结果列表
        """
        if not file_ids and not filenames:
            return [{
                "status": "error",
                "message": "file_ids 和 filenames 必须提供其中一个"
            }]

        if file_ids and filenames:
            return [{
                "status": "error",
                "message": "file_ids 和 filenames 只能提供其中一个"
            }]

        from app.services.files.files_repository import files_repository

        # 获取知识库实例
        knowledge = self.get_or_load_knowledge(user_id=user_id, kb_name=kb_name)
        table_name = knowledge.vector_db.table_name

        results = []

        try:
            if file_ids:
                # 按 file_id 删除
                for file_id in file_ids:
                    try:
                        # 1. 从 business.files 获取文件信息
                        file_info = files_repository.get_file_by_id(file_id)

                        if not file_info:
                            results.append({
                                "status": "error",
                                "message": f"文件 {file_id} 不存在",
                                "file_id": file_id
                            })
                            continue

                        filename = file_info.get('file_name')
                        actual_user_id = file_info.get('user_id')

                        # 2. 验证文件是否属于该用户
                        if not is_admin and actual_user_id != user_id:
                            results.append({
                                "status": "error",
                                "message": f"文件 {file_id} 不属于用户 {user_id}",
                                "file_id": file_id
                            })
                            continue

                        # 3. 检查文件在知识库表中是否存在
                        engine = get_sync_engine()
                        doc_exists = False
                        with engine.connect() as conn:
                            check_sql = text(f"""
                                SELECT COUNT(*) as cnt
                                FROM "{self.db_schema}"."{table_name}"
                                WHERE (meta_data->>'filename' = :filename
                                   OR filters->>'filename' = :filename)
                                AND meta_data->>'user_id' = :actual_user_id
                            """)
                            check_result = conn.execute(check_sql, {"filename": filename, "user_id": actual_user_id})
                            doc_count = check_result.fetchone()[0]
                            doc_exists = doc_count > 0

                        # 4. 如果文档存在，从知识库表删除
                        if doc_exists:
                            self._delete_documents_from_table(table_name, actual_user_id, filename=filename)

                        # 5. 从 knowledge_base_registry 的 document_ids 中移除（无论文档是否存在）
                        self._remove_document_from_registry(table_name, file_id)

                        # 6. 如果需要，从文件系统删除
                        if delete_from_file_system:
                            files_repository.delete_file(file_id, permanent=True)
                            files_repository.update_file(file_id, {"kb_name": None})
                        else:
                            files_repository.update_file(file_id, {"kb_name": None})

                        # 7. 返回结果
                        if doc_exists:
                            results.append({
                                "status": "success",
                                "message": f"文件 {filename} 已从知识库删除",
                                "file_id": file_id,
                                "filename": filename
                            })
                        else:
                            results.append({
                                "status": "success",
                                "message": f"文件 {filename} 在知识库中不存在，已清理 registry 记录",
                                "file_id": file_id,
                                "filename": filename
                            })

                    except Exception as e:
                        results.append({
                            "status": "error",
                            "message": f"删除文件 {file_id} 失败: {str(e)}",
                            "file_id": file_id
                        })

            elif filenames:
                # 按 filename 删除
                for filename in filenames:
                    try:
                        # 1. 先检查该 filename 是否存在
                        engine = get_sync_engine()
                        with engine.connect() as conn:
                            # 检查文件是否存在（包括没有 file_id 的记录）
                            check_sql = text(f"""
                                SELECT COUNT(*) as cnt
                                FROM "{self.db_schema}"."{table_name}"
                                WHERE (meta_data->>'filename' = :filename
                                   OR filters->>'filename' = :filename)
                                AND meta_data->>'user_id' = :user_id
                            """)
                            check_result = conn.execute(check_sql, {"filename": filename, "user_id": user_id})
                            count = check_result.fetchone()[0]

                        # 2. 查询该 filename 对应的所有 file_id（用于更新文件系统和 registry）
                        with engine.connect() as conn:
                            sql = text(f"""
                                SELECT DISTINCT meta_data->>'file_id' as file_id
                                FROM "{self.db_schema}"."{table_name}"
                                WHERE (meta_data->>'filename' = :filename
                                   OR filters->>'filename' = :filename)
                                AND meta_data->>'user_id' = :user_id
                            """)
                            result = conn.execute(sql, {"filename": filename, "user_id": user_id})
                            file_ids_for_filename = [row[0] for row in result if row[0]]

                        if count == 0:
                            # 文件在知识库中不存在，但仍需清理 registry 中的记录
                            # 从 registry 表中查询该 filename 对应的所有 file_id
                            engine = get_sync_engine()
                            with engine.connect() as conn:
                                registry_sql = text("""
                                    SELECT doc->>'file_id' as file_id
                                    FROM knowledge.knowledge_base_registry
                                    CROSS JOIN jsonb_array_elements(document_ids) AS doc
                                    WHERE table_name = :table_name
                                    AND doc->>'filename' = :filename
                                """)
                                registry_result = conn.execute(
                                    registry_sql,
                                    {"table_name": table_name, "filename": filename}
                                )
                                file_ids_from_registry = [row[0] for row in registry_result if row[0]]

                            cleaned = 0
                            for file_id in file_ids_from_registry:
                                self._remove_document_from_registry(table_name, file_id)
                                cleaned += 1

                            results.append({
                                "status": "success",
                                "message": f"文件 {filename} 在知识库中不存在，已清理 registry 记录",
                                "filename": filename,
                                "cleaned_count": cleaned
                            })
                            continue

                        # 3. 从知识库表删除所有匹配的记录（按 filename）
                        self._delete_documents_from_table(table_name, user_id, filename=filename)

                        # 4. 从 registry 中移除所有相关的 file_id（如果有）
                        for file_id in file_ids_for_filename:
                            self._remove_document_from_registry(table_name, file_id)

                            # 如果需要，从文件系统删除
                            if delete_from_file_system:
                                files_repository.delete_file(file_id, permanent=True)
                            else:
                                files_repository.update_file(file_id, {"kb_name": None})

                        results.append({
                            "status": "success",
                            "message": f"文件 {filename} 已从知识库删除（共 {count} 个分块）",
                            "filename": filename,
                            "deleted_count": count
                        })

                    except Exception as e:
                        results.append({
                            "status": "error",
                            "message": f"删除文件 {filename} 失败: {str(e)}",
                            "filename": filename
                        })

        except Exception as e:
            results.append({
                "status": "error",
                "message": f"删除操作失败: {str(e)}"
            })

        return results

    def _delete_documents_from_table(
        self,
        table_name: str,
        user_id: str,
        file_id: Optional[str] = None,
        filename: Optional[str] = None
    ):
        """从知识库表中删除文档记录

        Args:
            table_name: 知识库表名
            user_id: 用户ID
            file_id: 文件ID（可选）
            filename: 文件名（可选，与file_id二选一）
        """
        try:
            engine = get_sync_engine()
            with engine.connect() as conn:
                if file_id:
                    # 按 file_id 删除
                    sql = text(f"""
                        DELETE FROM "{self.db_schema}"."{table_name}"
                        WHERE meta_data->>'file_id' = :file_id
                        AND meta_data->>'user_id' = :user_id
                    """)
                    conn.execute(sql, {"file_id": file_id, "user_id": user_id})
                elif filename:
                    # 按 filename 删除
                    sql = text(f"""
                        DELETE FROM "{self.db_schema}"."{table_name}"
                        WHERE (meta_data->>'filename' = :filename
                           OR filters->>'filename' = :filename)
                        AND meta_data->>'user_id' = :user_id
                    """)
                    conn.execute(sql, {"filename": filename, "user_id": user_id})

                conn.commit()
        except Exception as e:
            print(f"从知识库表删除文档失败: {e}")
            raise


# 全局服务实例
knowledge_service = KnowledgeService()

