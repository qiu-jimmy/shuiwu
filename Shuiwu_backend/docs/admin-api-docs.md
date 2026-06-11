# 管理员系统前端对接文档

## 接口说明

本文档描述了管理员系统的所有API接口，供前端开发人员对接使用。

**Base URL**: `http://127.0.0.1:8000`

**认证方式**: Bearer Token (JWT)

**通用响应格式**:
```json
{
  "code": 1,           // 1表示成功，0表示失败
  "message": "操作成功",
  "data": {}           // 返回数据，可能为null
}
```

---

## 1. 管理员认证

### 1.1 管理员登录

**接口地址**: `POST /api/admin/login`

**认证要求**: 无

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| username | string | 是 | 用户名或手机号 |
| password | string | 是 | 密码 |

**请求示例**:
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**响应示例**:
```json
{
  "code": 1,
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 604800,
    "admin_info": {
      "admin_id": "admin_001",
      "username": "admin",
      "nickname": "系统管理员",
      "role": "super_admin",
      "permissions": [
        "user.manage",
        "user.view",
        "member.manage",
        "member.view",
        "knowledge.manage",
        "knowledge.view",
        "mcp.manage",
        "mcp.view",
        "distribution.manage",
        "distribution.view",
        "order.view",
        "order.manage",
        "system.manage",
        "system.view",
        "log.view"
      ]
    }
  }
}
```

**注意**:
- 默认账户: 用户名 `admin`，密码 `admin123`
- 生产环境请修改默认密码
- Token 有效期为 7 天 (604800 秒)

---

### 1.2 获取当前管理员信息

**接口地址**: `GET /api/admin/me`

**认证要求**: 需要管理员 Bearer Token

**请求头**:
```
Authorization: Bearer {access_token}
```

**响应示例**:
```json
{
  "code": 1,
  "message": "操作成功",
  "data": {
    "admin_id": "admin_001",
    "username": "admin",
    "nickname": "系统管理员",
    "role": "super_admin",
    "permissions": [
      "user.manage",
      "user.view",
      "member.manage",
      "member.view",
      "knowledge.manage",
      "knowledge.view",
      "mcp.manage",
      "mcp.view",
      "distribution.manage",
      "distribution.view",
      "order.view",
      "order.manage",
      "system.manage",
      "system.view",
      "log.view"
    ]
  }
}
```

---

## 2. 用户管理

### 2.1 创建用户

**接口地址**: `POST /api/admin/users`

**认证要求**: 需要管理员 Bearer Token

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| phone | string | 是 | 手机号 |
| nickname | string | 否 | 昵称 |
| password | string | 否 | 密码（默认123456） |
| status | string | 否 | 状态：normal/disabled/banned，默认normal |
| user_type | string | 否 | 用户类型：individual/enterprise/admin，默认individual |
| member_level | string | 否 | 会员等级：free/basic/premium/enterprise，默认free |
| member_expire_at | string | 否 | 会员到期时间（ISO 8601格式） |

**请求示例**:
```json
{
  "phone": "13800138000",
  "nickname": "测试用户",
  "status": "normal",
  "user_type": "individual",
  "member_level": "free"
}
```

**响应示例**:
```json
{
  "code": 1,
  "message": "用户创建成功",
  "data": {
    "user_id": "user_1737465600000",
    "initial_password": "123456"
  }
}
```

---

### 2.2 获取用户列表

**接口地址**: `GET /api/admin/users`

**认证要求**: 需要管理员 Bearer Token

**Query参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| keyword | string | 否 | 搜索关键词（手机号、昵称、用户ID） |
| status | string | 否 | 用户状态：normal/disabled/banned |
| user_type | string | 否 | 用户类型：individual/enterprise/admin |
| member_level | string | 否 | 会员等级：free/basic/premium/enterprise |
| start_date | string | 否 | 注册开始日期（YYYY-MM-DD） |
| end_date | string | 否 | 注册结束日期（YYYY-MM-DD） |
| page | int | 否 | 页码，默认1 |
| page_size | int | 否 | 每页数量，默认20，最大100 |

**请求示例**:
```
GET /api/admin/users?status=normal&member_level=premium&page=1&page_size=20
```

**响应示例**:
```json
{
  "code": 1,
  "message": "操作成功",
  "data": {
    "total": 100,
    "page": 1,
    "page_size": 20,
    "users": [
      {
        "user_id": "user_1234567890",
        "phone": "13800138000",
        "nickname": "测试用户",
        "status": "normal",
        "user_type": "individual",
        "member_level": "premium",
        "register_time": "2024-01-01T00:00:00"
      }
    ]
  }
}
```

---

### 2.3 更新用户状态

**接口地址**: `PUT /api/admin/users/{user_id}/status`

**认证要求**: 需要管理员 Bearer Token

**路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| user_id | string | 是 | 用户ID |

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| status | string | 是 | 状态：normal/disabled/banned |
| reason | string | 否 | 状态变更原因 |

**请求示例**:
```json
{
  "status": "disabled",
  "reason": "违反用户协议"
}
```

**响应示例**:
```json
{
  "code": 1,
  "message": "用户状态已更新为: disabled",
  "data": null
}
```

**状态说明**:
- `normal`: 正常
- `disabled`: 禁用
- `banned`: 封禁

---

### 2.4 更新用户类型

**接口地址**: `PUT /api/admin/users/{user_id}/type`

**认证要求**: 需要管理员 Bearer Token

**路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| user_id | string | 是 | 用户ID |

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| user_type | string | 是 | 用户类型 |

**请求示例**:
```json
{
  "user_type": "enterprise"
}
```

**响应示例**:
```json
{
  "code": 1,
  "message": "用户类型已更新为: enterprise",
  "data": null
}
```

**类型说明**:
- `individual`: 个人用户
- `enterprise`: 企业用户
- `admin`: 管理员

---

### 2.5 更新用户会员信息

**接口地址**: `PUT /api/admin/users/{user_id}/member`

**认证要求**: 需要管理员 Bearer Token

