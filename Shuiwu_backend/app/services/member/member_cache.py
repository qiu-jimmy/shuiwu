"""
会员信息状态管理服务

【修改说明】：
为了解决多进程环境下 (Uvicorn workers > 1) 内存字典不共享导致的状态不一致问题，
以及避免引入 Redis 带来的运维复杂度，本项目已废弃所有本地字典缓存。

所有与会员相关的状态（权益、统计、基本信息）改为直接穿透查询数据库。
由于系统使用 SQLAlchemy 连接池且查询均为轻量级的索引/主键查询，
在当前量级下直接查询数据库的性能损耗可以忽略不计。

本文件保留原本的 API 签名，并统一通过一个“空缓存”占位类进行兼容。
"""
from typing import Dict, Any, Optional

class DummyMemberCache:
    """空缓存：不保存任何数据，强制业务走数据库查询"""

    def __init__(self):
        pass

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        return None

    def set(self, key: str, value: Dict[str, Any]) -> None:
        pass

    def delete(self, key: str) -> None:
        pass

    def clear_user_cache(self, user_id: str) -> None:
        pass

    def clear_all(self) -> None:
        pass

    # ==================== 便捷方法 ====================

    def get_member_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        return None

    def set_member_info(self, user_id: str, info: Dict[str, Any]) -> None:
        pass

    def get_member_stats(self, user_id: str) -> Optional[Dict[str, Any]]:
        return None

    def set_member_stats(self, user_id: str, stats: Dict[str, Any]) -> None:
        pass

    def get_privilege_check(self, user_id: str, privilege_type: str) -> Optional[Dict[str, Any]]:
        return None

    def set_privilege_check(self, user_id: str, privilege_type: str, result: Dict[str, Any]) -> None:
        pass


# 全局实例替换为 DummyCache，对外接口不变
member_cache = DummyMemberCache()


# ==================== 缓存装饰器 ====================
# 将所有的装饰器改为透传(Pass-through)，确保每次执行原函数直接查询数据库

def cached_member_info(func):
    """【已废弃缓存功能】直接执行原函数查询数据库"""
    def wrapper(user_id: str, *args, **kwargs):
        return func(user_id, *args, **kwargs)
    return wrapper


def cached_member_stats(func):
    """【已废弃缓存功能】直接执行原函数查询数据库"""
    def wrapper(user_id: str, *args, **kwargs):
        return func(user_id, *args, **kwargs)
    return wrapper


def cached_privilege_check(func):
    """【已废弃缓存功能】直接执行原函数查询数据库"""
    def wrapper(user_id: str, privilege_type: str, *args, **kwargs):
        return func(user_id, privilege_type, *args, **kwargs)
    return wrapper
