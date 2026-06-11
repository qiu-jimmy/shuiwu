"""
会员权限装饰器实际应用示例

使用系统中已有的API端点演示权限装饰器的使用
"""
from fastapi import APIRouter, Request
from app.middleware.permission import (
    require_privilege,
    require_quota,
    require_member_level,
    require_any_privilege,
    require_all_privileges,
)
from app.utils.response import response

router = APIRouter(prefix="/api/examples/permission", tags=["权限示例"])


# ==================== 示例1: RAG聊天接口 - 使用现有端点 ====================
# 原端点: /api/chat/rag
# 需要的权限: RAG功能权限 + 每日聊天配额

@router.post("/rag-chat-demo")
@require_privilege("rag")        # 自动检查RAG功能权限
@require_quota("daily_chats")    # 自动检查每日聊天配额
async def rag_chat_demo(request: Request, message: str):
    """
    RAG聊天演示（带权限控制）

    对应实际端点: POST /api/chat/rag

    权限要求:
    - 用户套餐必须启用 enable_rag
    - 每日聊天次数未达上限

    如果权限不足，装饰器会自动返回:
    - "当前套餐不支持RAG功能"
    - "今日聊天次数已达上限"
    """
    # 业务逻辑：直接写代码，不需要任何权限检查代码
    # 这里模拟调用实际的chat服务
    return response.success(data={
        "message": f"这是RAG回复：{message}",
        "type": "rag",
        "user_id": request.state.user_id,
        "note": "权限检查和配额验证已由装饰器自动完成"
    })


# ==================== 示例2: 网络搜索聊天 - 使用现有端点 ====================
# 原端点: /api/chat/chat-with-search
# 需要的权限: 网络搜索功能权限 + 每日聊天配额

@router.post("/search-chat-demo")
@require_privilege("web_search")  # 自动检查网络搜索权限
@require_quota("daily_chats")     # 自动检查每日聊天配额
async def search_chat_demo(request: Request, message: str):
    """
    网络搜索聊天演示（带权限控制）

    对应实际端点: POST /api/chat/chat-with-search

    权限要求:
    - 用户套餐必须启用 enable_web_search
    - 每日聊天次数未达上限
    """
    return response.success(data={
        "message": f"网络搜索回复：{message}",
        "type": "search",
        "search_engines": ["百度", "DuckDuckGo"],
        "user_id": request.state.user_id,
        "note": "权限检查已自动完成"
    })


# ==================== 示例3: 全功能聊天 - 使用现有端点 ====================
# 原端点: /api/chat/full-feature
# 需要的权限: RAG + 网络搜索 + MCP工具 + 每日聊天配额

@router.post("/full-chat-demo")
@require_member_level("premium")               # 需要premium会员
@require_all_privileges(["rag", "web_search"]) # 需要RAG和搜索权限
@require_quota("daily_chats")                  # 需要聊天配额
async def full_chat_demo(request: Request, message: str):
    """
    全功能聊天演示（带权限控制）

    对应实际端点: POST /api/chat/full-feature

    权限要求（按顺序检查）:
    1. 会员等级 >= premium
    2. 同时具备RAG和网络搜索权限
    3. 每日聊天配额未用完
    """
    return response.success(data={
        "message": f"全功能回复：{message}",
        "type": "full",
        "features": ["RAG", "网络搜索", "多模态支持"],
        "user_id": request.state.user_id,
        "note": "所有权限检查已自动完成"
    })


# ==================== 示例4: 创建知识库 - 使用现有端点 ====================
# 原端点: /api/knowledge-base/create
# 需要的权限: 知识库数量配额

@router.post("/create-kb-demo")
@require_quota("kb_count")  # 检查知识库数量配额
async def create_kb_demo(
    request: Request,
    name: str,
    description: str = None
):
    """
    创建知识库演示（带权限控制）

    对应实际端点: POST /api/knowledge-base/create

    权限要求:
    - 知识库数量 < 套餐上限

    如果已达上限，自动返回:
    - "知识库数量不足，剩余: 0，请升级会员"
    """
    return response.success(data={
        "kb_id": f"kb_{request.state.user_id}_{name}",
        "name": name,
        "description": description,
        "user_id": request.state.user_id,
        "note": "知识库配额检查已自动完成"
    })


