"""
动态知识库检索工具（系统知识库）

支持：
- 从启动时预加载的系统知识库缓存中检索
- 并行向量检索所有系统知识库（限制并发数）
- 返回 Top 3 结果
- 智能筛选相关知识库
- LRU 缓存常见查询结果

性能优化：
- 使用信号量限制并发数，避免线程池耗尽
- 通过环境变量 KB_MAX_CONCURRENCY 控制并发数（默认 2）
- 适用于多核服务器（4核、8核等）
"""
import asyncio
import hashlib
import logging
import os
from functools import lru_cache
from typing import Dict, List

from agno.tools import tool

logger = logging.getLogger(__name__)

# ✅ 从环境变量读取最大并发数（默认 4）
KB_MAX_CONCURRENCY = int(os.getenv("KB_MAX_CONCURRENCY", "4"))


class DynamicKnowledgeSearcher:
    """动态知识库搜索器（系统知识库）"""

    def __init__(
        self,
        user_id: str = "default",
        max_results_per_kb: int = 3,
        max_total_results: int = 3,  # 默认返回 Top 3
        enable_cache: bool = True,  # ✅ 启用缓存
        cache_size: int = 100,  # ✅ 缓存大小
    ):
        self.user_id = user_id
        self.max_results_per_kb = max_results_per_kb
        self.max_total_results = max_total_results
        self.enable_cache = enable_cache

        # ✅ LRU 缓存（通过字典模拟）
        self._cache = {}
        self._cache_keys = []  # 缓存键队列（用于 LRU 淘汰）
        self._cache_size = cache_size

        # ✅ 缓存统计
        self._cache_hits = 0
        self._cache_misses = 0

        # ✅ 查询词向量缓存（避免重复向量化）
        self._query_vectors = {}

    def _get_cache_key(self, query: str) -> str:
        """生成缓存键"""
        # 使用 MD5 哈希查询词
        return hashlib.md5(query.encode('utf-8')).hexdigest()

    def _get_from_cache(self, query: str) -> str:
        """从缓存获取结果（LRU 淘汰机制）"""
        if not self.enable_cache:
            return None

        cache_key = self._get_cache_key(query)
        if cache_key in self._cache:
            self._cache_hits += 1
            logger.info(f"[动态知识库] ✅ 缓存命中: {query} (命中次数: {self._cache_hits})")

            # 更新缓存顺序（LRU）：将访问的键移到队列末尾
            self._cache_keys.remove(cache_key)
            self._cache_keys.append(cache_key)

            return self._cache[cache_key]

        self._cache_misses += 1
        logger.info(f"[动态知识库] ❌ 缓存未命中: {query} (未命中次数: {self._cache_misses})")
        return None

    def _save_to_cache(self, query: str, result: str):
        """保存结果到缓存（LRU 淘汰机制）"""
        if not self.enable_cache:
            return

        cache_key = self._get_cache_key(query)

        # 如果缓存已满，淘汰最旧的缓存项（LRU）
        if len(self._cache_keys) >= self._cache_size:
            oldest_key = self._cache_keys.pop(0)  # 移除队列头部（最久未使用）
            del self._cache[oldest_key]
            logger.info(f"[动态知识库] 🗑️  淘汰最旧缓存 (缓存大小: {len(self._cache_keys)}/{self._cache_size})")

        # 添加到缓存和队列末尾
        self._cache[cache_key] = result
        self._cache_keys.append(cache_key)
        logger.info(f"[动态知识库] 💾 保存到缓存 (缓存大小: {len(self._cache_keys)}/{self._cache_size})")

    def get_cache_stats(self) -> dict:
        """获取缓存统计信息"""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": f"{hit_rate:.2f}%",
            "cache_size": len(self._cache_keys),
            "max_cache_size": self._cache_size,
        }

    def search(self, query: str, kb_name: str = "") -> str:
        """
        搜索知识库（并行检索 + LRU 缓存）

        流程：
        1. 检查缓存
        2. 如果指定了 kb_name，优先从该知识库检索
        3. 如果未指定或结果不足，智能筛选相关知识库进行检索
        4. 并行检索知识库
        5. 合并结果，返回 Top 3
        6. 保存到缓存

        Args:
            query: 搜索查询
            kb_name: 可选，指定要搜索的知识库名称

        Returns:
            str: 搜索结果（格式化的文本）
        """
        try:
            #  优化2: 检查缓存
            cached_result = self._get_from_cache(query)
            if cached_result is not None:
                return cached_result

            from app.services.knowledge.system_kb_cache import system_kb_cache
            from app.services.knowledge.knowledge_service import knowledge_service

            logger.info(f"[动态知识库] 开始搜索，查询: {query}, 指定知识库: {kb_name or '无'}")

            # ========== 获取所有知识库 ==========
            async def search_all_system_kbs():
                """并行检索知识库"""
                # 步骤1: 获取所有系统知识库信息
                logger.info(f"[动态知识库] 获取系统知识库信息")

                system_kb_names = system_kb_cache.get_all_system_kb_names()
                system_kb_infos = system_kb_cache.get_all_system_kb_info()

                # 构建知识库列表
                system_kb_list = []
                system_kb_cache_dict = {}
                for kb_info in system_kb_infos:
                    kb_name = kb_info["name"]
                    system_kb_list.append({
                        "name": kb_name,
                        "type": "system",
                        "description": kb_info.get("description", ""),
                    })
                    system_kb_cache_dict[kb_name] = system_kb_cache.get_system_kb(kb_name)

                logger.info(f"[动态知识库] 找到 {len(system_kb_list)} 个系统知识库")

                #  如果指定了知识库名称，优先加载该知识库
                if kb_name:
                    logger.info(f"[动态知识库] 📌 指定优先检索知识库: {kb_name}")

                    # 尝试从系统知识库缓存中获取
                    specified_kb = system_kb_cache_dict.get(kb_name)

                    # 如果不在系统知识库中，尝试作为用户知识库加载
                    if not specified_kb:
                        try:
                            logger.info(f"[动态知识库] 尝试加载用户知识库: {kb_name}")
                            specified_kb = knowledge_service.get_or_load_knowledge(
                                user_id=self.user_id,
                                kb_name=kb_name
                            )
                            if specified_kb:
                                # 将用户知识库添加到缓存字典中
                                system_kb_cache_dict[kb_name] = specified_kb
                                logger.info(f"[动态知识库] ✅ 成功加载用户知识库: {kb_name}")
                        except Exception as e:
                            logger.warning(f"[动态知识库] 加载用户知识库 {kb_name} 失败: {e}")

                    # 如果找到了指定的知识库，将其放在最前面
                    if specified_kb:
                        # 将指定知识库单独处理，优先搜索
                        ordered_kb_names = [kb_name] + [name for name in system_kb_cache_dict.keys() if name != kb_name]
                        logger.info(f"[动态知识库] 🔍 搜索优先级: 指定知识库 {kb_name} 优先")
                    else:
                        logger.warning(f"[动态知识库] ⚠️ 未找到指定的知识库: {kb_name}，将搜索所有知识库")
                        ordered_kb_names = list(system_kb_cache_dict.keys())
                else:
                    # 未指定知识库，搜索所有知识库
                    ordered_kb_names = list(system_kb_cache_dict.keys())
                    logger.info(f"[动态知识库] 搜索所有 {len(ordered_kb_names)} 个知识库")

                # 步骤2: 真正的并行检索知识库（使用线程池）
                async def search_single_kb(kb_name: str) -> List[Dict]:
                    """搜索单个知识库（在线程池中执行）"""
                    try:
                        kb_instance = system_kb_cache_dict.get(kb_name)
                        if not kb_instance:
                            logger.warning(f"[动态知识库] 知识库 {kb_name} 未找到实例")
                            return []

                        logger.info(f"[动态知识库] 🔄 在线程池中搜索知识库: {kb_name}")

                        # ✅ 将同步的 search 调用放到线程池中，实现真正的并行
                        loop = asyncio.get_event_loop()
                        documents = await loop.run_in_executor(
                            None,  # 使用默认线程池
                            kb_instance.search,
                            query,
                            self.max_results_per_kb,
                        )

                        logger.info(f"[动态知识库] 知识库 {kb_name} 返回 {len(documents) if documents else 0} 个结果")

                        if not documents:
                            return []

                        results = []
                        for doc in documents:
                            # 提取文件名（从 Document 对象的元数据中）
                            filename = None

                            # 尝试从多个可能的字段中提取文件名
                            if hasattr(doc, 'meta_data') and isinstance(doc.meta_data, dict):
                                filename = doc.meta_data.get('filename')

                            if not filename and hasattr(doc, 'data') and isinstance(doc.data, dict):
                                filename = doc.data.get('filename')

                            if not filename and hasattr(doc, 'meta') and isinstance(doc.meta, dict):
                                filename = doc.meta.get('filename')

                            # 如果仍然没有文件名，使用文档名称或其他标识
                            if not filename:
                                filename = getattr(doc, 'name', None)

                            # 兜底：使用知识库名称作为文件名
                            if not filename:
                                filename = f"{kb_name}_文档"

                            results.append({
                                "content": doc.content if hasattr(doc, 'content') else str(doc),
                                "filename": filename,  # ✅ 添加文件名字段
                                "kb_name": kb_name,
                                "kb_type": "system",
                                "score": getattr(doc, 'score', 0),
                            })

                        return results

                    except Exception as e:
                        logger.error(f"[动态知识库] 搜索知识库 {kb_name} 失败: {e}", exc_info=True)
                        return []

                # 并行检索知识库（限制并发数，避免线程池耗尽）
                logger.info(f"[动态知识库] 🚀 开始并行检索 {len(ordered_kb_names)} 个知识库（最大并发: {KB_MAX_CONCURRENCY}）")

                # ✅ 从环境变量读取并发限制（默认 2）
                semaphore = asyncio.Semaphore(KB_MAX_CONCURRENCY)

                async def search_single_kb_with_limit(kb_name: str):
                    """带并发限制的搜索"""
                    async with semaphore:
                        return await search_single_kb(kb_name)

                tasks = [search_single_kb_with_limit(kb_name) for kb_name in ordered_kb_names]
                results_list = await asyncio.gather(*tasks, return_exceptions=True)

                logger.info(f"[动态知识库] ✅ 并行检索 {len(tasks)} 个知识库完成")

                # 合并结果
                all_results = []
                for results in results_list:
                    if isinstance(results, Exception):
                        logger.error(f"[动态知识库] 搜索任务失败: {results}")
                        continue
                    if isinstance(results, list):
                        all_results.extend(results)

                return all_results, system_kb_list

            # 执行并行检索
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            all_results, all_knowledge_bases = loop.run_until_complete(search_all_system_kbs())

            # ========== 合并结果并返回 Top 3 ==========
            if not all_results:
                logger.warning(f"[动态知识库] 未找到相关内容")
                return "未找到相关内容。建议：\n1. 检查知识库中是否有相关文档\n2. 尝试更换搜索关键词"

            # 按相关性排序并返回 Top 3
            all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
            all_results = all_results[:self.max_total_results]

            logger.info(f"[动态知识库] 搜索完成，返回 {len(all_results)} 个结果")

            # 格式化结果
            formatted_result = self._format_results(all_results)

            # ✅ 保存到缓存（LRU 淘汰机制）
            self._save_to_cache(query, formatted_result)

            # ✅ 输出缓存统计（每10次查询输出一次）
            total_requests = self._cache_hits + self._cache_misses
            if total_requests % 10 == 0:
                stats = self.get_cache_stats()
                logger.info(f"[动态知识库] 📊 缓存统计: {stats}")

            return formatted_result

        except Exception as e:
            logger.error(f"[动态知识库] 搜索失败: {e}", exc_info=True)
            return f"知识库搜索出错: {str(e)}"

    def _format_results(self, results: List[Dict]) -> str:
        """
        格式化搜索结果

        Args:
            results: 搜索结果列表

        Returns:
            格式化的字符串（包含JSON元数据用于解析）
        """
        result_parts = []
        result_parts.append(f"从 {len(results)} 个相关文档中找到答案：\n")

        # 构建文件信息列表（用于日志解析）
        file_info_list = []

        for i, result in enumerate(results, 1):
            content = result['content']
            if len(content) > 500:
                content = content[:500] + "..."
            result_parts.append(
                f"{i}. **{result['kb_name']}**\n"
                f"{content}\n"
            )

            # 收集文件信息（用于日志解析）
            file_info = {
                "filename": result.get("filename", result.get("name", "未知文件")),
                "kb_name": result.get("kb_name", ""),
                "kb_type": result.get("kb_type", ""),
                "score": result.get("score", 0),
            }
            file_info_list.append(file_info)

        # 在结果末尾添加JSON格式的文件信息（用于解析）
        import json
        result_parts.append(f"\n\n---REFERENCES---\n{json.dumps(file_info_list, ensure_ascii=False)}\n---END-REFERENCES---")

        return "\n".join(result_parts)