**路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| user_id | string | 是 | 用户ID |

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| member_level | string | 是 | 会员等级 |
| member_expire_at | string | 是 | 会员到期时间（ISO 8601格式） |

**请求示例**:
```json
{
  "member_level": "premium",
  "member_expire_at": "2025-12-31T23:59:59"
}
```

**响应示例**:
```json
{
  "code": 1,
  "message": "会员信息已更新",
  "data": null
}
```

**会员等级说明**:
- `free`: 免费用户
- `basic`: 基础会员
- `premium`: 高级会员
- `enterprise`: 企业会员

---

## 3. 订单管理

### 3.1 获取订单列表

**接口地址**: `GET /api/admin/orders`

**认证要求**: 需要管理员 Bearer Token

**Query参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| keyword | string | 否 | 搜索关键词（订单号、用户ID） |
| payment_status | string | 否 | 支付状态：unpaid/paid/refunded |
| status | string | 否 | 订单状态：pending/completed/cancelled/failed |
| start_date | string | 否 | 开始日期（YYYY-MM-DD） |
| end_date | string | 否 | 结束日期（YYYY-MM-DD） |
| page | int | 否 | 页码，默认1 |
| page_size | int | 否 | 每页数量，默认20，最大100 |

**请求示例**:
```
GET /api/admin/orders?payment_status=paid&page=1&page_size=20
```

**响应示例**:
```json
{
  "code": 1,
  "message": "操作成功",
  "data": {
    "total": 50,
    "page": 1,
    "page_size": 20,
    "orders": []
  }
}
```

---

## 4. 知识库管理

### 4.1 获取知识库列表

**接口地址**: `GET /api/admin/knowledge-bases`

**认证要求**: 需要管理员 Bearer Token

**Query参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| keyword | string | 否 | 搜索关键词 |
| is_system | boolean | 否 | 是否为系统知识库 |
| page | int | 否 | 页码，默认1 |
| page_size | int | 否 | 每页数量，默认20，最大100 |

**请求示例**:
```
GET /api/admin/knowledge-bases?is_system=true&page=1&page_size=20
```

**响应示例**:
```json
{
  "code": 1,
  "message": "操作成功",
  "data": {
    "total": 50,
    "page": 1,
    "page_size": 20,
    "knowledge_bases": []
  }
}
```

---

## 5. 分销管理

### 5.1 获取分销商列表

**接口地址**: `GET /api/admin/distributors`

**认证要求**: 需要管理员 Bearer Token

**Query参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| status | string | 否 | 状态 |
| page | int | 否 | 页码，默认1 |
| page_size | int | 否 | 每页数量，默认20，最大100 |

**请求示例**:
```
GET /api/admin/distributors?page=1&page_size=20
```

**响应示例**:
```json
{
  "code": 1,
  "message": "操作成功",
  "data": {
    "total": 30,
    "page": 1,
    "page_size": 20,
    "distributors": []
  }
}
```

---

### 5.2 处理提现申请

**接口地址**: `PUT /api/admin/withdrawals/{withdrawal_id}/handle`

**认证要求**: 需要管理员 Bearer Token

**路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| withdrawal_id | string | 是 | 提现申请ID |

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| status | string | 是 | 处理状态：approved/rejected |
| handle_result | string | 是 | 处理结果说明 |
| transaction_id | string | 否 | 交易流水号（通过时必填） |

**请求示例**:
```json
{
  "status": "approved",
  "handle_result": "已转账",
  "transaction_id": "TXN202401011234567890"
}
```

**响应示例**:
```json
{
  "code": 1,
  "message": "提现申请已处理",
  "data": null
}
```

---

## 6. 系统统计

### 6.1 获取系统统计数据

**接口地址**: `GET /api/admin/stats`

**认证要求**: 需要管理员 Bearer Token

**响应示例**:
```json
{
  "code": 1,
  "message": "操作成功",
  "data": {
    "total_users": 1000,
    "total_members": 150,
    "total_knowledge_bases": 200,
    "total_orders": 500,
    "total_revenue": 50000.0,
    "today_new_users": 20,
    "today_new_orders": 15,
    "today_revenue": 1500.0,
    "active_distributors": 30
  }
}
```

**统计字段说明**:
- `total_users`: 总用户数
- `total_members`: 总会员数
- `total_knowledge_bases`: 总知识库数
- `total_orders`: 总订单数
- `total_revenue`: 总收入
- `today_new_users`: 今日新增用户
- `today_new_orders`: 今日新增订单
- `today_revenue`: 今日收入
- `active_distributors`: 活跃分销商数

---

## 附录

### A. 错误码说明

| 错误码 | 说明 |
|--------|------|
| 0 | 请求失败 |
| 1 | 请求成功 |

### B. 权限说明

管理员角色：
- `super_admin`: 超级管理员，拥有所有权限
- `admin`: 普通管理员，拥有部分权限

权限列表：
- `user.manage`: 用户管理
- `user.view`: 用户查看
- `member.manage`: 会员管理
- `member.view`: 会员查看
- `knowledge.manage`: 知识库管理
- `knowledge.view`: 知识库查看
- `mcp.manage`: MCP服务管理
- `mcp.view`: MCP服务查看
- `distribution.manage`: 分销管理
- `distribution.view`: 分销查看
- `order.view`: 订单查看
- `order.manage`: 订单管理
- `system.manage`: 系统管理
- `system.view`: 系统查看
- `log.view`: 日志查看

### C. Swagger文档

完整的API文档可以通过访问以下地址查看：

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

---

## 7. 文件管理

### 7.1 配置 OSS

**接口地址**: `POST /api/files/config/oss`

**认证要求**: 需要管理员 Bearer Token

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| access_key_id | string | 是 | 阿里云AccessKey ID |
| access_key_secret | string | 是 | 阿里云AccessKey Secret |
| region | string | 是 | OSS区域，默认cn-hangzhou |
| bucket | string | 是 | Bucket名称 |
| endpoint | string | 否 | 自定义endpoint |