# ==================== 示例5: 上传文档 - 使用现有端点 ====================
# 原端点: /api/knowledge-base/upload-document
# 需要的权限: 知识库文档数配额 + 文件存储空间配额

@router.post("/upload-doc-demo")
@require_quota("kb_documents")       # 检查文档数量配额
@require_quota("file_storage_mb", consume=5)  # 检查存储空间（预计5MB）
async def upload_doc_demo(request: Request):
    """
    上传文档演示（带权限控制）

    对应实际端点: POST /api/knowledge-base/upload-document

    权限要求:
    1. 知识库文档数 < 套餐上限
    2. 存储空间剩余 >= 5MB

    如果配额不足，自动返回:
    - "知识库文档数不足，剩余: X，需要: 1"
    - "文件存储空间不足，剩余: X MB，需要: 5 MB"
    """
    return response.success(data={
        "doc_id": f"doc_{request.state.user_id}_123",
        "filename": "example.pdf",
        "size_mb": 5,
        "user_id": request.state.user_id,
        "note": "文档数量和存储空间配额检查已自动完成"
    })


# ==================== 示例6: 高级功能 - MCP工具 ====================
# 原端点: 可能是未来的 /api/chat/mcp
# 需要的权限: MCP工具权限 + premium会员

@router.post("/mcp-tools-demo")
@require_member_level("premium")      # 需要premium会员
@require_privilege("mcp_tools")       # 需要MCP工具权限
@require_quota("daily_chats")        # 需要聊天配额
async def mcp_tools_demo(request: Request, message: str):
    """
    MCP工具演示（带权限控制）

    权限要求:
    1. 会员等级 >= premium
    2. 用户套餐必须启用 enable_mcp_tools
    3. 每日聊天配额未用完

    适用场景:
    - 企业级应用
    - 高级用户
    - 需要外部工具集成
    """
    return response.success(data={
        "message": f"MCP工具回复：{message}",
        "type": "mcp",
        "available_tools": ["calculator", "weather", "news"],
        "user_id": request.state.user_id,
        "note": "MCP工具权限检查已自动完成"
    })


# ==================== 示例7: 智能聊天 - 满足任一权限即可 ====================
# 综合多种聊天方式，用户有任一权限即可使用

@router.post("/smart-chat-demo")
@require_any_privilege(["rag", "web_search"])  # 有RAG或搜索任一权限即可
@require_quota("daily_chats")
async def smart_chat_demo(request: Request, message: str):
    """
    智能聊天演示（OR逻辑）

    权限要求:
    - 有RAG权限 或 网络搜索权限（满足其一即可）
    - 每日聊天配额未用完

    适用场景:
    - 提供多种方式实现同一功能
    - 用户有任一权限都能使用
    - 提升用户体验和灵活性
    """
    # 根据用户权限选择合适的聊天方式
    return response.success(data={
        "message": f"智能回复：{message}",
        "type": "smart",
        "available_features": ["根据用户权限自动选择"],
        "user_id": request.state.user_id,
        "note": "只要有RAG或网络搜索任一权限即可"
    })


# ==================== 示例8: 权限检查演示 ====================
# 演示不同权限等级的用户能访问什么功能

@router.get("/check-permissions-demo")
async def check_permissions_demo(request: Request):
    """
    检查当前用户的所有权限

    演示端点，展示如何获取和使用权限信息
    """
    from app.services.member.member_service import member_service

    user_id = request.state.user_id

    # 获取会员信息
    member_info = member_service.get_member_info(user_id)

    # 获取会员统计
    member_stats = member_service.get_member_stats(user_id)

    # 检查各种权限
    privileges_to_check = ["rag", "web_search", "mcp_tools"]
    privilege_results = {}

    for privilege in privileges_to_check:
        result = member_service.check_privilege(user_id, privilege)
        privilege_results[privilege] = result.get("has_privilege", False)

    return response.success(data={
        "user_id": user_id,
        "member_level": member_info.get("member_level"),
        "member_expire_at": member_info.get("member_expire_at"),
        "privileges": privilege_results,
        "quotas": {
            "today_chats": member_stats.get("today_chats", 0),
            "max_daily_chats": member_stats.get("max_daily_chats", 0),
            "kb_count": member_stats.get("kb_count", 0),
            "max_kb_count": member_stats.get("max_kb_count", 0),
        },
        "available_features": [
            feature for feature, has_permission in privilege_results.items()
            if has_permission
        ]
    })


