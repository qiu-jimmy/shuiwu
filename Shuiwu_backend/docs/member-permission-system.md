# 会员权限认证系统使用指南

## 概述

这是一套基于 `business.member_packages` 表的声明式会员权限认证系统，允许您：

1. **声明式权限检查** - 在接口上声明需要的权益，系统自动验证
2. **动态权限扩展** - 通过 `custom_config` JSON 字段添加新权限，无需修改代码
3. **细粒度错误提示** - 明确告知用户缺少哪些权益
4. **组合条件检查** - 同时检查多个权益、配额、等级
5. **管理员跳过** - 管理员自动跳过所有权限检查 ⭐ 新增

---

## 快速开始

### 1. 注册路由

在 `app/main.py` 中添加：

```python
from app.api.member_permission_examples import router as member_examples_router
from app.api.member_package_config import router as package_config_router

app.include_router(member_examples_router, prefix="/api/examples", tags=["会员权限示例"])
app.include_router(package_config_router, prefix="/api/package-config", tags=["套餐配置管理"])
```

### 2. 基本使用

```python
from fastapi import APIRouter
from app.middleware.member_permission import require_member_privilege

router = APIRouter()

@router.post("/chat/rag")
@require_member_privilege("rag")
async def rag_chat():
    return {"message": "RAG 功能已启用"}
```

### 3. 配置套餐权益

在数据库中配置：

```sql
-- 启用 RAG 功能
UPDATE business.member_packages
SET enable_rag = true
WHERE package_id = 'premium_month';

-- 或使用 custom_config 添加自定义权限
UPDATE business.member_packages
SET custom_config = '{"enable_advanced_analytics": true, "max_team_members": 10}'
WHERE package_id = 'enterprise_year';
```

---

## 管理员跳过权限检查

### 自动跳过机制

所有会员权限装饰器都支持管理员自动跳过，无需额外配置：

```python
@router.post("/chat/rag")
@require_member_privilege("rag")
async def rag_chat():
    # 管理员可以直接访问，跳过权限检查
    pass
```

### 管理员标识

系统通过以下字段判断是否为管理员：

| 字段 | 值 | 说明 |
|------|-----|------|
| `user_type` | `"admin"` | 用户类型为管理员 |
| `role` | `"admin"` 或 `"super_admin"` | 角色为管理员 |

### 检查管理员身份

在业务逻辑中检查当前用户是否为管理员：

```python
from app.middleware.member_permission import is_admin_user

@router.get("/api/some-endpoint")
async def some_endpoint(request: Request):
    if is_admin_user(request):
        return {"message": "管理员访问", "data": "所有数据"}
    else:
        return {"message": "普通用户访问", "data": "部分数据"}
```

### 禁用管理员跳过

如果某个接口需要管理员也遵守权限检查，可以设置 `skip_admin=False`：

```python
@router.post("/special-feature")
@require_member_privilege("rag", skip_admin=False)
async def special_feature():
    # 管理员也需要有 rag 权限才能访问
    pass
```

### Request State 标识

当管理员跳过权限检查时，会在 `request.state` 中设置标识：

```python
@router.post("/some-feature")
@require_member_privilege("rag")
async def some_feature(request: Request):
    # 检查是否为管理员跳过
    is_admin_bypass = getattr(request.state, "is_admin_bypass", False)

    if is_admin_bypass:
        admin_info = getattr(request.state, "admin_privilege_check", {})
        return {
            "message": "管理员访问",
            "bypassed_privilege": admin_info.get("bypassed_privilege")
        }

    # 普通用户逻辑
    ...
```

### 示例接口

```bash
# 检查当前用户是否为管理员
GET /api/examples/admin-check

# 测试管理员跳过权限检查
GET /api/examples/admin-bypass
```

---

## 装饰器详解

### 1. `@require_member_privilege` - 单个权益检查

```python
@require_member_privilege("rag")
async def rag_feature():
    pass
```

**支持的权益类型：**
- `rag` - RAG 检索增强
- `web_search` - 网络搜索
- `mcp_tools` - MCP 工具
- 任意自定义权益（从 `custom_config.enable_xxx` 读取）

### 2. `@require_any_member_privilege` - OR 逻辑

```python
@require_any_member_privilege(["rag", "web_search"])
async def advanced_chat():
    # 用户有 RAG 或网络搜索任一权限即可
    pass
```

### 3. `@require_all_member_privileges` - AND 逻辑

```python
@require_all_member_privileges(["rag", "web_search", "mcp_tools"])
async def full_featured():
    # 用户需要同时拥有所有权限
    pass
```

### 4. `@require_member_quota` - 配额检查

```python
@require_member_quota("kb_count", consume=1)
async def create_knowledge():
    # 检查是否有剩余的知识库配额
    pass

@require_member_quota("file_storage_mb", consume=50)
async def upload_large_file():
    # 检查是否有 50MB 的存储空间
    pass
```