**请求示例**:
```json
{
  "access_key_id": "LTAI...",
  "access_key_secret": "xxxxxx",
  "region": "cn-hangzhou",
  "bucket": "my-bucket"
}
```

**响应示例**:
```json
{
  "code": 1,
  "message": "OSS配置成功",
  "data": {
    "bucket": "my-bucket",
    "region": "cn-hangzhou"
  }
}
```

---

### 7.2 获取 OSS 配置状态

**接口地址**: `GET /api/files/config/oss`

**认证要求**: 需要管理员 Bearer Token

**响应示例**:
```json
{
  "code": 1,
  "message": "OSS已配置",
  "data": {
    "configured": true,
    "bucket": "my-bucket",
    "region": "cn-hangzhou"
  }
}
```

---

### 7.3 上传文件

**接口地址**: `POST /api/files/upload`

**认证要求**: 需要 Bearer Token

**请求类型**: `multipart/form-data`

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| file | File | 是 | 要上传的文件 |
| folder_path | string | 否 | 文件夹路径 |
| kb_name | string | 否 | 关联知识库名称 |
| original_filename | string | 否 | 原始文件名（解决微信小程序编码问题） |

**微信小程序上传示例**:
```javascript
wx.uploadFile({
  url: 'https://your-domain.com/api/files/upload',
  filePath: tempFile.path,
  name: 'file',
  formData: {
    original_filename: tempFile.name,
    folder_path: 'documents'
  },
  header: {
    'Authorization': 'Bearer ' + token
  }
});
```

**响应示例**:
```json
{
  "code": 1,
  "message": "文件 'example.pdf' 上传成功",
  "data": {
    "file_id": "file_1234567890abcdef",
    "file_name": "example.pdf",
    "file_type": "pdf",
    "file_size": 1048576,
    "file_url": "https://my-bucket.oss-cn-hangzhou.aliyuncs.com/files/file_1234567890abcdef.pdf",
    "mime_type": "application/pdf",
    "category": "document",
    "folder_path": "documents/tax",
    "status": "active",
    "created_at": "2024-01-13T15:30:00"
  }
}
```

---

### 7.4 批量上传文件

**接口地址**: `POST /api/files/upload/batch`

**认证要求**: 需要 Bearer Token

**请求类型**: `multipart/form-data`

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| files | File[] | 是 | 要上传的多个文件 |
| folder_path | string | 否 | 文件夹路径 |
| kb_name | string | 否 | 关联知识库名称 |
| original_filenames | string | 否 | 原始文件名列表（逗号分隔） |

**响应示例**:
```json
{
  "code": 1,
  "message": "批量上传完成，成功 3 个，失败 1 个",
  "data": {
    "total": 4,
    "success": 3,
    "failed": 1,
    "files": [],
    "errors": {
      "invalid_file.txt": "上传失败: 文件内容为空"
    }
  }
}
```

---

### 7.5 查询文件列表

**接口地址**: `GET /api/files/list`

**认证要求**: 需要 Bearer Token

**Query参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| file_type | string | 否 | 文件类型过滤（pdf、docx等） |
| category | string | 否 | 分类过滤（document、image、video、audio、other） |
| folder_path | string | 否 | 文件夹路径过滤 |
| kb_name | string | 否 | 知识库名称过滤 |
| keyword | string | 否 | 文件名关键词搜索 |
| page | int | 否 | 页码（默认1） |
| page_size | int | 否 | 每页数量（默认20） |

---

### 7.6 获取文件夹列表

**接口地址**: `GET /api/files/folders`

**认证要求**: 需要 Bearer Token

**响应示例**:
```json
{
  "code": 1,
  "message": "查询文件夹列表成功",
  "data": {
    "folders": [
      "documents",
      "documents/tax",
      "documents/finance",
      "images",
      "videos"
    ]
  }
}
```

---

### 7.7 获取文件信息

**接口地址**: `GET /api/files/{file_id}`

**认证要求**: 需要 Bearer Token

---

### 7.8 获取文件下载链接

**接口地址**: `GET /api/files/{file_id}/download`

**认证要求**: 需要 Bearer Token

**响应示例**:
```json
{
  "code": 1,
  "message": "获取下载链接成功",
  "data": {
    "download_url": "https://my-bucket.oss-cn-hangzhou.aliyuncs.com/files/example.pdf?expires=3600&signature=xxx",
    "file_id": "file_1234567890abcdef"
  }
}
```

---

### 7.9 更新文件信息

**接口地址**: `PUT /api/files/{file_id}`

**认证要求**: 需要 Bearer Token

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| file_name | string | 否 | 新文件名 |
| folder_path | string | 否 | 文件夹路径 |
| kb_name | string | 否 | 知识库名称 |

---

### 7.10 批量更新文件

**接口地址**: `PUT /api/files/batch`

**认证要求**: 需要 Bearer Token

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| file_ids | array | 是 | 文件ID列表 |
| folder_path | string | 否 | 文件夹路径 |
| kb_name | string | 否 | 知识库名称 |

---

### 7.11 删除文件

**接口地址**: `DELETE /api/files/{file_id}`

**认证要求**: 需要 Bearer Token

**Query参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| permanent | boolean | 否 | 是否永久删除（默认false） |

**删除说明**:
- 软删除（permanent=false）：将文件标记为deleted状态，可恢复
- 永久删除（permanent=true）：彻底删除，无法恢复

---

### 7.12 批量删除文件

**接口地址**: `DELETE /api/files/batch`

**认证要求**: 需要 Bearer Token

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| file_ids | array | 是 | 文件ID列表 |
| permanent | boolean | 否 | 是否永久删除（默认false） |

---

### 7.13 获取文件统计

**接口地址**: `GET /api/files/stats/my`

**认证要求**: 需要 Bearer Token

**响应示例**:
```json
{
  "code": 1,
  "message": "查询统计信息成功",
  "data": {
    "total_files": 150,
    "total_size_mb": 1024.5,
    "by_type": {
      "pdf": 50,
      "docx": 30,
      "pptx": 20,
      "image": 30,
      "video": 10,
      "audio": 10
    },
    "by_category": {
      "document": 100,
      "image": 30,
      "video": 10,
      "audio": 10
    },
    "today_uploads": 5,
    "month_uploads": 45
  }
}
```

