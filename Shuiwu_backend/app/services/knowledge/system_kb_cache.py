"""
系统知识库缓存管理器

在项目启动时预加载所有系统知识库到内存缓存，避免重复加载。
"""
import logging
from typing import Dict, List, Optional

from agno.knowledge.knowledge import Knowledge

from app.services.knowledge.knowledge_service import knowledge_service

logger = logging.getLogger(__name__)


class SystemKnowledgeBaseCache:
    """系统知识库缓存管理器"""

    def __init__(self):
        self._cache: Dict[str, Knowledge] = {}  # kb_name -> Knowledge 实例
        self._kb_info: Dict[str, dict] = {}  # kb_name -> 知识库元信息
        self._loaded = False

    def load_all_system_knowledge_bases(self, default_user_id: str = "system") -> int:
        """
        加载所有系统知识库到缓存

        Args:
            default_user_id: 默认用户ID（用于权限检查）

        Returns:
            成功加载的知识库数量
        """
        if self._loaded:
            logger.info("[系统知识库缓存] 已经加载过，跳过")
            return len(self._cache)

        try:
            logger.info("[系统知识库缓存] 开始加载所有系统知识库...")

            # 获取所有系统知识库
            all_kbs = knowledge_service.list_knowledge_bases(user_id=None)
            system_kbs = [kb for kb in all_kbs if kb.get("is_system", False)]

            logger.info(f"[系统知识库缓存] 找到 {len(system_kbs)} 个系统知识库")

            loaded_count = 0
            for kb_info in system_kbs:
                kb_name = kb_info.get("kb_name")
                if not kb_name:
                    continue

                try:
                    # 加载知识库实例
                    kb_instance = knowledge_service.get_or_load_knowledge(
                        user_id=default_user_id,
                        kb_name=kb_name
                    )

                    if kb_instance:
                        self._cache[kb_name] = kb_instance
                        self._kb_info[kb_name] = {
                            "name": kb_name,
                            "type": "system",
                            "description": kb_info.get("description", ""),
                            "created_at": kb_info.get("created_at"),
                        }
                        loaded_count += 1
                        logger.info(f"[系统知识库缓存] 成功加载: {kb_name}")

                except Exception as e:
                    logger.error(f"[系统知识库缓存] 加载 {kb_name} 失败: {e}", exc_info=True)
                    continue

            self._loaded = True
            logger.info(f"[系统知识库缓存] 加载完成，成功加载 {loaded_count}/{len(system_kbs)} 个知识库")

            return loaded_count

        except Exception as e:
            logger.error(f"[系统知识库缓存] 批量加载失败: {e}", exc_info=True)
            self._loaded = True  # 标记为已加载，避免重复尝试
            return 0

    def get_system_kb(self, kb_name: str) -> Optional[Knowledge]:
        """
        从缓存获取系统知识库实例

        Args:
            kb_name: 知识库名称

        Returns:
            Knowledge 实例，如果不存在返回 None
        """
        return self._cache.get(kb_name)

    def get_all_system_kb_names(self) -> List[str]:
        """
        获取所有系统知识库名称

        Returns:
            知识库名称列表
        """
        return list(self._cache.keys())

    def get_all_system_kb_info(self) -> List[dict]:
        """
        获取所有系统知识库的元信息

        Returns:
            知识库元信息列表
        """
        return list(self._kb_info.values())

    def get_system_kb_info(self, kb_name: str) -> Optional[dict]:
        """
        获取指定系统知识库的元信息

        Args:
            kb_name: 知识库名称

        Returns:
            知识库元信息，如果不存在返回 None
        """
        return self._kb_info.get(kb_name)

    def is_loaded(self) -> bool:
        """检查是否已加载"""
        return self._loaded

    def reload_kb(self, kb_name: str, default_user_id: str = "system") -> bool:
        """
        重新加载指定的系统知识库

        Args:
            kb_name: 知识库名称
            default_user_id: 默认用户ID

        Returns:
            是否成功
        """
        try:
            logger.info(f"[系统知识库缓存] 重新加载: {kb_name}")

            kb_instance = knowledge_service.get_or_load_knowledge(
                user_id=default_user_id,
                kb_name=kb_name
            )

            if kb_instance:
                self._cache[kb_name] = kb_instance
                logger.info(f"[系统知识库缓存] 重新加载成功: {kb_name}")
                return True

            return False

        except Exception as e:
            logger.error(f"[系统知识库缓存] 重新加载失败 {kb_name}: {e}", exc_info=True)
            return False

    def clear_cache(self):
        """清空缓存"""
        logger.info("[系统知识库缓存] 清空缓存")
        self._cache.clear()
        self._kb_info.clear()
        self._loaded = False


# 全局单例
system_kb_cache = SystemKnowledgeBaseCache()
