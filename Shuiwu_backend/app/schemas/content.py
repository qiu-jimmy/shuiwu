"""
内容管理相关的 Pydantic 模型（轮播图、公告等）
"""
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime


# ==================== 轮播图管理 ====================

class BannerCreate(BaseModel):
    """创建轮播图"""
    title: Optional[str] = None
    image_url: str
    link_url: Optional[str] = None
    link_type: str = "none"  # none, internal, external, mini_program
    sort_order: Optional[int] = 0
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class BannerUpdate(BaseModel):
    """更新轮播图"""
    title: Optional[str] = None
    image_url: Optional[str] = None
    link_url: Optional[str] = None
    link_type: Optional[str] = None
    sort_order: Optional[int] = None
    status: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class BannerResponse(BaseModel):
    """轮播图响应"""
    banner_id: str
    title: Optional[str] = None
    image_url: str
    link_url: Optional[str] = None
    link_type: str
    sort_order: int
    status: str
    view_count: int
    click_count: int
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BannerListResponse(BaseModel):
    """轮播图列表响应"""
    banners: List[BannerResponse]


class BannerViewRequest(BaseModel):
    """轮播图浏览/点击"""
    banner_id: str
    action: str  # view, click


# ==================== 系统公告 ====================

class AnnouncementCreate(BaseModel):
    """创建系统公告"""
    title: str
    content: str
    announcement_type: str = "system"  # system, activity, maintenance
    priority: Optional[int] = 0
    target_users: Optional[str] = "all"  # all, vip, enterprise
    publish_time: Optional[str] = None


class AnnouncementUpdate(BaseModel):
    """更新系统公告"""
    title: Optional[str] = None
    content: Optional[str] = None
    announcement_type: Optional[str] = None
    priority: Optional[int] = None
    target_users: Optional[str] = None
    status: Optional[str] = None
    publish_time: Optional[str] = None


class AnnouncementResponse(BaseModel):
    """系统公告响应"""
    announcement_id: str
    title: str
    content: str
    announcement_type: str
    priority: int
    target_users: str
    status: str
    view_count: int
    publish_time: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AnnouncementListResponse(BaseModel):
    """系统公告列表响应"""
    total: int
    page: int
    page_size: int
    announcements: List[AnnouncementResponse]


class AnnouncementDetailResponse(BaseModel):
    """系统公告详情响应"""
    announcement: AnnouncementResponse
    is_viewed: bool = False