---

## 8. 系统配置

### 8.1 获取分销配置

**接口地址**: `GET /api/config/distribution`

**认证要求**: 无（生产环境建议添加认证）

**响应示例**:
```json
{
  "code": 1,
  "message": "获取成功",
  "data": {
    "commission_rate": 10.0,
    "min_withdraw_amount": 50.0,
    "settlement_days": 7,
    "enabled": true
  }
}
```

---

### 8.2 更新分销配置

**接口地址**: `POST /api/config/distribution`

**认证要求**: 需要管理员 Bearer Token

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| commission_rate | float | 否 | 佣金比例（0-100） |
| min_withdraw_amount | float | 否 | 提现最低金额（>=0） |
| settlement_days | int | 否 | 结算天数（>=0） |
| enabled | boolean | 否 | 是否开启分销系统 |

**请求示例**:
```json
{
  "commission_rate": 15.0,
  "min_withdraw_amount": 100.0,
  "settlement_days": 7,
  "enabled": true
}
```

---

### 8.3 获取所有系统配置

**接口地址**: `GET /api/config/all`

**认证要求**: 需要管理员 Bearer Token

**响应示例**:
```json
{
  "code": 1,
  "message": "获取成功",
  "data": {
    "configs": [
      {
        "config_key": "commission_rate",
        "config_value": "10.0",
        "config_type": "float",
        "description": "分销佣金比例"
      }
    ]
  }
}
```

---

### 8.4 更新单个配置

**接口地址**: `POST /api/config/{config_key}`

**认证要求**: 需要管理员 Bearer Token

**路径参数**:
- `config_key`: 配置键名

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| config_value | any | 是 | 配置值 |

**请求示例**:
```json
{
  "config_value": 15.0
}
```

---

## 11. 仪表盘统计

### 11.1 获取仪表盘统计数据

**接口地址**: `GET /api/dashboard/stats`

**Query参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| user_id | string | 否 | 用户ID |

**响应示例**:
```json
{
  "code": 1,
  "message": "获取统计数据成功",
  "data": {
    "total_sessions": 150,
    "total_tokens": 500000,
    "total_files": 45,
    "active_sessions": 12
  }
}
```

---

### 11.2 获取 Token 趋势图表

**接口地址**: `GET /api/dashboard/token-chart`

**Query参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| user_id | string | 否 | 用户ID |
| days | int | 否 | 天数（默认7，范围1-365） |

**响应示例**:
```json
{
  "code": 1,
  "message": "获取token图表数据成功",
  "data": {
    "data": [
      {"date": "2024-01-01", "tokens": 15000},
      {"date": "2024-01-02", "tokens": 18000}
    ]
  }
}
```

---

## 附录

### A. 错误码说明

| 错误码 | 说明 |
|--------|------|
| 0 | 请求失败 |
| 1 | 请求成功 |
| 401 | 未授权 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 405 | 方法不允许 |
| 422 | 参数验证失败 |
| 500 | 服务器内部错误 |

### B. 权限说明

管理员角色：
- `super_admin`: 超级管理员，拥有所有权限
- `admin`: 普通管理员，拥有部分权限

权限列表：
- `user.manage`: 用户管理
- `user.view`: 用户查看
- `member.manage`: 会员管理
- `member.view`: 会员查看
- `knowledge.manage`: 知识库管理
- `knowledge.view`: 知识库查看
- `mcp.manage`: MCP服务管理
- `mcp.view`: MCP服务查看
- `distribution.manage`: 分销管理
- `distribution.view`: 分销查看
- `order.view`: 订单查看
- `order.manage`: 订单管理
- `system.manage`: 系统管理
- `system.view`: 系统查看
- `log.view`: 日志查看
- `*/*`: 超级管理员通配符

### C. Swagger文档

完整的API文档可以通过访问以下地址查看：

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

---

## 9. 个体户工商申报管理

### 9.1 获取所有工商申报列表（管理员）

**接口地址**: `GET /api/business-declaration/admin/list`

**认证要求**: 需要管理员 Bearer Token

**Query参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| user_id | string | 否 | 用户ID筛选 |
| status | string | 否 | 状态筛选：pending/processing/completed/rejected/need_supplement |
| declaration_type | string | 否 | 申报类型筛选：annual_report/change_registration/deregistration/tax_registration/invoice_application/license_application |
| page | int | 否 | 页码，默认1 |
| page_size | int | 否 | 每页数量，默认20，最大100 |

**请求示例**:
```
GET /api/business-declaration/admin/list?status=pending&page=1&page_size=20
```

**响应示例**:
```json
{
  "code": 1,
  "message": "操作成功",
  "data": {
    "total": 50,
    "page": 1,
    "page_size": 20,
    "declarations": [
      {
        "id": 1,
        "declaration_no": "BD2026012000001",
        "user_id": "user_123456",
        "business_name": "张三小吃店",
        "operator_name": "张三",
        "operator_phone": "13800138000",
        "declaration_type": "annual_report",
        "status": "pending",
        "created_at": "2026-01-20T10:00:00"
      }
    ]
  }
}
```

---

### 9.2 处理工商申报（管理员）

**接口地址**: `POST /api/business-declaration/admin/{declaration_id}/process`

**认证要求**: 需要管理员 Bearer Token

**路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| declaration_id | int | 是 | 申报ID |

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| status | string | 是 | 处理状态：processing/completed/rejected/need_supplement |
| approval_no | string | 否 | 受理号（已完成时必填） |
| approval_date | string | 否 | 受理日期（YYYY-MM-DD） |
| approval_proof_url | string | 否 | 批准凭证URL |
| process_result | string | 是 | 处理结果说明 |
| process_notes | string | 否 | 处理备注 |

**请求示例**:
```json
{
  "status": "completed",
  "approval_no": "SP2026012000001",
  "approval_date": "2026-01-20",
  "process_result": "年报审核通过",
  "process_notes": "材料齐全，符合要求"
}
```