# ==================== 示例9: 不自动记录使用量 ====================
# 某些场景需要手动控制记录时机

@router.post("/manual-record-demo")
@require_privilege("rag", auto_record=False)  # 不自动记录
async def manual_record_demo(request: Request, message: str):
    """
    手动记录使用演示

    不自动记录使用量，适用于:
    - 需要手动控制记录时机
    - 按照实际结果决定是否记录
    - 特殊的业务场景
    """
    from app.services.member.member_service import member_service

    # 执行业务逻辑
    success = True  # 假设执行成功

    if success:
        # 根据结果决定是否记录
        member_service.record_usage(
            request.state.user_id,
            "rag",
            1
        )

    return response.success(data={
        "message": f"RAG回复：{message}",
        "note": "使用量已手动记录"
    })


# ==================== 使用说明 ====================

"""
📖 如何在实际接口中应用权限装饰器

1️⃣ 修改现有的聊天接口 (app/api/chat.py):

   # 原代码:
   @router.post("/rag")
   async def rag_query(request: RagQueryRequest):
       # 业务逻辑
       pass

   # 添加权限控制后:
   @router.post("/rag")
   @require_privilege("rag")        # 新增：检查RAG权限
   @require_quota("daily_chats")    # 新增：检查聊天配额
   async def rag_query(request: RagQueryRequest):
       # 业务逻辑（不需要任何权限检查代码）
       pass

2️⃣ 修改知识库创建接口 (app/api/knowledge.py):

   # 原代码:
   @router.post("/create")
   async def create_knowledge_base(request: CreateKnowledgeBaseRequest):
       # 业务逻辑
       pass

   # 添加权限控制后:
   @router.post("/create")
   @require_quota("kb_count")  # 新增：检查知识库数量配额
   async def create_knowledge_base(request: CreateKnowledgeBaseRequest):
       # 业务逻辑（不需要任何权限检查代码）
       pass

3️⃣ 修改全功能接口:

   # 原代码:
   @router.post("/full-feature")
   async def full_feature_chat(request: FullFeatureChatRequest):
       # 业务逻辑
       pass

   # 添加权限控制后:
   @router.post("/full-feature")
   @require_member_level("premium")               # 新增：需要premium会员
   @require_all_privileges(["rag", "web_search"]) # 新增：需要RAG和搜索
   @require_quota("daily_chats")                  # 新增：需要聊天配额
   async def full_feature_chat(request: FullFeatureChatRequest):
       # 业务逻辑（不需要任何权限检查代码）
       pass

🎯 装饰器使用建议:

1. 从最重要的接口开始添加权限控制
2. 根据业务需求选择合适的装饰器
3. 组合使用多个装饰器实现复杂权限逻辑
4. 定期检查权限配置是否合理

📝 权限配置建议:

免费版 (free):
- 每日聊天: 20次
- 知识库: 2个
- RAG: ✅
- 网络搜索: ❌
- MCP工具: ❌

VIP月卡 (vip_month):
- 每日聊天: 无限制
- 知识库: 10个
- RAG: ✅
- 网络搜索: ✅
- MCP工具: ❌

VIP季卡 (vip_quarter):
- 每日聊天: 无限制
- 知识库: 20个
- RAG: ✅
- 网络搜索: ✅
- MCP工具: ✅

VIP年卡 (vip_year):
- 每日聊天: 无限制
- 知识库: 50个
- RAG: ✅
- 网络搜索: ✅
- MCP工具: ✅
"""