# 全局搜索器缓存
_searcher_cache: Dict[str, DynamicKnowledgeSearcher] = {}


def get_or_create_searcher(
    user_id: str,
    max_results_per_kb: int = 3,
    max_total_results: int = 10,
) -> DynamicKnowledgeSearcher:
    """获取或创建搜索器实例"""
    cache_key = f"{user_id}_{max_results_per_kb}_{max_total_results}"

    if cache_key not in _searcher_cache:
        _searcher_cache[cache_key] = DynamicKnowledgeSearcher(
            user_id=user_id,
            max_results_per_kb=max_results_per_kb,
            max_total_results=max_total_results,
        )

    return _searcher_cache[cache_key]


def create_dynamic_knowledge_toolkit(
    user_id: str = "default",
    max_results_per_kb: int = 3,
    max_total_results: int = 10,
    cache_size: int = 100,  # ✅ 可配置缓存大小
) -> List:
    """
    创建动态知识库工具集

    Args:
        user_id: 用户ID（保留兼容性，实际未使用）
        max_results_per_kb: 每个知识库最多返回结果数
        max_total_results: 总共最多返回结果数
        cache_size: 缓存大小（默认100，建议值）
                      - 小型应用（<1000 DAU）：100
                      - 中型应用（1000-10000 DAU）：300-500
                      - 大型应用（>10000 DAU）：1000

    Returns:
        List[Function]: 工具列表
    """

    # 获取或创建搜索器
    searcher = get_or_create_searcher(
        user_id=user_id,
        max_results_per_kb=max_results_per_kb,
        max_total_results=max_total_results,
    )

    # ✅ 动态设置缓存大小
    searcher._cache_size = cache_size
    logger.info(f"[动态知识库] 缓存大小设置为: {cache_size}")

    # 创建工具函数
    def search_all_knowledge_bases(query: str, kb_name: str = "") -> str:
        """
        搜索知识库中的相关信息。

        使用场景：
        - 用户询问具体的政策、法规、流程时使用此工具
        - 需要从知识库中查找准确信息时使用此工具
        - 不确定答案时，使用此工具检索专业知识

        知识库选择策略：
        - 默认情况：不传入 kb_name，将并行搜索所有系统知识库
        - 指定知识库：传入 kb_name 参数，将优先搜索指定知识库

        何时指定 kb_name（重要）：
        - 用户问题与税务无关（如系统使用、文档处理、账户管理等）时，
          必须指定 kb_name="kb_user_268_0697300c"
        - 用户明确指定了要查询的知识库名称时

        示例：
        - 税务问题：search_all_knowledge_bases("增值税税率是多少？")
        - 非税务问题：search_all_knowledge_bases("帮我处理文档", kb_name="kb_user_268_0697300c")

        Args:
            query: 搜索查询（关键词或问题）
            kb_name: 可选，指定要搜索的知识库名称
                    - 非税务问题必须指定 kb_name="kb_user_268_0697300c"
                    - 税务问题不传此参数，搜索所有知识库

        Returns:
            str: 格式化的搜索结果，包含相关文档内容和来源信息
        """
        return searcher.search(query, kb_name=kb_name)

    # 使用 @tool 装饰器创建工具
    search_tool = tool(search_all_knowledge_bases)

    return [search_tool]