**响应示例**:
```json
{
  "code": 1,
  "message": "申报 BD2026012000001 状态已更新为 completed",
  "data": {
    "declaration_id": 1,
    "declaration_no": "BD2026012000001",
    "status": "completed"
  }
}
```

**状态流转说明**:
- `pending` → `processing`（开始处理）
- `processing` → `completed`（处理完成）
- `processing` → `rejected`（拒绝申报）
- `processing` → `need_supplement`（需要补充材料）

---

### 9.3 获取全局工商申报统计（管理员）

**接口地址**: `GET /api/business-declaration/admin/stats`

**认证要求**: 需要管理员 Bearer Token

**响应示例**:
```json
{
  "code": 1,
  "message": "操作成功",
  "data": {
    "total_count": 100,
    "pending_count": 20,
    "processing_count": 10,
    "completed_count": 65,
    "rejected_count": 3,
    "need_supplement_count": 2,
    "annual_report_count": 60,
    "change_registration_count": 25,
    "deregistration_count": 15,
    "license_application_count": 10
  }
}
```

---

## 10. 智能报税管理

### 10.1 获取所有报税申报列表（管理员）

**接口地址**: `GET /api/tax-declaration/admin/list`

**认证要求**: 需要管理员 Bearer Token

**Query参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| user_id | string | 否 | 用户ID筛选 |
| status | string | 否 | 状态筛选：pending/processing/completed/rejected |
| tax_type | string | 否 | 税种筛选：pit/vat/cit |
| tax_period | string | 否 | 税期筛选：2024Q1/2024-01/2024 |
| page | int | 否 | 页码，默认1 |
| page_size | int | 否 | 每页数量，默认20，最大100 |

**请求示例**:
```
GET /api/tax-declaration/admin/list?status=pending&page=1&page_size=20
```

**响应示例**:
```json
{
  "code": 1,
  "message": "操作成功",
  "data": {
    "total": 50,
    "page": 1,
    "page_size": 20,
    "declarations": [
      {
        "id": 1,
        "declaration_no": "TD2026012000001",
        "user_id": "user_123456",
        "taxpayer_name": "张三",
        "taxpayer_phone": "13800138000",
        "taxpayer_type": "individual",
        "tax_type": "pit",
        "tax_period": "2024Q1",
        "total_income": 75000.00,
        "tax_amount": 2500.00,
        "status": "pending",
        "created_at": "2026-01-20T10:00:00"
      }
    ]
  }
}
```

---

### 10.2 处理报税申报（管理员）

**接口地址**: `POST /api/tax-declaration/admin/{declaration_id}/process`

**认证要求**: 需要管理员 Bearer Token

**路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| declaration_id | int | 是 | 申报ID |

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| status | string | 是 | 处理状态：processing/completed/rejected |
| total_income | float | 否 | 收入总额（不填则自动计算） |
| total_deduction | float | 否 | 扣除总额（不填则自动计算） |
| taxable_income | float | 否 | 应纳税所得额（不填则自动计算） |
| tax_amount | float | 否 | 应纳税额（不填则自动计算） |
| tax_paid | float | 否 | 已缴税额 |
| tax_refund | float | 否 | 应退税额（不填则自动计算） |
| declaration_serial_no | string | 否 | 申报流水号 |
| declaration_date | string | 否 | 申报日期（YYYY-MM-DD） |
| declaration_proof_url | string | 否 | 申报凭证URL |
| process_result | string | 是 | 处理结果说明 |
| process_notes | string | 否 | 处理备注 |

**请求示例**:
```json
{
  "status": "completed",
  "declaration_serial_no": "WS2026012000001",
  "declaration_date": "2026-01-20",
  "process_result": "已自动计算并完成申报",
  "process_notes": "系统自动计算"
}
```

**响应示例**:
```json
{
  "code": 1,
  "message": "申报 TD2026012000001 状态已更新为 completed",
  "data": {
    "declaration_id": 1,
    "declaration_no": "TD2026012000001",
    "status": "completed"
  }
}
```

**自动计算功能说明**:
- 如果管理员不填写计算结果（total_income、tax_amount等），系统会根据申报信息自动计算税额

---

### 10.3 获取全局报税统计（管理员）

**接口地址**: `GET /api/tax-declaration/admin/stats`

**认证要求**: 需要管理员 Bearer Token

**响应示例**:
```json
{
  "code": 1,
  "message": "操作成功",
  "data": {
    "total_count": 100,
    "pending_count": 20,
    "processing_count": 10,
    "completed_count": 65,
    "rejected_count": 5,
    "total_tax_amount": 150000.00
  }
}
```

---

## 12. 会员套餐管理

### 12.1 创建会员套餐

**接口地址**: `POST /api/member/packages`

**认证要求**: 需要管理员 Bearer Token

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| name | string | 是 | 套餐名称 |
| level | string | 是 | 会员等级：basic/premium/enterprise |
| price | float | 是 | 套餐价格 |
| duration | int | 是 | 有效期（天） |
| description | string | 否 | 套餐描述 |
| features | array | 否 | 套餐功能列表 |
| is_active | boolean | 否 | 是否启用，默认true |

**请求示例**:
```json
{
  "name": "基础会员套餐",
  "level": "basic",
  "price": 99.00,
  "duration": 30,
  "description": "适合个人用户",
  "features": [
    "智能报税（月度）",
    "知识库查询",
    "在线客服"
  ],
  "is_active": true
}
```

**响应示例**:
```json
{
  "code": 1,
  "message": "套餐创建成功",
  "data": {
    "package_id": "pkg_001",
    "name": "基础会员套餐",
    "level": "basic",
    "price": 99.00
  }
}
```

---

### 12.2 获取套餐列表

**接口地址**: `GET /api/member/packages`

**认证要求**: 无需认证

**Query参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| level | string | 否 | 会员等级筛选 |
| is_active | boolean | 否 | 是否只显示启用的套餐 |

