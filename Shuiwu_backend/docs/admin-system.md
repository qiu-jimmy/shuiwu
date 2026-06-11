# 管理系统 API 文档

## 概述

管理系统提供了完整的管理员功能,包括管理员登录、用户管理、订单管理、知识库管理、分销管理和系统统计等功能。

**基础路径:** `/api/admin`

**默认管理员账户:**
- 用户名: `admin`
- 密码: `admin123`

**⚠️ 重要提示:** 生产环境请务必修改默认密码!

---

## 功能模块

### 1. 管理员认证

#### 1.1 管理员登录

**接口:** `POST /api/admin/login`

**请求参数:**
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**响应示例:**
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
        "user.manage", "user.view",
        "member.manage", "member.view",
        "knowledge.manage", "knowledge.view",
        "mcp.manage", "mcp.view",
        "distribution.manage", "distribution.view",
        "order.view", "order.manage",
        "system.manage", "system.view",
        "log.view"
      ]
    }
  }
}
```

**注意:** 管理员 token 与普通用户 token 不同,需要使用专门的登录接口。

---

#### 1.2 获取当前管理员信息

**接口:** `GET /api/admin/me`

**请求头:**
```
Authorization: Bearer {admin_token}
```

**响应示例:**
```json
{
  "code": 1,
  "message": "操作成功",
  "data": {
    "admin_id": "admin_001",
    "username": "admin",
    "nickname": "系统管理员",
    "role": "super_admin",
    "permissions": ["user.manage", "user.view", "..."]
  }
}
```

---

### 2. 用户管理

#### 2.1 获取用户列表

**接口:** `GET /api/admin/users`

**查询参数:**
- `keyword`: 搜索关键词(手机号、昵称、用户ID)
- `status`: 用户状态(normal, disabled, banned)
- `user_type`: 用户类型(individual, enterprise, admin)
- `member_level`: 会员等级(free, basic, premium, enterprise)
- `start_date`: 注册开始日期(YYYY-MM-DD)
- `end_date`: 注册结束日期(YYYY-MM-DD)
- `page`: 页码(默认1)
- `page_size`: 每页数量(默认20,最大100)

**响应示例:**
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
        "member_expire_at": "2025-12-31T23:59:59",
        "register_time": "2024-01-01T00:00:00",
        "last_login_time": "2024-01-15T10:30:00"
      }
    ]
  }
}
```

---

#### 2.2 更新用户状态

**接口:** `PUT /api/admin/users/{user_id}/status`

**请求参数:**
```json
{
  "status": "disabled",
  "reason": "违反用户协议"
}
```

**状态说明:**
- `normal`: 正常
- `disabled`: 禁用
- `banned`: 封禁

---

#### 2.3 更新用户类型

**接口:** `PUT /api/admin/users/{user_id}/type`

**请求参数:**
```json
{
  "user_type": "enterprise"
}
```

**类型说明:**
- `individual`: 个人用户
- `enterprise`: 企业用户
- `admin`: 管理员

---

#### 2.4 更新用户会员信息

**接口:** `PUT /api/admin/users/{user_id}/member`

**请求参数:**
```json
{
  "member_level": "premium",
  "member_expire_at": "2025-12-31T23:59:59"
}
```

**会员等级:**
- `free`: 免费用户
- `basic`: 基础会员
- `premium`: 高级会员
- `enterprise`: 企业会员

---

### 3. 订单管理

#### 3.1 获取订单列表

**接口:** `GET /api/admin/orders`

**查询参数:**
- `keyword`: 搜索关键词(订单号、用户ID)
- `payment_status`: 支付状态(unpaid, paid, refunded)
- `status`: 订单状态(pending, completed, cancelled, failed)
- `start_date`: 开始日期(YYYY-MM-DD)
- `end_date`: 结束日期(YYYY-MM-DD)
- `page`: 页码
- `page_size`: 每页数量

---

### 4. 知识库管理

#### 4.1 获取知识库列表

**接口:** `GET /api/admin/knowledge-bases`

**查询参数:**
- `keyword`: 搜索关键词
- `is_system`: 是否为系统知识库(true/false)
- `page`: 页码
- `page_size`: 每页数量

---

### 5. 分销管理

#### 5.1 获取分销商列表

**接口:** `GET /api/admin/distributors`

**查询参数:**
- `status`: 状态(active, inactive, pending)
- `page`: 页码
- `page_size`: 每页数量

---

#### 5.2 处理提现申请

**接口:** `PUT /api/admin/withdrawals/{withdrawal_id}/handle`

**请求参数:**
```json
{
  "status": "approved",
  "handle_result": "审核通过",
  "transaction_id": "wx_202401151234567890"
}
```

**处理状态:**
- `approved`: 通过
- `rejected`: 拒绝

---

### 6. 系统统计

#### 6.1 获取系统统计

**接口:** `GET /api/admin/stats`

**响应示例:**
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

---

## 测试

运行管理员系统测试:

```bash
python test/test_admin_e2e.py
```

**测试内容包括:**
1. 管理员登录
2. 获取当前管理员信息
3. 获取用户列表
4. 获取系统统计
5. 获取订单列表
6. 获取知识库列表
7. 获取分销商列表
8. 更新用户状态

---

## 权限说明

### 管理员权限列表

| 权限代码 | 说明 |
|---------|------|
| `user.manage` | 用户管理(增删改) |
| `user.view` | 查看用户信息 |
| `member.manage` | 会员管理 |
| `member.view` | 查看会员信息 |
| `knowledge.manage` | 知识库管理 |
| `knowledge.view` | 查看知识库 |
| `mcp.manage` | MCP服务管理 |
| `mcp.view` | 查看MCP服务 |
| `distribution.manage` | 分销管理 |
| `distribution.view` | 查看分销信息 |
| `order.view` | 查看订单 |
| `order.manage` | 订单管理 |
| `system.manage` | 系统管理 |
| `system.view` | 查看系统信息 |
| `log.view` | 查看日志 |

### 超级管理员

超级管理员拥有所有权限,权限代码为 `super_admin`。

---

## 安全建议

1. **修改默认密码:** 生产环境务必修改默认管理员密码
2. **使用HTTPS:** 生产环境必须使用HTTPS
3. **限制访问:** 管理后台应限制IP访问
4. **日志记录:** 记录所有管理操作日志
5. **定期审计:** 定期审计管理员操作记录

---

## 后续开发建议

### 数据库层面的改进

当前管理员信息是硬编码在代码中的,生产环境建议:

1. 创建 `admins` 表存储管理员信息
2. 支持多个管理员账户
3. 支持不同的角色和权限配置
4. 记录管理员操作日志

### 建议的表结构

```sql
CREATE TABLE business.admins (
    admin_id VARCHAR(50) PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nickname VARCHAR(100),
    role VARCHAR(50) NOT NULL,
    permissions TEXT[], -- PostgreSQL 数组类型
    status VARCHAR(20) DEFAULT 'active',
    last_login_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE business.admin_action_logs (
    id SERIAL PRIMARY KEY,
    admin_id VARCHAR(50) REFERENCES admins(admin_id),
    action_type VARCHAR(50) NOT NULL,
    action_module VARCHAR(50) NOT NULL,
    action_detail JSONB,
    target_user_id VARCHAR(50),
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## API 文档

完整的 API 文档可以通过以下方式访问:

- **Swagger UI:** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc

在 Swagger UI 中,可以找到 "管理系统" 标签查看所有管理员接口。
