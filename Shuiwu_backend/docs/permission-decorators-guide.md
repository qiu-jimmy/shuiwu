# 会员权限装饰器使用指南

本文档介绍如何使用会员权限装饰器来实现自动化的权限控制。

## 目录
- [快速开始](#快速开始)
- [装饰器类型](#装饰器类型)
- [使用示例](#使用示例)
- [高级用法](#高级用法)
- [扩展性](#扩展性)
- [错误处理](#错误处理)

## 快速开始

### 基本使用

```python
from fastapi import APIRouter, Request
from app.middleware.permission import require_privilege, require_quota
from app.utils.response import response

router = APIRouter(prefix="/api/chat", tags=["聊天"])

@router.post("/rag")
@require_privilege("rag")  # 自动检查RAG权限
async def rag_chat(request: Request, message: str):
    # 直接写业务逻辑，不需要任何权限检查代码
    return response.success(data={"response": "RAG回复内容"})
```

### 多个装饰器组合

```python
@router.post("/chat/advanced")
@require_privilege("rag")        # 检查RAG功能权限
@require_quota("daily_chats")    # 检查每日聊天配额
async def advanced_chat(request: Request, message: str):
    # 只有同时满足RAG权限和聊天配额才会执行这里
    return response.success(data={"response": "高级聊天回复"})
```

## 装饰器类型

### 1. require_privilege - 功能权限装饰器

检查用户是否有权使用某项功能。

**参数：**
- `privilege_type`: 权益类型（str）
- `auto_record`: 是否自动记录使用（bool，默认True）

**支持的权限类型：**
- `rag` - RAG功能
- `web_search` - 网络搜索
- `mcp_tools` - MCP工具
- 任何数据库套餐表中 `enable_xxx` 字段对应的权限

**示例：**
```python
@router.post("/chat/rag")
@require_privilege("rag")
async def rag_chat(message: str):
    return execute_rag(message)

# 不自动记录使用
@router.post("/special/feature")
@require_privilege("special_feature", auto_record=False)
async def special_feature():
    # 需要手动记录使用
    pass
```

### 2. require_quota - 配额权限装饰器

检查用户是否有足够的配额。

**参数：**
- `quota_type`: 配额类型（str）
- `consume`: 消耗数量（int，默认1）

**支持的配额类型：**
- `daily_chats` - 每日聊天次数
- `kb_count` - 知识库数量
- `kb_documents` - 知识库文档数
- `file_storage_mb` - 文件存储(MB)
- `file_count` - 文件数量

**示例：**
```python
@router.post("/knowledge/create")
@require_quota("kb_count")
async def create_knowledge(name: str):
    # 知识库数量未达上限才会执行
    return create_kb(name)

@router.post("/file/upload")
@require_quota("file_storage_mb", consume=10)  # 消耗10MB
async def upload_file(file: UploadFile):
    # 存储空间足够才会执行
    return save_file(file)
```

### 3. require_member_level - 会员等级装饰器

要求用户达到指定的会员等级。

**参数：**
- `min_level`: 最低会员等级（str，默认"basic"）

**支持的等级：**
- `free` - 免费用户
- `basic` - 基础会员
- `premium` - 高级会员
- `enterprise` - 企业会员

**示例：**
```python
@router.post("/advanced/feature")
@require_member_level("premium")
async def advanced_feature():
    # 只有premium及以上等级才能访问
    return execute_advanced()
```

### 4. require_any_privilege - 多权限OR装饰器

满足任一权限即可。

**参数：**
- `privilege_types`: 权限类型列表（List[str]）
- `auto_record`: 是否自动记录使用（bool，默认True）

**示例：**
```python
@router.post("/chat/advanced")
@require_any_privilege(["rag", "web_search"])
async def advanced_chat(message: str):
    # 只要有RAG或网络搜索任一权限即可
    return execute_advanced(message)
```

### 5. require_all_privileges - 多权限AND装饰器

需要同时满足所有权限。

**参数：**
- `privilege_types`: 权限类型列表（List[str]）
- `auto_record`: 是否自动记录使用（bool，默认True）

**示例：**
```python
@router.post("/chat/full-featured")
@require_all_privileges(["rag", "web_search", "mcp_tools"])
async def full_chat(message: str):
    # 需要同时具备RAG、网络搜索、MCP工具权限
    return execute_full(message)
```

## 使用示例

### 场景1：RAG聊天接口

需要RAG功能权限和每日聊天配额。

```python
@router.post("/chat/rag")
@require_privilege("rag")        # 自动检查RAG功能开关
@require_quota("daily_chats")    # 自动检查每日聊天次数
async def rag_chat(request: Request, message: str):
    # 业务逻辑
    result = await rag_service.chat(message)
    return response.success(data=result)
```

**执行流程：**
1. 检查RAG功能权限 → 不支持则返回 "当前套餐不支持RAG功能"
2. 检查每日聊天配额 → 用完则返回 "今日聊天次数已达上限"
3. 都通过才进入函数体执行业务逻辑
4. 自动记录使用量

### 场景2：创建知识库

需要检查知识库数量配额。

```python
@router.post("/knowledge/create")
@require_quota("kb_count")
async def create_knowledge(
    request: Request,
    name: str,
    description: str = None
):
    # 知识库数量未达上限才会执行
    kb_id = await knowledge_service.create(
        user_id=request.state.user_id,
        name=name,
        description=description
    )
    return response.success(data={"kb_id": kb_id})
```

### 场景3：高级功能

需要premium及以上会员等级。

```python
@router.post("/advanced/feature")
@require_member_level("premium")
async def advanced_feature(request: Request):
    # 只有premium及以上等级才能访问
    result = await advanced_service.execute()
    return response.success(data=result)
```

### 场景4：文件上传

需要检查存储空间配额。

```python
@router.post("/file/upload")
@require_quota("file_storage_mb", consume=10)  # 预计消耗10MB
async def upload_file(request: Request, file: UploadFile):
    # 存储空间足够才会执行
    file_id = await file_service.save(file)
    return response.success(data={"file_id": file_id})
```

### 场景5：复杂权限组合

```python
@router.post("/ai/generate")
@require_member_level("premium")               # 需要premium会员
@require_all_privileges(["rag", "web_search"]) # 需要同时有RAG和搜索权限
@require_quota("daily_chats")                  # 需要聊天配额
async def ai_generate(request: Request, prompt: str):
    # 所有条件都满足才会执行
    result = await ai_service.generate(prompt)
    return response.success(data=result)
```

## 高级用法

### 自定义权限检查器

对于需要复杂逻辑的权限，可以注册自定义检查器。

```python
from app.middleware.permission import register_privilege_checker

# 注册自定义权限检查器
@register_privilege_checker("team_collaboration")
def check_team_collaboration(user_id: str) -> dict:
    """检查团队协作权限"""
    # 复杂逻辑：检查是否是企业会员 + 已创建团队 + 团队成员未满
    member_info = member_service.get_member_info(user_id)

    if member_info.get("member_level") != "enterprise":
        return {"has_privilege": False, "reason": "需要企业会员"}

    team = team_service.get_team(user_id)
    if not team:
        return {"has_privilege": False, "reason": "需要先创建团队"}

    if len(team["members"]) >= team["max_members"]:
        return {"has_privilege": False, "reason": "团队成员已满"}

    return {"has_privilege": True, "reason": ""}

# 使用自定义权限
@router.post("/team/collaborate")
@require_privilege("team_collaboration")
async def collaborate(request: Request):
    return response.success(data={})
```

### 动态权限扩展

只需在数据库中添加字段，无需修改代码。

**步骤：**
1. 在数据库 `member_packages` 表添加字段：
```sql
ALTER TABLE business.member_packages ADD COLUMN enable_ai_image BOOLEAN DEFAULT FALSE;
```

2. 创建套餐时配置：
```python
{
    "name": "高级会员",
    "enable_ai_image": True
}
```

3. 直接使用：
```python
@router.post("/ai/generate-image")
@require_privilege("ai_image")
async def generate_image(prompt: str):
    # 装饰器会自动检查 enable_ai_image 字段
    return ai_service.generate_image(prompt)
```

### 获取权限检查结果

装饰器会将权限检查结果存储在 `request.state` 中。

```python
@router.post("/chat/rag")
@require_privilege("rag")
async def rag_chat(request: Request, message: str):
    # 获取权限检查结果
    privilege_check = getattr(request.state, "privilege_check", None)

    if privilege_check:
        # 可以使用权限信息
        pass

    return execute_rag(message)
```

## 扩展性

### 添加新的配额类型

1. 在数据库 `member_packages` 表添加字段：
```sql
ALTER TABLE business.member_packages ADD COLUMN max_api_calls INT DEFAULT 100;
```

2. 在 `permission.py` 的 `quota_mapping` 中添加映射：
```python
quota_mapping = {
    # ... 现有映射 ...
    "api_calls": ("api_calls_used", "max_api_calls", "API调用次数"),
}
```

3. 使用：
```python
@router.post("/api/call")
@require_quota("api_calls")
async def api_call():
    pass
```

### 切换数据源

实现自定义的数据源类。

```python
from app.middleware.permission import PrivilegeSource

class RedisPrivilegeSource(PrivilegeSource):
    async def get_privileges(self, user_id: str) -> dict:
        return redis_client.get(f"privileges:{user_id}")

# 切换数据源
privilege_source = RedisPrivilegeSource()
```

## 错误处理

### 错误响应格式

所有权限检查失败都返回统一格式：

```json
{
  "code": 0,
  "message": "当前套餐不支持RAG功能",
  "data": {
    "used": 45,
    "max": 100,
    "remaining": 55,
    "required": 1
  }
}
```

### 错误代码

- `PERMISSION_DENIED` - 权限不足
- `QUOTA_EXCEEDED` - 配额超限
- `MEMBER_REQUIRED` - 需要会员权限
- `UPGRADE_REQUIRED` - 需要升级会员等级

### 前端处理建议

```javascript
// 前端根据错误代码处理
if (response.code === "PERMISSION_DENIED") {
  // 引导用户查看会员权益
  showUpgradeModal();
} else if (response.code === "QUOTA_EXCEEDED") {
  // 显示剩余配额
  showQuotaInfo(response.data);
} else if (response.code === "MEMBER_REQUIRED") {
  // 引导开通会员
  showMemberIntro();
}
```

## 最佳实践

1. **装饰器顺序**：先检查等级，再检查权限，最后检查配额
```python
@require_member_level("premium")
@require_privilege("rag")
@require_quota("daily_chats")
async def feature():
    pass
```

2. **错误提示**：使用友好的错误消息，告诉用户如何解决
3. **性能考虑**：对于高频接口，可以考虑减少 `auto_record` 次数
4. **缓存**：会员信息会自动缓存，减少数据库查询

## 常见问题

### Q: 如何禁用自动记录使用？

```python
@require_privilege("rag", auto_record=False)
```

### Q: 如何同时检查多个权限？

```python
# AND逻辑：需要所有权限
@require_all_privileges(["rag", "web_search"])

# OR逻辑：需要任一权限
@require_any_privilege(["rag", "web_search"])
```

### Q: 如何自定义错误消息？

注册自定义权限检查器，返回自定义的 `reason` 字段。

### Q: 装饰器会影响性能吗？

装饰器会使用缓存，对性能影响很小。首次检查后会缓存结果。

## 相关文件

- [app/middleware/permission.py](../app/middleware/permission.py) - 权限装饰器实现
- [app/services/member/member_service.py](../app/services/member/member_service.py) - 会员服务
- [app/services/member/member_cache.py](../app/services/member/member_cache.py) - 会员缓存