**支持的配额类型：**
- `daily_chats` - 每日聊天次数
- `kb_count` - 知识库数量
- `kb_documents` - 知识库文档数
- `file_storage_mb` - 文件存储空间
- `file_count` - 文件数量

### 5. `@require_member_level` - 会员等级检查

```python
@require_member_level("premium")
async def premium_feature():
    # 需要 premium 及以上会员
    pass
```

**等级顺序：** `free` < `basic` < `premium` < `enterprise`

### 6. `@require_member_features` - 组合检查（推荐）

```python
@require_member_features(
    privileges=["rag", "web_search"],
    quotas={"kb_count": 1},
    min_level="premium"
)
async def enterprise_feature():
    # 同时满足：
    # 1. 有 RAG 和网络搜索权限
    # 2. 至少剩余 1 个知识库配额
    # 3. premium 及以上会员
    pass
```

---

## 数据库表结构

### member_packages 核心字段

```sql
CREATE TABLE business.member_packages (
    package_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL,

    -- 标准权益
    enable_rag BOOLEAN DEFAULT true,
    enable_web_search BOOLEAN DEFAULT false,
    enable_mcp_tools BOOLEAN DEFAULT false,

    -- 配额
    max_daily_chats INTEGER DEFAULT -1,
    max_kb_count INTEGER DEFAULT 5,
    max_kb_documents INTEGER DEFAULT 100,
    max_file_storage_mb INTEGER DEFAULT 1024,
    max_file_count INTEGER DEFAULT 100,

    -- 扩展配置
    custom_config JSONB DEFAULT '{}',
    benefits JSONB DEFAULT '[]'
);
```

### custom_config 扩展权限

在 `custom_config` 中可以添加任意自定义权限：

```sql
-- 添加自定义权限
UPDATE business.member_packages
SET custom_config = '{
    "level": "premium",
    "enable_advanced_analytics": true,
    "enable_team_collaboration": true,
    "max_team_members": 50,
    "enable_api_access": true
}'::jsonb
WHERE package_id = 'premium_month';
```

系统会自动检查 `custom_config.enable_xxx` 字段，无需修改代码。

---

## 套餐配置工具

### 使用配置构建器

```python
from app.services.member.package_config_helper import (
    PackageConfigBuilder,
    create_premium_month_package
)

# 方式1: 使用构建器
builder = (
    PackageConfigBuilder("custom_package", "自定义套餐")
    .set_description("我的自定义套餐")
    .set_pricing(99.9, "month", 30)
    .enable_privilege("rag")
    .enable_privilege("web_search")
    .set_quota("daily_chats", -1)
    .set_quota("kb_count", 20)
    .set_custom_privilege("team_collaboration", True)
    .add_benefit("无限对话", "每日无限制AI对话")
    .add_benefit("团队协作", "支持多人协作")
)

sql = builder.generate_sql()
print(sql)  # 复制到数据库执行

# 方式2: 使用预设模板
template = create_premium_month_package()
template.set_custom_config({"enable_custom_feature": True})
sql = template.generate_sql()
```

### 使用 API 配置

```bash
# 获取所有可用权限类型
GET /api/package-config/privilege-types

# 获取套餐模板
GET /api/package-config/templates

# 生成配置 SQL
POST /api/package-config/generate-sql
{
    "package_id": "my_package",
    "name": "我的套餐",
    "price": 99.9,
    "enable_rag": true,
    "enable_web_search": true,
    "max_daily_chats": -1,
    "custom_config": {
        "enable_team_collaboration": true
    }
}

# 快速启用自定义权限
POST /api/package-config/quick-enable-privilege
{
    "package_id": "premium_month",
    "custom_config": {
        "enable_advanced_analytics": true
    }
}
```

---

## 权限检查流程

```
用户请求 → JWT 中间件 → 获取 user_id + user_type + role
    ↓
检查是否为管理员？（user_type=admin 或 role=admin/super_admin）
    ├─ 是 → 跳过所有权限检查 → 执行业务逻辑 ✅
    └─ 否 → 继续检查 ↓
查询 users 表获取 member_level
    ↓
查询 member_packages 表获取套餐配置
    ↓
根据装饰器参数检查权限：
  ├─ 检查 enable_xxx 字段（标准权益）
  ├─ 检查 custom_config.enable_xxx（自定义权益）
  ├─ 检查配额使用情况
  └─ 检查会员等级
    ↓
通过 → 执行业务逻辑 + 自动记录使用
失败 → 返回详细错误信息
```

---

## 错误响应格式

### 权限不足

```json
{
    "code": "PRIVILEGE_REQUIRED",
    "message": "当前套餐不支持 RAG 功能",
    "data": {
        "privilege_type": "rag",
        "source": "standard_field"
    }
}
```

### 配额不足

```json
{
    "code": "QUOTA_EXCEEDED",
    "message": "知识库数量不足（剩余: 0，需要: 1）",
    "data": {
        "quota_type": "kb_count",
        "used": 10,
        "max": 10,
        "remaining": 0,
        "required": 1
    }
}
```