**响应示例**:
```json
{
  "code": 1,
  "message": "获取成功",
  "data": {
    "total": 3,
    "packages": [
      {
        "package_id": "pkg_001",
        "name": "基础会员套餐",
        "level": "basic",
        "price": 99.00,
        "duration": 30,
        "description": "适合个人用户",
        "features": [
          "智能报税（月度）",
          "知识库查询"
        ],
        "is_active": true
      }
    ]
  }
}
```

---

### 12.3 获取套餐详情

**接口地址**: `GET /api/member/packages/{package_id}`

**认证要求**: 无需认证

**路径参数**:
- `package_id`: 套餐ID

---

### 12.4 更新套餐

**接口地址**: `PUT /api/member/packages/{package_id}`

**认证要求**: 需要管理员 Bearer Token

**请求参数**: 同创建套餐

---

### 12.5 删除套餐

**接口地址**: `DELETE /api/member/packages/{package_id}`

**认证要求**: 需要管理员 Bearer Token

**注意**: 删除套餐不会影响已购买的会员权益

---

## 13. 订单管理

### 13.1 创建订单

**接口地址**: `POST /api/member/orders`

**认证要求**: 需要 Bearer Token

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| package_id | string | 是 | 套餐ID |
| payment_method | string | 否 | 支付方式：wechat/alipay/balance |

**请求示例**:
```json
{
  "package_id": "pkg_001",
  "payment_method": "wechat"
}
```

**响应示例**:
```json
{
  "code": 1,
  "message": "订单创建成功",
  "data": {
    "order_id": "ord_2026012000001",
    "order_no": "ORD2026012000001",
    "package_id": "pkg_001",
    "amount": 99.00,
    "status": "pending",
    "created_at": "2026-01-20T10:00:00"
  }
}
```

---

### 13.2 获取订单详情

**接口地址**: `GET /api/member/orders/{order_id}`

**认证要求**: 需要 Bearer Token

---

### 13.3 获取订单列表

**接口地址**: `GET /api/member/orders`

**认证要求**: 需要 Bearer Token

**Query参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| status | string | 否 | 订单状态：pending/paid/cancelled/refunded |
| page | int | 否 | 页码 |
| page_size | int | 否 | 每页数量 |

**响应示例**:
```json
{
  "code": 1,
  "message": "获取成功",
  "data": {
    "total": 10,
    "orders": [
      {
        "order_id": "ord_001",
        "order_no": "ORD2026012000001",
        "package_name": "基础会员套餐",
        "amount": 99.00,
        "status": "paid",
        "created_at": "2026-01-20T10:00:00"
      }
    ]
  }
}
```

---

### 13.4 支付订单

**接口地址**: `POST /api/member/orders/{order_id}/payment`

**认证要求**: 需要 Bearer Token

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| payment_method | string | 是 | 支付方式：wechat/alipay/balance |

**响应示例**:
```json
{
  "code": 1,
  "message": "支付成功",
  "data": {
    "order_id": "ord_001",
    "status": "paid",
    "paid_at": "2026-01-20T10:05:00"
  }
}
```

---

### 13.5 取消订单

**接口地址**: `POST /api/member/orders/{order_id}/cancel`

**认证要求**: 需要 Bearer Token

**响应示例**:
```json
{
  "code": 1,
  "message": "订单已取消",
  "data": {
    "order_id": "ord_001",
    "status": "cancelled"
  }
}
```

---

## 14. 分销提现管理

### 14.1 获取提现申请列表（管理员）

**接口地址**: `GET /api/distribution/admin/withdrawals`

**认证要求**: 需要管理员 Bearer Token

**Query参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| status | string | 否 | 状态筛选：pending/approved/rejected |
| user_id | string | 否 | 用户ID筛选 |
| page | int | 否 | 页码，默认1 |
| page_size | int | 否 | 每页数量，默认20 |

**请求示例**:
```
GET /api/distribution/admin/withdrawals?status=pending&page=1&page_size=20
```

**响应示例**:
```json
{
  "code": 1,
  "message": "获取成功",
  "data": {
    "total": 30,
    "page": 1,
    "page_size": 20,
    "withdrawals": [
      {
        "withdrawal_id": "wd_001",
        "user_id": "user_123",
        "nickname": "张三",
        "phone": "13800138000",
        "amount": 500.00,
        "commission_available": 1000.00,
        "status": "pending",
        "created_at": "2026-01-20T10:00:00"
      }
    ]
  }
}
```

---

### 14.2 获取分销商列表（管理员）

**接口地址**: `GET /api/distribution/admin/distributors`

**认证要求**: 需要管理员 Bearer Token

**Query参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| status | string | 否 | 状态筛选：active/inactive |
| page | int | 否 | 页码，默认1 |
| page_size | int | 否 | 每页数量，默认20 |

**响应示例**:
```json
{
  "code": 1,
  "message": "获取成功",
  "data": {
    "total": 100,
    "distributors": [
      {
        "user_id": "user_123",
        "nickname": "张三",
        "phone": "13800138000",
        "referrer_code": "REF123456",
        "total_commission": 5000.00,
        "available_commission": 1000.00,
        "total_orders": 50,
        "status": "active",
        "created_at": "2026-01-01T00:00:00"
      }
    ]
  }
}
```

---

### 14.3 审核通过提现申请

**接口地址**: `POST /api/distribution/admin/withdrawals/{withdrawal_id}/approve`

**认证要求**: 需要管理员 Bearer Token

**路径参数**:
- `withdrawal_id`: 提现申请ID

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| transaction_id | string | 是 | 交易流水号 |
| notes | string | 否 | 审核备注 |

**请求示例**:
```json
{
  "transaction_id": "TXN202601201234567890",
  "notes": "已转账至用户账户"
}
```

**响应示例**:
```json
{
  "code": 1,
  "message": "提现已审核通过",
  "data": {
    "withdrawal_id": "wd_001",
    "status": "approved",
    "transaction_id": "TXN202601201234567890"
  }
}
```

---

### 14.4 审核拒绝提现申请

**接口地址**: `POST /api/distribution/admin/withdrawals/{withdrawal_id}/reject`

