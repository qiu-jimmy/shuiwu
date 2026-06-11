# 问题反馈系统 API 文档

## 接口拆分说明

系统已将问题反馈接口拆分为 **用户端** 和 **管理员端** 两个独立模块，方便对接后台管理系统。

## 认证说明

**所有接口均需要 JWT token 认证**，请在请求头中携带：

```http
Authorization: Bearer {access_token}
Content-Type: application/json
```

- **用户端接口**：使用普通用户 token（登录时获取）
- **管理员端接口**：使用管理员 token（需要管理员权限）

---

## 用户端接口（移动端/Web前端）

**基础路径：** `/api/feedback`

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 提交反馈 | POST | `/api/feedback/submit` | 用户提交问题反馈 |
| 我的反馈列表 | GET | `/api/feedback/my` | 获取当前用户的反馈列表 |
| 反馈详情 | GET | `/api/feedback/{feedback_id}` | 获取反馈详情 |

### 用户端接口详情

#### 1. 提交问题反馈
```http
POST /api/feedback/submit
Content-Type: application/json
Authorization: Bearer {access_token}

{
    "feedback_type": "bug",
    "feedback_content": "发现登录页面在移动端显示异常",
    "feedback_images": ["https://example.com/image1.png"]
}
```

**问题类型：**
| 值 | 说明 |
|---|------|
| `bug` | 系统错误 |
| `feature` | 功能建议 |
| `complaint` | 投诉 |
| `other` | 其他 |

**响应示例：**
```json
{
    "code": 1,
    "message": "反馈提交成功，我们会尽快处理",
    "data": {
        "feedback_id": "FB1234567890ABCDE"
    }
}
```

#### 2. 获取我的反馈列表
```http
GET /api/feedback/my?status=pending&page=1&page_size=20
Authorization: Bearer {access_token}
```

**查询参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `status` | string | 否 | 筛选状态（pending, processing, resolved, closed）|
| `page` | int | 否 | 页码（默认1） |
| `page_size` | int | 否 | 每页数量（默认20，最大100） |

**响应示例：**
```json
{
    "code": 1,
    "message": "操作成功",
    "data": {
        "total": 5,
        "page": 1,
        "page_size": 20,
        "feedbacks": [
            {
                "feedback_id": "FB1234567890ABCDE",
                "feedback_type": "bug",
                "feedback_content": "登录页面在移动端显示异常",
                "status": "processing",
                "priority": "high",
                "created_at": "2024-01-14T08:00:00"
            }
        ]
    }
}
```

#### 3. 获取反馈详情
```http
GET /api/feedback/{feedback_id}
Authorization: Bearer {access_token}
```

---

## 管理员端接口（后台管理系统）

**基础路径：** `/api/admin/feedback`

**注意：** 所有管理员接口需要在请求头中携带管理员 JWT token

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 反馈列表 | GET | `/api/admin/feedback/list` | 获取所有反馈列表 |
| 反馈详情 | GET | `/api/admin/feedback/{feedback_id}` | 获取反馈详情（含用户信息） |
| 更新状态 | PUT | `/api/admin/feedback/{feedback_id}/status` | 更新反馈状态/优先级 |
| 回复反馈 | POST | `/api/admin/feedback/{feedback_id}/reply` | 管理员回复 |
| 关闭反馈 | POST | `/api/admin/feedback/{feedback_id}/close` | 关闭反馈 |
| 删除反馈 | DELETE | `/api/admin/feedback/{feedback_id}` | 删除反馈 |
| 统计信息 | GET | `/api/admin/feedback/stats/overview` | 获取统计数据 |
| 导出Excel | GET | `/api/admin/feedback/export/excel` | 导出反馈数据 |

### 管理员端接口详情

#### 1. 获取所有反馈列表
```http
GET /api/admin/feedback/list?status=pending&page=1&page_size=20
Authorization: Bearer {admin_access_token}
```

**查询参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `status` | string | 否 | 筛选状态（pending, processing, resolved, closed） |
| `feedback_type` | string | 否 | 筛选类型（bug, feature, complaint, other） |
| `priority` | string | 否 | 筛选优先级（low, normal, high, urgent） |
| `page` | int | 否 | 页码（默认1） |
| `page_size` | int | 否 | 每页数量（默认20，最大100） |

**排序规则：** 优先级（urgent > high > normal > low）+ 创建时间倒序

**响应示例：**
```json
{
    "code": 1,
    "message": "操作成功",
    "data": {
        "total": 50,
        "page": 1,
        "page_size": 20,
        "feedbacks": [
            {
                "feedback_id": "FB1234567890ABCDE",
                "user_id": "user_001",
                "feedback_type": "bug",
                "feedback_content": "登录页面在移动端显示异常",
                "status": "processing",
                "priority": "high",
                "user_nickname": "测试用户",
                "user_phone": "138****8000"
            }
        ]
    }
}
```

#### 2. 获取反馈详情（管理员）
```http
GET /api/admin/feedback/{feedback_id}
Authorization: Bearer {admin_access_token}
```

**返回数据包含：**
- 反馈基本信息
- 用户信息（昵称、手机号、会员等级、状态）
- 管理员回复历史
- 处理状态和优先级