### 等级不足

```json
{
    "code": "LEVEL_REQUIRED",
    "message": "此功能需要 premium 及以上会员等级（当前: basic）",
    "data": {
        "current_level": "basic",
        "required_level": "premium"
    }
}
```

---

## 高级用法

### 可选功能（权限不足时不报错）

```python
@require_member_privilege("advanced_analytics", on_fail="return_none")
async def optional_feature(request: Request):
    member_info = get_current_member_privileges(request)
    if not member_info:
        # 返回基础版本
        return {"version": "basic"}

    # 返回高级版本
    return {"version": "advanced"}
```

### 在路由中获取会员信息

```python
from app.middleware.member_permission import get_current_member_privileges

@router.get("/api/my-status")
async def get_my_status(request: Request):
    member_info = get_current_member_privileges(request)

    if not member_info:
        return {"error": "未获取到会员信息"}

    return {
        "member_level": member_info.get("member_level"),
        "enable_rag": member_info.get("enable_rag"),
        "max_daily_chats": member_info.get("max_daily_chats"),
        "today_chats": member_info.get("today_chats")
    }
```

### 清除缓存

```python
from app.middleware.member_permission import clear_member_cache

# 用户购买会员后清除缓存
clear_member_cache(user_id)

# 清除所有缓存
clear_member_cache()
```

---

## 完整示例

### 知识库创建接口

```python
@router.post("/knowledge/create")
@require_member_features(
    privileges=["rag"],
    quotas={"kb_count": 1},
    min_level="basic"
)
async def create_knowledge(
    request: Request,
    name: str,
    description: str = ""
):
    """
    创建知识库

    权限要求：
    1. 需要 RAG 功能（basic 及以上会员）
    2. 至少剩余 1 个知识库配额
    """
    user_id = getattr(request.state, "user_id")

    # 执行实际业务逻辑
    kb_id = await knowledge_service.create(user_id, name, description)

    return {
        "kb_id": kb_id,
        "name": name,
        "message": "知识库创建成功"
    }
```

### 企业级功能接口

```python
@router.post("/enterprise/report")
@require_member_features(
    privileges=["rag", "web_search", "mcp_tools", "team_collaboration"],
    quotas={"daily_chats": 1},
    min_level="enterprise"
)
async def generate_enterprise_report(request: Request, query: str):
    """
    生成企业报告

    需要同时满足：
    - RAG、网络搜索、MCP 工具、团队协作权限
    - enterprise 会员等级
    - 剩余至少 1 次每日对话
    """
    member_info = get_current_member_privileges(request)
    custom_config = member_info.get("custom_config", {})

    # 使用自定义配置
    max_team_members = custom_config.get("max_team_members", 10)

    # 执行业务逻辑
    report = await report_service.generate(query)

    return {
        "report": report,
        "team_members_limit": max_team_members
    }
```

---

## 管理接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/package-config/privilege-types` | GET | 获取所有可用权限类型 |
| `/api/package-config/templates` | GET | 获取套餐配置模板 |
| `/api/package-config/generate-sql` | POST | 生成配置 SQL |
| `/api/package-config/validate-config` | POST | 验证配置格式 |
| `/api/package-config/quick-enable-privilege` | POST | 快速启用权限 |
| `/api/examples/my-privileges` | GET | 查看当前用户权益 |

---

## 常见问题

### Q: 如何添加新的权益类型？

A: 两种方式：

1. **标准权益**（需修改代码）：在 `STANDARD_PRIVILEGE_FIELDS` 中添加

2. **自定义权益**（推荐）：直接在数据库 `custom_config` 中配置

```sql
UPDATE business.member_packages
SET custom_config = '{"enable_my_feature": true}'
WHERE package_id = 'premium_month';
```

然后在代码中直接使用：

```python
@require_member_privilege("my_feature")
async def my_feature():
    pass
```

### Q: 权限检查会影响性能吗？

A: 系统内置了 5 分钟的缓存机制，同一用户短时间内多次请求会使用缓存，不会重复查询数据库。

### Q: 如何测试不同套餐的权限？

A: 使用示例接口：

```bash
GET /api/examples/privileges-by-package/vip_month
```

或在数据库中修改用户的 `member_level` 进行测试。

---

## 文件结构

```
app/
├── middleware/
│   └── member_permission.py          # 核心装饰器
├── services/
│   └── member/
│       ├── member_service.py          # 会员服务
│       ├── member_repository.py       # 数据访问层
│       └── package_config_helper.py   # 配置工具
└── api/
    ├── member_permission_examples.py  # 使用示例
    └── member_package_config.py       # 配置管理 API
```

---

## 更新日志

- **v1.0** (2025-01-20)
  - 初始版本
  - 支持标准权益和自定义权益
  - 支持配额和等级检查
  - 内置缓存机制
  - 配置管理 API
