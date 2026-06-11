# 微信小程序接入指南

## 目录
- [概述](#概述)
- [前置条件](#前置条件)
- [服务器配置](#服务器配置)
- [API接口文档](#api接口文档)
- [小程序端实现示例](#小程序端实现示例)
- [最佳实践](#最佳实践)
- [常见问题](#常见问题)

---

## 概述

本文档提供FastAPI后端系统接入微信小程序的完整指南。系统支持以下核心功能：
- AI智能对话（普通对话、搜索增强对话、RAG知识库对话）
- 会话管理（创建、查询、更新、删除）
- 知识库管理（创建、上传文档、搜索）
- 文档生成与导出
- 数据统计与监控

---

## 前置条件

### 1. 微信小程序账号
- 已注册微信小程序账号
- 完成[微信开放平台](https://open.weixin.qq.com/)开发者资质认证
- 获取AppID和AppSecret

### 2. 服务器要求
- **域名**: 必须已备案的域名
- **HTTPS**: 必须使用HTTPS协议
- **SSL证书**: 有效的SSL证书（支持TLS 1.2+）
- **服务器配置**: 建议配置 2核4G 以上

### 3. 后端服务
- FastAPI后端已部署
- API服务可公网访问
- PostgreSQL数据库正常运行

---

## 服务器配置

### 1. 微信公众平台配置

登录 [微信公众平台](https://mp.weixin.qq.com/) 进行以下配置：

#### 步骤1: 配置服务器域名
```
开发 -> 开发设置 -> 服务器域名
```

配置以下合法域名：

| 类型 | 域名 | 说明 |
|------|------|------|
| request合法域名 | `https://your-domain.com` | API请求域名 |
| uploadFile合法域名 | `https://your-domain.com` | 文件上传域名 |
| downloadFile合法域名 | `https://your-domain.com` | 文件下载域名 |

**注意**：
- 域名必须是HTTPS
- 域名必须已ICP备案
- 不能配置IP地址或端口号
- 不能使用临时域名

#### 步骤2: 配置业务域名（可选）
如果小程序需要跳转到H5页面，需要配置业务域名。

### 2. 后端CORS配置

当前项目的CORS配置在 [main.py](../app/main.py:62-70)：

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议配置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)
```

**生产环境建议**：将 `allow_origins` 改为小程序的特定域名：

```python
allow_origins=[
    "https://your-domain.com",
    "https://servicewechat.com"  # 微信小程序服务域名
]
```

---

## API接口文档

### 基础信息

| 项目 | 说明 |
|------|------|
| 基础URL | `https://your-domain.com` |
| 数据格式 | JSON |
| 字符编码 | UTF-8 |
| 认证方式 | 当前无认证（建议添加） |

### 响应格式规范

#### 成功响应
```json
{
  "status": "success",
  "data": {
    // 响应数据
  }
}
```

#### 错误响应
```json
{
  "detail": "错误信息描述"
}
```

---

### 一、健康检查

#### 1.1 检查服务状态

```http
GET /health
```

**响应示例**：
```json
{
  "status": "healthy"
}
```

**小程序使用示例**：
```javascript
wx.request({
  url: 'https://your-domain.com/health',
  method: 'GET',
  success(res) {
    console.log('服务状态:', res.data.status);
  }
});
```

---

### 二、会话管理

#### 2.1 创建会话

```http
POST /api/chat/sessions
Content-Type: application/json

{
  "user_id": "string",           // 用户ID（必填）
  "session_name": "string",      // 会话名称（可选）
  "agent_type": "chat"           // 智能体类型：chat/rag/search
}
```

**响应示例**：
```json
{
  "status": "success",
  "session": {
    "session_id": "uuid-string",
    "user_id": "string",
    "session_name": "新对话",
    "agent_id": "string",
    "created_at": 1234567890
  }
}
```

**小程序示例**：
```javascript
wx.request({
  url: 'https://your-domain.com/api/chat/sessions',
  method: 'POST',
  data: {
    user_id: 'user123',
    session_name: '我的对话',
    agent_type: 'chat'
  },
  header: {
    'content-type': 'application/json'
  },
  success(res) {
    const sessionId = res.data.session.session_id;
    console.log('会话创建成功:', sessionId);
  }
});
```

#### 2.2 获取会话列表

```http
GET /api/chat/sessions?user_id={user_id}
```

**响应示例**：
```json
{
  "status": "success",
  "sessions": [
    {
      "session_id": "uuid",
      "session_name": "对话1",
      "created_at": 1234567890,
      "updated_at": 1234567890
    }
  ]
}
```

**小程序示例**：
```javascript
wx.request({
  url: 'https://your-domain.com/api/chat/sessions',
  method: 'GET',
  data: {
    user_id: 'user123'
  },
  success(res) {
    console.log('会话列表:', res.data.sessions);
    this.setData({
      sessions: res.data.sessions
    });
  }
});
```

#### 2.3 更新会话名称

```http
PUT /api/chat/sessions/{session_id}
Content-Type: application/json

{
  "user_id": "string",
  "session_name": "新的会话名称"
}
```

#### 2.4 删除会话

```http
DELETE /api/chat/sessions/{session_id}?user_id={user_id}
```

#### 2.5 获取消息历史

```http
GET /api/chat/sessions/{session_id}/messages?user_id={user_id}
```

**响应示例**：
```json
{
  "status": "success",
  "messages": [
    {
      "role": "user",
      "content": "你好"
    },
    {
      "role": "assistant",
      "content": "你好！有什么可以帮助你的？"
    }
  ]
}
```

---

### 三、AI对话

#### 3.1 普通对话（支持多模态）

```http
POST /api/chat/chat
Content-Type: application/json

{
  "session_id": "string",      // 会话ID（必填）
  "user_id": "string",         // 用户ID（必填）
  "message": "string",         // 用户消息（必填）
  "files": []                  // 文件列表（可选）
}
```

**响应示例**：
```json
{
  "status": "success",
  "response": "AI回复内容",
  "session_id": "uuid"
}
```

**小程序示例**：
```javascript
// 发送消息
wx.request({
  url: 'https://your-domain.com/api/chat/chat',
  method: 'POST',
  data: {
    session_id: this.data.sessionId,
    user_id: 'user123',
    message: '你好，请介绍一下你自己',
    files: []
  },
  header: {
    'content-type': 'application/json'
  },
  success(res) {
    console.log('AI回复:', res.data.response);
    this.setData({
      messages: [...this.data.messages, {
        role: 'user',
        content: '你好，请介绍一下你自己'
      }, {
        role: 'assistant',
        content: res.data.response
      }]
    });
  },
  fail(err) {
    wx.showToast({
      title: '请求失败',
      icon: 'error'
    });
  }
});
```

#### 3.2 搜索增强对话

```http
POST /api/chat/chat-with-search
Content-Type: application/json

{
  "session_id": "string",
  "user_id": "string",
  "message": "string"
}
```

**说明**：此接口会在对话前先进行在线搜索，获取最新信息后生成回复。

#### 3.3 RAG知识库对话

```http
POST /api/chat/rag
Content-Type: application/json

{
  "user_id": "string",
  "query": "string",           // 查询问题
  "knowledge_bases": ["kb1", "kb2"],  // 知识库名称列表
  "top_k": 5                   // 返回最相关的K个文档片段
}
```

**响应示例**：
```json
{
  "status": "success",
  "answer": "基于知识库的答案",
  "sources": [
    {
      "file_name": "doc1.pdf",
      "content": "相关文档片段...",
      "score": 0.95
    }
  ]
}
```

**小程序示例**：
```javascript
wx.request({
  url: 'https://your-domain.com/api/chat/rag',
  method: 'POST',
  data: {
    user_id: 'user123',
    query: '如何使用FastAPI？',
    knowledge_bases: ['tech_docs'],
    top_k: 5
  },
  success(res) {
    console.log('答案:', res.data.answer);
    console.log('来源:', res.data.sources);
  }
});
```

---

### 四、知识库管理

#### 4.1 创建知识库

```http
POST /api/knowledge-base/create
Content-Type: application/json

{
  "user_id": "string",
  "kb_name": "string",          // 知识库名称（唯一标识）
  "display_name": "string",     // 显示名称
  "description": "string"       // 描述（可选）
}
```

**小程序示例**：
```javascript
wx.request({
  url: 'https://your-domain.com/api/knowledge-base/create',
  method: 'POST',
  data: {
    user_id: 'user123',
    kb_name: 'my_knowledge_base',
    display_name: '我的知识库',
    description: '存储我的文档'
  },
  success(res) {
    wx.showToast({
      title: '创建成功',
      icon: 'success'
    });
  }
});
```

#### 4.2 获取知识库列表

```http
GET /api/knowledge-base/list?user_id={user_id}
```

**响应示例**：
```json
{
  "status": "success",
  "knowledge_bases": [
    {
      "kb_name": "kb1",
      "display_name": "知识库1",
      "description": "描述",
      "document_count": 10
    }
  ]
}
```

#### 4.3 上传文档

```http
POST /api/knowledge-base/upload
Content-Type: multipart/form-data

{
  "file": <binary>,             // 文件二进制数据
  "kb_name": "string",          // 目标知识库名称
  "user_id": "string"
}
```

**小程序示例（文件上传）**：
```javascript
// 选择文件
wx.chooseMessageFile({
  count: 1,
  type: 'file',
  success(res) {
    const filePath = res.tempFiles[0].path;

    // 上传文件
    wx.uploadFile({
      url: 'https://your-domain.com/api/knowledge-base/upload',
      filePath: filePath,
      name: 'file',
      formData: {
        kb_name: 'my_knowledge_base',
        user_id: 'user123'
      },
      success(uploadRes) {
        const data = JSON.parse(uploadRes.data);
        wx.showToast({
          title: '上传成功',
          icon: 'success'
        });
      },
      fail(err) {
        wx.showToast({
          title: '上传失败',
          icon: 'error'
        });
      }
    });
  }
});
```

#### 4.4 批量上传文档

```http
POST /api/knowledge-base/upload-batch
Content-Type: multipart/form-data

{
  "files": [<binary>, ...],     // 多个文件
  "kb_name": "string",
  "user_id": "string"
}
```

#### 4.5 搜索知识库

```http
POST /api/knowledge-base/search
Content-Type: application/json

{
  "user_id": "string",
  "kb_name": "string",
  "query": "搜索关键词",
  "top_k": 5
}
```

#### 4.6 获取知识库文档列表

```http
GET /api/knowledge-base/documents?user_id={user_id}&kb_name={kb_name}
```

#### 4.7 删除知识库

```http
DELETE /api/knowledge-base/{kb_name}?user_id={user_id}
```

---

### 五、文档生成

#### 5.1 创建文档会话

```http
POST /api/document/sessions
Content-Type: application/json

{
  "user_id": "string",
  "title": "文档标题"
}
```

#### 5.2 生成文档内容

```http
POST /api/document/generate
Content-Type: application/json

{
  "session_id": "string",
  "user_id": "string",
  "prompt": "生成文档的要求"
}
```

#### 5.3 导出文档

```http
POST /api/document/export
Content-Type: application/json

{
  "session_id": "string",
  "user_id": "string"
}
```

**响应示例**：
```json
{
  "status": "success",
  "download_url": "/api/document/download/document_20250109.docx"
}
```

#### 5.4 下载文档

```http
GET /api/document/download/{filename}
```

**小程序下载示例**：
```javascript
wx.downloadFile({
  url: 'https://your-domain.com/api/document/download/document_20250109.docx',
  success(res) {
    if (res.statusCode === 200) {
      // 临时文件路径
      const tempFilePath = res.tempFilePath;

      // 打开文档
      wx.openDocument({
        filePath: tempFilePath,
        success(openRes) {
          console.log('文档打开成功');
        }
      });
    }
  }
});
```

---

### 六、数据统计

#### 6.1 获取统计数据

```http
GET /api/dashboard/stats?user_id={user_id}
```

**响应示例**：
```json
{
  "status": "success",
  "stats": {
    "total_sessions": 10,
    "total_messages": 156,
    "total_tokens": 45678
  }
}
```

#### 6.2 获取Token使用趋势

```http
GET /api/dashboard/token-chart?user_id={user_id}&days=7
```

---

## 小程序端实现示例

### 完整的聊天页面示例

```javascript
// pages/chat/chat.js
Page({
  data: {
    sessionId: '',
    userId: 'user123',  // 应从登录状态获取
    messages: [],
    inputValue: '',
    loading: false
  },

  onLoad() {
    // 创建新会话或加载已有会话
    this.createSession();
  },

  // 创建会话
  createSession() {
    wx.request({
      url: 'https://your-domain.com/api/chat/sessions',
      method: 'POST',
      data: {
        user_id: this.data.userId,
        session_name: '新对话',
        agent_type: 'chat'
      },
      success: (res) => {
        this.setData({
          sessionId: res.data.session.session_id
        });
      }
    });
  },

  // 发送消息
  sendMessage() {
    const message = this.data.inputValue.trim();
    if (!message) return;

    // 添加用户消息到界面
    const messages = [...this.data.messages, {
      role: 'user',
      content: message
    }];
    this.setData({
      messages,
      inputValue: '',
      loading: true
    });

    // 发送到后端
    wx.request({
      url: 'https://your-domain.com/api/chat/chat',
      method: 'POST',
      data: {
        session_id: this.data.sessionId,
        user_id: this.data.userId,
        message: message,
        files: []
      },
      success: (res) => {
        this.setData({
          messages: [...this.data.messages, {
            role: 'assistant',
            content: res.data.response
          }],
          loading: false
        });
      },
      fail: (err) => {
        wx.showToast({
          title: '发送失败',
          icon: 'error'
        });
        this.setData({ loading: false });
      }
    });
  },

  // 输入框变化
  onInput(e) {
    this.setData({
      inputValue: e.detail.value
    });
  }
});
```

### 对应的WXML

```xml
<!-- pages/chat/chat.wxml -->
<view class="chat-container">
  <!-- 消息列表 -->
  <scroll-view scroll-y class="message-list">
    <block wx:for="{{messages}}" wx:key="index">
      <view class="message {{item.role}}">
        <text>{{item.content}}</text>
      </view>
    </block>
  </scroll-view>

  <!-- 输入框 -->
  <view class="input-bar">
    <input
      value="{{inputValue}}"
      bindinput="onInput"
      placeholder="输入消息..."
      disabled="{{loading}}"
    />
    <button
      bindtap="sendMessage"
      disabled="{{loading}}"
      size="mini"
    >
      {{loading ? '发送中...' : '发送'}}
    </button>
  </view>
</view>
```

### API封装工具类

```javascript
// utils/api.js

const BASE_URL = 'https://your-domain.com';

class API {
  constructor() {
    this.baseUrl = BASE_URL;
    this.userId = wx.getStorageSync('userId') || 'user123';
  }

  // 通用请求方法
  request(options) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: this.baseUrl + options.url,
        method: options.method || 'GET',
        data: options.data || {},
        header: {
          'content-type': 'application/json',
          ...options.header
        },
        success: (res) => {
          if (res.statusCode === 200) {
            resolve(res.data);
          } else {
            reject(res);
          }
        },
        fail: reject
      });
    });
  }

  // 创建会话
  createSession(data) {
    return this.request({
      url: '/api/chat/sessions',
      method: 'POST',
      data: {
        user_id: this.userId,
        ...data
      }
    });
  }

  // 发送消息
  sendMessage(data) {
    return this.request({
      url: '/api/chat/chat',
      method: 'POST',
      data: {
        user_id: this.userId,
        ...data
      }
    });
  }

  // 获取会话列表
  getSessions() {
    return this.request({
      url: '/api/chat/sessions',
      data: { user_id: this.userId }
    });
  }

  // 获取消息历史
  getMessages(sessionId) {
    return this.request({
      url: `/api/chat/sessions/${sessionId}/messages`,
      data: { user_id: this.userId }
    });
  }

  // 获取知识库列表
  getKnowledgeBases() {
    return this.request({
      url: '/api/knowledge-base/list',
      data: { user_id: this.userId }
    });
  }

  // 上传文件
  uploadFile(filePath, formData) {
    return new Promise((resolve, reject) => {
      wx.uploadFile({
        url: this.baseUrl + '/api/knowledge-base/upload',
        filePath: filePath,
        name: 'file',
        formData: {
          user_id: this.userId,
          ...formData
        },
        success: (res) => {
          resolve(JSON.parse(res.data));
        },
        fail: reject
      });
    });
  }

  // RAG查询
  ragQuery(data) {
    return this.request({
      url: '/api/chat/rag',
      method: 'POST',
      data: {
        user_id: this.userId,
        ...data
      }
    });
  }
}

module.exports = new API();
```

---

## 最佳实践

### 1. 用户认证

**当前问题**：项目目前没有用户认证机制，任何人都可以伪造`user_id`访问其他用户数据。

**建议实现方案**：

#### 方案A: 微信登录（推荐）

```javascript
// 小程序端
wx.login({
  success(res) {
    if (res.code) {
      // 发送code到后端换取session
      wx.request({
        url: 'https://your-domain.com/api/auth/wechat-login',
        method: 'POST',
        data: { code: res.code },
        success(loginRes) {
          // 保存token
          wx.setStorageSync('token', loginRes.data.token);
          wx.setStorageSync('userId', loginRes.data.user_id);
        }
      });
    }
  }
});
```

后端需要添加微信登录接口（需先实现）：

```python
# app/api/auth.py
@router.post("/wechat-login")
async def wechat_login(code: str):
    # 1. 使用code换取openid和session_key
    # 2. 生成JWT token
    # 3. 返回token和user_id
    pass
```

#### 方案B: 匿名用户 + 设备ID

如果不需要用户登录，可以使用设备唯一标识：

```javascript
// 获取设备唯一ID
let userId = wx.getStorageSync('userId');
if (!userId) {
  userId = 'anon_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  wx.setStorageSync('userId', userId);
}
```

### 2. 请求优化

#### 并发控制
微信小程序最多10个并发请求，建议使用请求队列：

```javascript
// utils/requestQueue.js
class RequestQueue {
  constructor(maxConcurrent = 5) {
    this.queue = [];
    this.running = 0;
    this.maxConcurrent = maxConcurrent;
  }

  add(requestFn) {
    return new Promise((resolve, reject) => {
      this.queue.push({
        requestFn,
        resolve,
        reject
      });
      this.runNext();
    });
  }

  runNext() {
    if (this.running >= this.maxConcurrent || this.queue.length === 0) {
      return;
    }

    this.running++;
    const { requestFn, resolve, reject } = this.queue.shift();

    requestFn()
      .then(resolve)
      .catch(reject)
      .finally(() => {
        this.running--;
        this.runNext();
      });
  }
}

module.exports = new RequestQueue();
```

#### 数据缓存
对不常变化的数据进行缓存：

```javascript
// 带缓存的请求
getCachedData(key, apiFn, expireSeconds = 300) {
  const cached = wx.getStorageSync(key);
  const now = Date.now();

  if (cached && cached.timestamp && (now - cached.timestamp < expireSeconds * 1000)) {
    return Promise.resolve(cached.data);
  }

  return apiFn().then(data => {
    wx.setStorageSync(key, {
      data,
      timestamp: now
    });
    return data;
  });
}
```

### 3. 错误处理

```javascript
// 统一错误处理
function handleError(err) {
  console.error('API Error:', err);

  let message = '请求失败';

  if (err.statusCode) {
    switch(err.statusCode) {
      case 400:
        message = '请求参数错误';
        break;
      case 404:
        message = '资源不存在';
        break;
      case 500:
        message = '服务器错误';
        break;
    }
  }

  wx.showToast({
    title: message,
    icon: 'none'
  });
}
```

### 4. 流式响应处理

**注意**：微信小程序原生不支持Server-Sent Events (SSE)流式响应。

**解决方案**：

#### 方案A: 使用WebSocket
后端需要添加WebSocket支持（当前项目未实现）。

#### 方案B: 分段请求
将长对话拆分为多个短请求：

```javascript
async function streamChat(messages) {
  const responses = [];

  for (const msg of messages) {
    const response = await api.sendMessage({
      message: msg,
      stream: false  // 不使用流式
    });
    responses.push(response);
  }

  return responses;
}
```

#### 方案C: 使用轮询
对于需要长时间处理的任务：

```javascript
function pollResult(taskId, maxAttempts = 30) {
  let attempts = 0;

  return new Promise((resolve, reject) => {
    const poll = () => {
      wx.request({
        url: `/api/tasks/${taskId}`,
        success: (res) => {
          if (res.data.status === 'completed') {
            resolve(res.data.result);
          } else if (attempts < maxAttempts) {
            attempts++;
            setTimeout(poll, 1000);
          } else {
            reject(new Error('请求超时'));
          }
        }
      });
    };

    poll();
  });
}
```

---

## 常见问题

### Q1: 提示"不在以下 request 合法域名列表中"

**原因**：域名未在微信公众平台配置

**解决**：
1. 登录微信公众平台
2. 进入「开发 -> 开发设置 -> 服务器域名」
3. 添加域名到request合法域名列表
4. 确保使用HTTPS

### Q2: 开发时如何绕过域名验证？

**解决**：在微信开发者工具中：
1. 点击右上角「详情」
2. 勾选「不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书」

**注意**：此选项仅用于开发，正式版无法使用。

### Q3: 文件上传失败

**检查项**：
1. 确认已配置uploadFile合法域名
2. 检查文件大小（小程序限制10MB）
3. 确认后端支持multipart/form-data
4. 检查文件类型是否被允许

### Q4: 如何处理用户身份持久化？

**推荐方案**：
```javascript
// 用户首次打开时生成唯一ID
function initUser() {
  let userId = wx.getStorageSync('userId');

  if (!userId) {
    // 生成新的用户ID
    userId = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    wx.setStorageSync('userId', userId);

    // 同步到服务器（如果需要）
    syncUserToServer(userId);
  }

  return userId;
}
```

### Q5: 如何实现消息推送？

小程序支持以下推送方式：
1. **模板消息**：需要用户主动订阅
2. **订阅消息**：一次性订阅，用户每次触发需重新授权
3. **WebSocket**：实时双向通信

### Q6: Token存储安全

```javascript
// 敏感数据加密存储
import { encryptData, decryptData } from './crypto';

function setSecureToken(key, value) {
  const encrypted = encryptData(value);
  wx.setStorageSync(key, encrypted);
}

function getSecureToken(key) {
  const encrypted = wx.getStorageSync(key);
  return encrypted ? decryptData(encrypted) : null;
}
```

### Q7: 如何监控API调用情况？

建议接入：
- **微信小程序后台**：查看访问数据分析
- **自定义监控**：记录API调用日志
- **第三方工具**：如神策、友盟等

---

## 后续开发建议

### 必须实现的功能

1. **用户认证系统**
   - 微信登录
   - JWT Token管理
   - Token刷新机制

2. **API安全加固**
   - 添加请求签名验证
   - 实现速率限制
   - 敏感数据加密

3. **错误处理优化**
   - 统一错误码
   - 友好的错误提示
   - 错误日志记录

### 建议添加的功能

1. **WebSocket支持**
   - 实现实时对话
   - 支持流式响应

2. **离线能力**
   - 本地消息存储
   - 离线消息同步

3. **数据分析**
   - 用户行为统计
   - API使用监控

---

## 参考资料

- [微信小程序官方文档](https://developers.weixin.qq.com/miniprogram/dev/framework/)
- [wx.request API](https://developers.weixin.qq.com/miniprogram/dev/api/network/request/wx.request.html)
- [wx.uploadFile API](https://developers.weixin.qq.com/miniprogram/dev/api/network/upload/wx.uploadFile.html)
- [服务器域名配置](https://developers.weixin.qq.com/miniprogram/dev/framework/server-ability/domain.html)

---

## 更新日志

| 日期 | 版本 | 说明 |
|------|------|------|
| 2025-01-09 | 1.0.0 | 初始版本 |

---

**文档维护**：如API有更新，请及时更新本文档。