#### 3. 更新反馈状态
```http
PUT /api/admin/feedback/{feedback_id}/status
Authorization: Bearer {admin_access_token}
Content-Type: application/json

{
    "status": "processing",
    "priority": "high"
}
```

**状态值：**
| 值 | 说明 |
|---|------|
| `pending` | 待处理 |
| `processing` | 处理中 |
| `resolved` | 已解决 |
| `closed` | 已关闭 |

**优先级：**
| 值 | 说明 |
|---|------|
| `low` | 低 |
| `normal` | 中 |
| `high` | 高 |
| `urgent` | 紧急 |

#### 4. 管理员回复
```http
POST /api/admin/feedback/{feedback_id}/reply
Authorization: Bearer {admin_access_token}
Content-Type: application/json

{
    "admin_reply": "您好，感谢您的反馈！我们已收到您的问题，正在加紧处理中。"
}
```

**注意：** 回复后反馈状态会自动变为"处理中"

#### 5. 关闭反馈
```http
POST /api/admin/feedback/{feedback_id}/close
Authorization: Bearer {admin_access_token}
```

**使用场景：**
- 问题已解决，用户无异议
- 用户主动撤回反馈
- 反馈无效或重复

#### 6. 删除反馈
```http
DELETE /api/admin/feedback/{feedback_id}
Authorization: Bearer {admin_access_token}
```

**注意：** 仅允许删除已关闭的反馈

#### 7. 获取统计信息
```http
GET /api/admin/feedback/stats/overview
Authorization: Bearer {admin_access_token}
```

**返回数据：**
```json
{
    "code": 1,
    "message": "获取成功",
    "data": {
        "stats": {
            "pending_count": 5,
            "processing_count": 3,
            "resolved_count": 20,
            "closed_count": 10,
            "urgent_count": 2
        }
    }
}
```

#### 8. 导出Excel（待实现）
```http
GET /api/admin/feedback/export/excel?start_date=2024-01-01&end_date=2024-12-31
Authorization: Bearer {admin_access_token}
```

---

## 响应格式

### 成功响应
```json
{
    "code": 1,
    "message": "操作成功",
    "data": { ... }
}
```

### 错误响应
```json
{
    "code": 0,
    "message": "错误描述",
    "data": null
}
```

---

## 状态码

| HTTP状态码 | 说明 |
|-----------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

## 后台管理系统对接示例

### Vue.js 示例

```javascript
// API 基础配置
const API_BASE = 'http://127.0.0.1:8000'
const ADMIN_TOKEN = 'your_admin_jwt_token'  // 从登录接口获取

// 通用请求配置
const headers = {
    'Authorization': `Bearer ${ADMIN_TOKEN}`,
    'Content-Type': 'application/json'
}

// 获取反馈列表
async function getFeedbackList(params) {
    const { status, page, page_size } = params
    const response = await fetch(
        `${API_BASE}/api/admin/feedback/list?status=${status}&page=${page}&page_size=${page_size}`,
        { headers }
    )
    return await response.json()
}

// 更新反馈状态
async function updateFeedbackStatus(feedbackId, status, priority) {
    const response = await fetch(
        `${API_BASE}/api/admin/feedback/${feedbackId}/status`,
        {
            method: 'PUT',
            headers,
            body: JSON.stringify({ status, priority })
        }
    )
    return await response.json()
}

// 回复反馈
async function replyFeedback(feedbackId, reply) {
    const response = await fetch(
        `${API_BASE}/api/admin/feedback/${feedbackId}/reply`,
        {
            method: 'POST',
            headers,
            body: JSON.stringify({ admin_reply: reply })
        }
    )
    return await response.json()
}

// 获取统计信息
async function getStats() {
    const response = await fetch(
        `${API_BASE}/api/admin/feedback/stats/overview`,
        { headers }
    )
    return await response.json()
}
```

### React 示例

```javascript
import axios from 'axios'

const API_BASE = 'http://127.0.0.1:8000'
const ADMIN_TOKEN = 'your_admin_jwt_token'  // 从登录接口获取

// 创建 axios 实例，统一配置
const api = axios.create({
    baseURL: API_BASE,
    headers: {
        'Authorization': `Bearer ${ADMIN_TOKEN}`,
        'Content-Type': 'application/json'
    }
})

// 获取反馈列表
const getFeedbackList = async (params) => {
    const { status, page, page_size } = params
    const { data } = await api.get('/api/admin/feedback/list', {
        params: { status, page, page_size }
    })
    return data
}

// 更新状态
const updateStatus = async (feedbackId, status, priority) => {
    const { data } = await api.put(
        `/api/admin/feedback/${feedbackId}/status`,
        { status, priority }
    )
    return data
}

// 回复反馈
const replyFeedback = async (feedbackId, reply) => {
    const { data } = await api.post(
        `/api/admin/feedback/${feedbackId}/reply`,
        { admin_reply: reply }
    )
    return data
}
```

---

## 文件结构

```
app/
├── api/
│   ├── feedback.py           # 用户端路由
│   └── admin_feedback.py     # 管理员端路由 ✨ 新增
├── services/feedback/
│   └── feedback_service.py   # 业务逻辑
└── schemas/
    └── feedback.py           # Schema定义
```

---

## Swagger 文档

访问 `http://127.0.0.1:8000/docs` 查看完整的交互式 API 文档。