**认证要求**: 需要管理员 Bearer Token

**路径参数**:
- `withdrawal_id`: 提现申请ID

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| reason | string | 是 | 拒绝原因 |

**请求示例**:
```json
{
  "reason": "银行账户信息不正确"
}
```

**响应示例**:
```json
{
  "code": 1,
  "message": "提现已拒绝",
  "data": {
    "withdrawal_id": "wd_001",
    "status": "rejected"
  }
}
```

---

## 15. 知识库管理

### 15.1 创建知识库

**接口地址**: `POST /api/knowledge-base/create`

**认证要求**: 需要 Bearer Token

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| name | string | 是 | 知识库名称 |
| description | string | 否 | 描述 |
| user_id | string | 是 | 用户ID |
| type_id | string | 否 | 知识库类型ID |
| is_system | boolean | 否 | 是否系统知识库（默认false） |
| chunking_rule | string | 否 | 分块规则：fixed_size/semantic/recursive |
| chunk_size | int | 否 | 分块大小（默认5000） |
| chunk_overlap | int | 否 | 分块重叠（默认200） |
| embedder_model | string | 否 | 嵌入模型 |

**请求示例**:
```json
{
  "name": "我的税务文档",
  "description": "个人收集的税务相关文档",
  "user_id": "user_123",
  "type_id": "type_001",
  "is_system": false,
  "chunking_rule": "fixed_size",
  "chunk_size": 5000,
  "chunk_overlap": 200
}
```

**响应示例**:
```json
{
  "code": 1,
  "message": "知识库 '我的税务文档' 创建成功",
  "data": {
    "kb_name": "我的税务文档",
    "user_id": "user_123",
    "type_id": "type_001",
    "is_system": false
  }
}
```

**注意**:
- 创建系统知识库（is_system=true）需要管理员权限

---

### 15.2 获取系统知识库列表

**接口地址**: `GET /api/knowledge-base/list/system`

**认证要求**: 需要 Bearer Token

**Query参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| type_id | string | 否 | 知识库类型ID筛选 |

**响应示例**:
```json
{
  "code": 1,
  "message": "列出系统知识库成功",
  "data": {
    "knowledge_bases": [
      {
        "kb_name": "税收政策库",
        "description": "包含各类税收政策和法规",
        "type_id": "type_001",
        "type_name": "税收知识",
        "is_system": true,
        "created_at": "2024-01-01T10:00:00",
        "created_by": "admin",
        "document_count": 150
      }
    ],
    "total": 1
  }
}
```

---

### 15.3 获取用户知识库列表

**接口地址**: `GET /api/knowledge-base/list/user`

**认证要求**: 需要 Bearer Token

**Query参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| kb_name | string | 否 | 知识库名称（精确匹配） |
| type_id | string | 否 | 知识库类型ID筛选 |

**响应示例**:
```json
{
  "code": 1,
  "message": "列出个人知识库成功",
  "data": {
    "knowledge_bases": [
      {
        "kb_name": "我的税务文档",
        "description": "个人收集的税务相关文档",
        "type_id": "type_001",
        "type_name": "税收知识",
        "is_system": false,
        "created_at": "2024-01-15T10:00:00",
        "created_by": "user_123",
        "document_count": 25
      }
    ],
    "total": 1
  }
}
```

---

### 15.4 上传文档到知识库

**接口地址**: `POST /api/knowledge-base/upload`

**认证要求**: 需要 Bearer Token

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| kb_name | string | 是 | 知识库名称 |
| user_id | string | 是 | 用户ID |
| files | array | 是 | 文件列表（filename + file_base64） |
| chunking_rule | string | 否 | 分块规则 |
| chunk_size | int | 否 | 分块大小 |
| chunk_overlap | int | 否 | 分块重叠 |

**请求示例**:
```json
{
  "kb_name": "我的税务文档",
  "user_id": "user_123",
  "files": [
    {
      "filename": "增值税政策.pdf",
      "file_base64": "JVBERi0xLjcKCjEgMCBvYm..."
    }
  ],
  "chunking_rule": "fixed_size",
  "chunk_size": 5000,
  "chunk_overlap": 200
}
```

**响应示例**:
```json
{
  "code": 1,
  "message": "成功上传 1 个文档",
  "data": {
    "results": [
      {
        "status": "success",
        "message": "文档 增值税政策.pdf 已成功上传到知识库",
        "filename": "增值税政策.pdf",
        "user_id": "user_123"
      }
    ]
  }
}
```

---

### 15.5 批量上传文档

**接口地址**: `POST /api/knowledge-base/upload-batch`

**认证要求**: 需要 Bearer Token

**请求参数**: 同上传接口，优化了批量处理逻辑

---

### 15.6 搜索知识库

**接口地址**: `POST /api/knowledge-base/search`

**认证要求**: 需要 Bearer Token

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| user_id | string | 是 | 用户ID |
| kb_name | string | 是 | 知识库名称 |
| query | string | 是 | 搜索关键词 |
| top_k | int | 否 | 返回结果数量（默认5） |
| search_type | string | 否 | 搜索类型：similarity/keyword/hybrid |

**请求示例**:
```json
{
  "user_id": "user_123",
  "kb_name": "我的税务文档",
  "query": "增值税税率",
  "top_k": 5,
  "search_type": "similarity"
}
```

**响应示例**:
```json
{
  "code": 1,
  "message": "搜索知识库成功",
  "data": {
    "results": [
      {
        "rank": 1,
        "id": "chunk_001",
        "name": "增值税政策.txt",
        "content": "增值税税率分为三档：17%、13%和零税率...",
        "score": 0.95,
        "meta_data": {
          "source": "增值税政策.txt",
          "page": 1
        }
      }
    ],
    "count": 1
  }
}
```

---

### 15.7 获取知识库文档列表

**接口地址**: `GET /api/knowledge-base/documents`

**认证要求**: 无

**Query参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| kb_name | string | 是 | 知识库名称 |
| user_id | string | 是 | 用户ID |

