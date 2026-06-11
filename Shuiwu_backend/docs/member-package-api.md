# 会员套餐管理接口文档

## 接口概述

本文档描述了会员套餐的创建与更新接口，供管理员使用。

**Base URL**: `http://127.0.0.1:8000`

**认证方式**: Bearer Token（管理员权限）

---

## 1. 创建会员套餐

### 接口信息

- **接口地址**: `POST /api/member/packages`
- **接口说明**: 管理员创建新的会员套餐
- **权限要求**: 管理员权限
- **Content-Type**: `application/json`

### 请求头

```json
{
  "Authorization": "Bearer <your_admin_token>"
}
```

### 请求参数

#### Body 参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| package_id | string | 是 | - | 套餐ID，必须唯一 |
| name | string | 是 | - | 套餐名称 |
| description | string | 否 | - | 套餐描述 |
| package_type | string | 是 | - | 套餐类型：free(免费)、basic(基础)、premium(高级)、enterprise(企业)、month(月卡)、quarter(季卡)、year(年卡)、lifetime(终身) |
| price | float | 是 | - | 价格 |
| original_price | float | 否 | - | 原价（用于显示折扣） |
| duration_days | int | 否 | - | 有效期（天），lifetime类型可不填 |
| max_daily_chats | int | 否 | -1 | 每日最大聊天次数，-1表示无限制 |
| max_kb_count | int | 否 | 5 | 最大知识库数量 |
| max_kb_documents | int | 否 | 100 | 最大文档数量 |
| max_file_storage_mb | int | 否 | 1024 | 最大文件存储空间（MB） |
| max_file_count | int | 否 | 100 | 最大文件数量 |
| enable_rag | bool | 否 | false | 是否启用RAG功能 |
| enable_web_search | bool | 否 | false | 是否启用网络搜索 |
| enable_mcp_tools | bool | 否 | false | 是否启用MCP工具 |
| sort_order | int | 否 | 0 | 排序顺序，数字越小越靠前 |
| custom_config | object | 否 | {} | 自定义配置（JSON格式），用于存储扩展字段 |
| benefits | array | 否 | [] | 权益描述列表，供前端渲染展示 |

#### custom_config 说明

自定义配置对象，可包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| level | string | 会员等级，如 "premium" |
| priority | int | 优先级，数字越大优先级越高 |
| features | array | 功能列表，如 ["rag", "web_search", "ai_image"] |

#### benefits 说明

权益描述数组，每个元素包含：

| 字段 | 类型 | 说明 |
|------|------|------|
| title | string | 权益标题 |
| desc | string | 权益描述 |

### 请求示例

#### 创建高级月卡套餐

```bash
curl -X POST "http://127.0.0.1:8000/api/member/packages" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "package_id": "premium_month_30days",
    "name": "高级月卡-30天",
    "description": "高级会员套餐，有效期30天，解锁全部功能",
    "package_type": "premium",
    "price": 29.9,
    "original_price": 39.9,
    "duration_days": 30,
    "max_daily_chats": 100,
    "max_kb_count": 10,
    "max_kb_documents": 100,
    "max_file_storage_mb": 1024,
    "max_file_count": 50,
    "enable_rag": true,
    "enable_web_search": true,
    "enable_mcp_tools": true,
    "sort_order": 2,
    "custom_config": {
      "level": "premium",
      "priority": 2,
      "features": ["rag", "web_search", "ai_image", "mcp_tools"]
    },
    "benefits": [
      {
        "title": "每日100次对话",
        "desc": "每天可使用100次AI智能对话"
      },
      {
        "title": "10个知识库",
        "desc": "支持创建10个知识库进行分类管理"
      },
      {
        "title": "RAG功能",
        "desc": "知识库检索增强生成，答案更精准"
      },
      {
        "title": "网络搜索",
        "desc": "实时联网搜索，获取最新信息"
      },
      {
        "title": "MCP工具",
        "desc": "支持使用MCP扩展工具"
      }
    ]
  }'
```

#### 创建免费套餐

```bash
curl -X POST "http://127.0.0.1:8000/api/member/packages" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "package_id": "free",
    "name": "免费版",
    "description": "基础功能体验",
    "package_type": "free",
    "price": 0,
    "duration_days": null,
    "max_daily_chats": 20,
    "max_kb_count": 2,
    "max_kb_documents": 20,
    "max_file_storage_mb": 100,
    "max_file_count": 100,
    "enable_rag": true,
    "enable_web_search": false,
    "enable_mcp_tools": false,
    "status": "active",
    "sort_order": 0,
    "custom_config": {},
    "benefits": [
      {
        "title": "每日10次对话",
        "desc": "每天可以免费使用10次AI对话"
      },
      {
        "title": "1个知识库",
        "desc": "支持创建1个个人知识库"
      },
      {
        "title": "10份文档",
        "desc": "最多可上传10份文档进行知识管理"
      },
      {
        "title": "100MB存储",
        "desc": "云端文件存储空间"
      }
    ]
  }'
```

