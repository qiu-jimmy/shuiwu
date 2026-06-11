"""
分销推广模块
"""
# 完整实现需要修复 distribution_repository.py 的数据库连接问题

from .distribution_service import distribution_service

__all__ = ['distribution_service']