**响应示例**:
```json
{
  "code": 1,
  "message": "获取文档列表成功",
  "data": {
    "documents": [
      {
        "filename": "增值税政策.txt",
        "total_chunks": 5,
        "parse_status": "已解析",
        "created_at": "2026-01-13T10:00:00"
      }
    ],
    "total_documents": 1
  }
}
```

---

### 15.8 删除知识库

**接口地址**: `DELETE /api/knowledge-base/{kb_name}`

**认证要求**: 需要 Bearer Token

**路径参数**:
- `kb_name`: 知识库名称

**响应示例**:
```json
{
  "code": 1,
  "message": "知识库 '我的税务文档' 删除成功",
  "data": null
}
```

**注意**: 删除操作不可逆，会删除所有文档和向量数据

---

### 15.9 从文件系统导入文件到知识库

**接口地址**: `POST /api/knowledge-base/import-files`

**认证要求**: 需要 Bearer Token

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| kb_name | string | 是 | 目标知识库名称 |
| user_id | string | 是 | 用户ID |
| file_ids | array | 是 | 文件ID列表 |
| chunking_rule | string | 否 | 分块规则 |
| chunk_size | int | 否 | 分块大小 |
| chunk_overlap | int | 否 | 分块重叠 |
| metadata | object | 否 | 额外元数据 |

**请求示例**:
```json
{
  "kb_name": "我的税务文档",
  "user_id": "user_123",
  "file_ids": [
    "file_1234567890abcdef",
    "file_2345678901bcdef"
  ],
  "chunking_rule": "fixed_size",
  "chunk_size": 5000,
  "chunk_overlap": 200
}
```

**响应示例**:
```json
{
  "code": 1,
  "message": "成功导入 2 个文件",
  "data": {
    "results": [
      {
        "status": "success",
        "message": "文档 增值税政策.pdf 已成功导入知识库",
        "filename": "增值税政策.pdf",
        "file_id": "file_1234567890abcdef",
        "user_id": "user_123"
      }
    ]
  }
}
```

---

## 16. 知识库类型管理

### 16.1 获取知识库类型列表

**接口地址**: `GET /api/knowledge-types/list`

**认证要求**: 无

**Query参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| status | string | 否 | 状态筛选：active/inactive |
| is_system | string | 否 | 是否系统类型：true/false |

**响应示例**:
```json
{
  "code": 1,
  "message": "获取成功",
  "data": [
    {
      "type_id": "type_012",
      "type_name": "增值税",
      "type_code": "vat_tax",
      "description": "增值税相关政策、计算、申报等",
      "icon": "percent",
      "sort_order": 12,
      "is_system": true,
      "status": "active",
      "created_at": "2026-01-13T10:00:00"
    }
  ]
}
```

---

### 16.2 获取知识库类型详情

**接口地址**: `GET /api/knowledge-types/{type_id}`

**认证要求**: 无

**路径参数**:
- `type_id`: 知识库类型ID

---

### 16.3 创建知识库类型（管理员）

**接口地址**: `POST /api/knowledge-types/`

**认证要求**: 需要管理员 Bearer Token

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| type_name | string | 是 | 类型名称 |
| type_code | string | 是 | 类型编码（唯一标识） |
| description | string | 否 | 类型描述 |
| icon | string | 否 | 图标名称 |
| sort_order | int | 否 | 排序顺序 |

**请求示例**:
```json
{
  "type_name": "自定义类型",
  "type_code": "custom_type",
  "description": "自定义知识库分类",
  "icon": "folder",
  "sort_order": 100
}
```

**响应示例**:
```json
{
  "code": 1,
  "message": "创建成功",
  "data": {
    "type_id": "type_100",
    "type_name": "自定义类型",
    "type_code": "custom_type",
    "is_system": false
  }
}
```

---

### 16.4 更新知识库类型（管理员）

**接口地址**: `PUT /api/knowledge-types/{type_id}`

**认证要求**: 需要管理员 Bearer Token

**路径参数**:
- `type_id`: 知识库类型ID

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| type_name | string | 否 | 类型名称 |
| description | string | 否 | 类型描述 |
| icon | string | 否 | 图标 |
| sort_order | int | 否 | 排序 |
| status | string | 否 | 状态：active/inactive |

---

### 16.5 删除知识库类型（管理员）

**接口地址**: `DELETE /api/knowledge-types/{type_id}`

**认证要求**: 需要管理员 Bearer Token

**路径参数**:
- `type_id`: 知识库类型ID

**注意**:
- 系统内置类型（is_system=true）不可删除
- 如果类型下有关联的知识库，需要先处理

---

### 16.6 搜索知识库内容

**接口地址**: `POST /api/knowledge-types/search/content`

**认证要求**: 无

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| keyword | string | 是 | 搜索关键词 |
| user_id | string | 否 | 用户ID |
| type_id | string | 否 | 知识库类型ID |
| limit | int | 否 | 返回数量（默认20，最大100） |
| offset | int | 否 | 偏移量（默认0） |

**响应示例**:
```json
{
  "code": 1,
  "message": "搜索成功",
  "data": {
    "keyword": "增值税",
    "total": 15,
    "items": [
      {
        "kb_name": "vat_kb_001",
        "filename": "增值税政策.txt",
        "content_preview": "增值税税率分为三档：17%、13%和零税率...",
        "rank": 0.95
      }
    ]
  }
}
```

---

### 16.7 搜索知识库

**接口地址**: `POST /api/knowledge-types/search/bases`

**认证要求**: 无

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| keyword | string | 是 | 搜索关键词 |
| user_id | string | 否 | 用户ID |
| limit | int | 否 | 返回数量（默认20） |
| offset | int | 否 | 偏移量（默认0） |

**响应示例**:
```json
{
  "code": 1,
  "message": "搜索成功",
  "data": {
    "keyword": "增值税",
    "total": 3,
    "items": [
      {
        "kb_name": "增值税政策库",
        "description": "增值税相关政策文档",
        "document_count": 10,
        "type_name": "增值税"
      }
    ]
  }
}
```