### 响应格式

#### 成功响应

```json
{
  "code": 1,
  "message": "创建套餐成功",
  "data": {
    "package_id": "premium_month_30days",
    "name": "高级月卡-30天",
    "description": "高级会员套餐，有效期30天，解锁全部功能",
    "package_type": "premium",
    "price": 29.9,
    "original_price": 39.9,
    "duration_days": 30,
    "max_daily_chats": 100,
    "max_kb_count": 10,
    "max_kb_documents": 100,
    "max_file_storage_mb": 1024,
    "max_file_count": 50,
    "enable_rag": true,
    "enable_web_search": true,
    "enable_mcp_tools": true,
    "status": "active",
    "sort_order": 2,
    "custom_config": {
      "level": "premium",
      "priority": 2,
      "features": ["rag", "web_search", "ai_image", "mcp_tools"]
    },
    "benefits": [
      {
        "title": "每日100次对话",
        "desc": "每天可使用100次AI智能对话"
      },
      {
        "title": "10个知识库",
        "desc": "支持创建10个知识库进行分类管理"
      },
      {
        "title": "RAG功能",
        "desc": "知识库检索增强生成，答案更精准"
      },
      {
        "title": "网络搜索",
        "desc": "实时联网搜索，获取最新信息"
      },
      {
        "title": "MCP工具",
        "desc": "支持使用MCP扩展工具"
      }
    ],
    "created_at": "2024-01-15T10:00:00",
    "updated_at": "2024-01-15T10:00:00"
  }
}
```

#### 失败响应

**套餐ID已存在**

```json
{
  "code": 0,
  "message": "套餐ID已存在",
  "data": null
}
```

**未授权**

```json
{
  "code": 0,
  "message": "未提供认证token",
  "data": null
}
```

**权限不足**

```json
{
  "code": 0,
  "message": "需要管理员权限",
  "data": null
}
```

---

## 2. 更新会员套餐

### 接口信息

- **接口地址**: `PUT /api/member/packages/{package_id}`
- **接口说明**: 管理员更新会员套餐信息
- **权限要求**: 管理员权限
- **Content-Type**: `application/json`

### 请求头

```json
{
  "Authorization": "Bearer <your_admin_token>"
}
```

### 路径参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| package_id | string | 是 | 套餐ID |

### 请求参数

#### Body 参数（可选，只更新提供的字段）

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| name | string | 否 | 套餐名称 |
| description | string | 否 | 套餐描述 |
| price | float | 否 | 价格 |
| original_price | float | 否 | 原价 |
| duration_days | int | 否 | 有效期（天） |
| max_daily_chats | int | 否 | 每日最大聊天次数 |
| max_kb_count | int | 否 | 最大知识库数量 |
| max_kb_documents | int | 否 | 最大文档数量 |
| max_file_storage_mb | int | 否 | 最大文件存储（MB） |
| max_file_count | int | 否 | 最大文件数量 |
| enable_rag | bool | 否 | 是否启用RAG |
| enable_web_search | bool | 否 | 是否启用网络搜索 |
| enable_mcp_tools | bool | 否 | 是否启用MCP工具 |
| status | string | 否 | 套餐状态：active（启用）、inactive（停用） |
| sort_order | int | 否 | 排序顺序 |
| custom_config | object | 否 | 自定义配置（JSON格式） |
| benefits | array | 否 | 权益描述列表（JSON数组） |

**注意**: 只更新提供的字段，未提供的字段保持不变。套餐ID不可修改。

### 请求示例

#### 更新套餐价格和描述

```bash
curl -X PUT "http://127.0.0.1:8000/api/member/packages/premium_month_30days" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "高级月卡-30天（限时优惠）",
    "price": 19.9,
    "original_price": 29.9,
    "description": "高级会员套餐，有效期30天，限时优惠价"
  }'
```

#### 更新套餐权益配置

```bash
curl -X PUT "http://127.0.0.1:8000/api/member/packages/premium_month_30days" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "max_daily_chats": 200,
    "max_kb_count": 20,
    "enable_mcp_tools": true,
    "benefits": [
      {
        "title": "每日200次对话",
        "desc": "每天可使用200次AI智能对话（升级后）"
      },
      {
        "title": "20个知识库",
        "desc": "支持创建20个知识库进行分类管理（升级后）"
      },
      {
        "title": "RAG功能",
        "desc": "知识库检索增强生成，答案更精准"
      },
      {
        "title": "网络搜索",
        "desc": "实时联网搜索，获取最新信息"
      },
      {
        "title": "MCP工具",
        "desc": "支持使用MCP扩展工具"
      }
    ]
  }'
```

#### 停用套餐

```bash
curl -X PUT "http://127.0.0.1:8000/api/member/packages/premium_month_30days" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "status": "inactive"
  }'
```

### 响应格式

#### 成功响应

```json
{
  "code": 1,
  "message": "更新套餐成功",
  "data": {
    "package_id": "premium_month_30days",
    "name": "高级月卡-30天（限时优惠）",
    "price": 19.9,
    "status": "active"
  }
}
```

#### 失败响应

**套餐不存在**

```json
{
  "code": 0,
  "message": "套餐不存在",
  "data": null
}
```

**未授权**

```json
{
  "code": 0,
  "message": "未提供认证token",
  "data": null
}
```

**权限不足**

```json
{
  "code": 0,
  "message": "需要管理员权限",
  "data": null
}
```

---

## 3. 套餐类型说明

| package_type | 说明 | 适用于 |
|--------------|------|--------|
| free | 免费套餐 | 新用户默认 |
| basic | 基础套餐 | 基础付费用户 |
| premium | 高级套餐 | 高级付费用户 |
| enterprise | 企业套餐 | 企业用户 |
| month | 月卡 | 30天有效期 |
| quarter | 季卡 | 90天有效期 |
| year | 年卡 | 365天有效期 |
| lifetime | 终身 | 永久有效 |

## 4. 状态码说明

| HTTP状态码 | 说明 |
|-----------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 401 | 未授权（token无效或缺失） |
| 403 | 权限不足（非管理员） |

## 5. 错误码说明

| code | message | 说明 |
|------|---------|------|
| 1 | 操作成功 | 请求处理成功 |
| 0 | 错误信息 | 请求处理失败，message包含具体错误原因 |

## 6. 常见错误

### 套餐ID已存在

```json
{
  "code": 0,
  "message": "套餐ID已存在",
  "data": null
}
```

**解决方案**: 使用不同的package_id创建套餐

### 套餐不存在

```json
{
  "code": 0,
  "message": "套餐不存在",
  "data": null
}
```

**解决方案**: 确认package_id是否正确，或先创建该套餐

### 未提供认证token

```json
{
  "code": 0,
  "message": "未提供认证token",
  "data": null
}
```

**解决方案**: 在请求头中添加有效的Bearer Token

### 需要管理员权限

```json
{
  "code": 0,
  "message": "需要管理员权限",
  "data": null
}
```

**解决方案**: 确保当前用户具有管理员角色

---

## 7. 完整示例 - 创建企业套餐

```bash
curl -X POST "http://127.0.0.1:8000/api/member/packages" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "package_id": "enterprise_year",
    "name": "企业年卡",
    "description": "企业级解决方案，满足团队协作需求",
    "package_type": "enterprise",
    "price": 999.0,
    "original_price": 1999.0,
    "duration_days": 365,
    "max_daily_chats": -1,
    "max_kb_count": 100,
    "max_kb_documents": 10000,
    "max_file_storage_mb": 102400,
    "max_file_count": 5000,
    "enable_rag": true,
    "enable_web_search": true,
    "enable_mcp_tools": true,
    "sort_order": 10,
    "custom_config": {
      "level": "enterprise",
      "priority": 10,
      "features": ["rag", "web_search", "ai_image", "mcp_tools", "team_collaboration", "api_access"],
      "max_team_members": 50,
      "priority_support": true
    },
    "benefits": [
      {
        "title": "无限对话",
        "desc": "AI对话次数无限制"
      },
      {
        "title": "100个知识库",
        "desc": "支持创建100个企业知识库"
      },
      {
        "title": "10000份文档",
        "desc": "最多可上传10000份文档"
      },
      {
        "title": "100GB存储",
        "desc": "超大云端文件存储空间"
      },
      {
        "title": "团队协作",
        "desc": "支持50人团队协作"
      },
      {
        "title": "API访问",
        "desc": "开放API接口供企业集成"
      },
      {
        "title": "优先支持",
        "desc": "专属客服，优先处理问题"
      }
    ]
  }'
```

---

## 8. 注意事项

1. **package_id必须唯一**: 创建套餐时，package_id是套餐的唯一标识，创建后不可修改
2. **price不能为负数**: 价格必须大于等于0
3. **duration_days**: lifetime类型套餐可以不设置duration_days
4. **max_daily_chats**: 设置为-1表示无限制
5. **custom_config**: 用于存储扩展字段，可以根据业务需求灵活配置
6. **benefits**: 前端会直接使用此数据渲染权益列表
7. **更新是部分更新**: 只更新提供的字段，未提供的字段保持不变
8. **状态管理**: 将套餐status设置为inactive可以停用套餐，不影响已购买该套餐的用户

---

## 9. 相关接口

- **获取套餐列表**: `GET /api/member/packages`
- **获取套餐详情**: `GET /api/member/packages/{package_id}`
- **删除套餐**: `DELETE /api/member/packages/{package_id}`

---

**文档版本**: v1.0
**最后更新**: 2024-01-22
