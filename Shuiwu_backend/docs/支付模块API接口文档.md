# 税小通 - 支付模块 API 接口文档

## 目录

- [概述](#概述)
- [认证说明](#认证说明)
- [通用响应格式](#通用响应格式)
- [支付流程](#支付流程)
- [接口列表](#接口列表)
  - [1. 获取会员套餐列表](#1-获取会员套餐列表)
  - [2. 创建订单](#2-创建订单)
  - [3. 发起JSAPI支付](#3-发起jsapi支付)
  - [4. 查询支付状态](#4-查询支付状态)
  - [5. 关闭订单](#5-关闭订单)
  - [6. 申请退款](#6-申请退款)
  - [7. 获取订单详情](#7-获取订单详情)
  - [8. 获取订单列表](#8-获取订单列表)
  - [9. 取消订单](#9-取消订单)
  - [10. 测试支付模拟](#10-测试支付模拟)
- [错误码说明](#错误码说明)
- [附录](#附录)

---

## 概述

本文档描述税小通系统的支付模块相关接口，支持微信小程序JSAPI支付。

**基础信息**

| 项目 | 说明 |
|------|------|
| API版本 | v1.0 |
| Base URL | `http://127.0.0.1:8000` (开发环境) |
| Content-Type | `application/json` |
| 字符编码 | UTF-8 |

**支付方式**

| 支付方式 | 标识 | 状态 |
|----------|------|------|
| 微信支付 | `wechat` | 已实现 |
| 支付宝 | `alipay` | 待实现 |

---

## 认证说明

除了支付回调接口外，所有接口都需要在请求头中提供有效的 Bearer Token：

```http
Authorization: Bearer {access_token}
```

Token 通过用户登录接口获取，详见 [认证模块文档](./认证模块API接口文档.md)。

---

## 通用响应格式

所有接口遵循统一的响应格式：

**成功响应**

```json
{
  "code": 1,
  "message": "操作成功",
  "data": { ... }
}
```

**失败响应**

```json
{
  "code": 0,
  "message": "错误描述",
  "data": null
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| code | integer | 状态码：1-成功，0-失败 |
| message | string | 响应消息 |
| data | object\|null | 响应数据 |

---

## 支付流程

### 完整支付流程图

```
┌─────────┐      ┌─────────┐      ┌─────────┐      ┌─────────┐
│  用户   │      │  前端   │      │  后端   │      │  微信   │
└────┬────┘      └────┬────┘      └────┬────┘      └────┬────┘
     │                │                │                │
     │  1.选择套餐    │                │                │
     ├───────────────>│                │                │
     │                │                │                │
     │                │  2.创建订单    │                │
     │                ├───────────────>│                │
     │                │                │                │
     │                │  3.返回订单信息 │                │
     │                │<───────────────┤                │
     │                │                │                │
     │  4.确认支付    │                │                │
     ├───────────────>│                │                │
     │                │                │                │
     │                │  5.发起支付    │                │
     │                ├───────────────>│                │
     │                │                │                │
     │                │                │  6.调用微信API │
     │                │                ├───────────────>│
     │                │                │                │
     │                │                │  7.返回支付参数│
     │                │                │<───────────────┤
     │                │                │                │
     │                │  8.返回支付参数 │                │
     │                │<───────────────┤                │
     │                │                │                │
     │  9.调起支付    │                │                │
     ├───────────────>│                │                │
     │                │  (wx.requestPayment)            │
     │                │                │                │
     │  10.完成支付   │                │                │
     │<───────────────┤                │                │
     │                │                │                │
     │                │                │  11.支付回调   │
     │                │                │<───────────────┤
     │                │                │                │
     │                │                │  12.激活会员   │
     │                │                │    (处理)      │
     │                │                │                │
     │  13.查询结果   │                │                │
     ├───────────────>│                │                │
     │                │  14.查询状态   │                │
     │                ├───────────────>│                │
     │                │                │                │
     │                │  15.返回最终状态│                │
     │                │<───────────────┤                │
     │                │                │                │
     │  16.显示结果   │                │                │
     ├───────────────>│                │                │
     │                │                │                │
```

### 前端集成要点

1. **获取用户OpenID**：在小程序登录时获取用户的微信OpenID
2. **创建订单**：用户选择套餐后，先调用创建订单接口
3. **发起支付**：使用订单ID和OpenID调用支付接口
4. **调起支付**：使用返回的支付参数调用`wx.requestPayment()`
5. **轮询查询**：支付完成后轮询查询订单状态，或等待回调

---

## 接口列表

### 1. 获取会员套餐列表

获取所有有效的会员套餐列表，用于展示给用户选择。

**接口地址**

```
GET /api/member/packages
```

**请求参数（Query）**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 否 | 套餐状态筛选：active-启用，inactive-停用 |
| package_type | string | 否 | 套餐类型：free, basic, premium, enterprise |

**请求示例**

```http
GET /api/member/packages?status=active
```

**响应示例**

```json
{
  "code": 1,
  "message": "操作成功",
  "data": {
    "packages": [
      {
        "package_id": "vip_month",
        "name": "月度会员",
        "description": "享受月度会员权益",
        "package_type": "month",
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
        "custom_config": {},
        "benefits": [
          {"title": "每日100次对话", "desc": "每天可使用100次AI智能对话"},
          {"title": "10个知识库", "desc": "支持创建10个知识库进行分类管理"},
          {"title": "RAG功能", "desc": "知识库检索增强生成，答案更精准"},
          {"title": "网络搜索", "desc": "实时联网搜索，获取最新信息"}
        ],
        "status": "active",
        "sort_order": 1,
        "created_at": "2024-01-15T10:00:00"
      }
    ]
  }
}
```

---

### 2. 创建订单

用户购买会员套餐时，先创建订单，然后使用订单ID发起支付。

**接口地址**

```
POST /api/member/orders
```

**请求头**

```http
Authorization: Bearer {access_token}
Content-Type: application/json
```

**请求参数（Body）**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| package_id | string | 是 | 套餐ID |
| payment_method | string | 否 | 支付方式，默认wechat |
| order_type | string | 否 | 订单类型，默认subscription |

**请求示例**

```json
{
  "package_id": "vip_month",
  "payment_method": "wechat"
}
```

**响应示例**

```json
{
  "code": 1,
  "message": "创建订单成功",
  "data": {
    "order_id": "ord_202401151234567890",
    "user_id": "user_1234567890abcdef",
    "package_id": "vip_month",
    "package_name": "月度会员",
    "order_type": "subscription",
    "amount": 29.9,
    "payment_method": "wechat",
    "payment_status": "unpaid",
    "status": "pending",
    "created_at": "2024-01-15T12:00:00",
    "expires_at": "2024-01-15T12:30:00"
  }
}
```

**订单状态说明**

| 状态 | 说明 |
|------|------|
| pending | 待支付 |
| paid | 已支付 |
| failed | 支付失败 |
| cancelled | 已取消 |
| refunded | 已退款 |

**支付状态说明**

| 状态 | 说明 |
|------|------|
| unpaid | 未支付 |
| paid | 已支付 |
| refunded | 已退款 |
| refunding | 退款中 |

---

### 3. 发起JSAPI支付

使用订单ID和用户OpenID发起微信小程序支付。

**接口地址**

```
POST /api/payments/jsapi
```

**请求头**

```http
Authorization: Bearer {access_token}
Content-Type: application/json
```

**请求参数（Body）**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| order_id | string | 是 | 订单ID |
| openid | string | 是 | 微信用户OpenID |

**请求示例**

```json
{
  "order_id": "ord_202401151234567890",
  "openid": "oXYZ1234567890abcdef"
}
```

**响应示例**

```json
{
  "code": 1,
  "message": "创建支付成功",
  "data": {
    "prepay_id": "wx1234567890abcdef12345678901234",
    "pay_params": {
      "appId": "wx1234567890abcdef",
      "timeStamp": "1642234567",
      "nonceStr": "5K8264ILTKCH16CQ2502SI8ZNMTM67VS",
      "package": "prepay_id=wx1234567890abcdef12345678901234",
      "signType": "RSA",
      "paySign": "A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q7R8S9T0U1V2W3X4Y5Z6a7b8c9d0e1f2"
    }
  }
}
```

**前端调用示例**

```javascript
// 调用小程序支付API
wx.requestPayment({
  appId: res.data.pay_params.appId,
  timeStamp: res.data.pay_params.timeStamp,
  nonceStr: res.data.pay_params.nonceStr,
  package: res.data.pay_params.package,
  signType: res.data.pay_params.signType,
  paySign: res.data.pay_params.paySign,
  success(res) {
    console.log('支付成功', res)
    // 查询订单状态
    queryOrderStatus(orderId)
  },
  fail(res) {
    console.log('支付失败或取消', res)
  }
})
```

---

### 4. 查询支付状态

主动查询订单的支付状态，用于确认支付结果。

**接口地址**

```
GET /api/payments/{order_id}/status
```

**请求头**

```http
Authorization: Bearer {access_token}
```

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| order_id | string | 是 | 订单ID |

**请求示例**

```http
GET /api/payments/ord_202401151234567890/status
```

**响应示例**

```json
{
  "code": 1,
  "message": "操作成功",
  "data": {
    "order_id": "ord_202401151234567890",
    "trade_state": "SUCCESS",
    "transaction_id": "4200001234567890123456789"
  }
}
```

**交易状态说明**

| 状态 | 说明 |
|------|------|
| SUCCESS | 支付成功 |
| REFUND | 转入退款 |
| NOTPAY | 未支付 |
| CLOSED | 已关闭 |
| REVOKED | 已撤销 |
| USERPAYING | 用户支付中 |
| PAYERROR | 支付失败 |

---

### 5. 关闭订单

关闭未支付的订单，用户主动取消或订单超时时使用。

**接口地址**

```
POST /api/payments/orders/{order_id}/close
```

**请求头**

```http
Authorization: Bearer {access_token}
```

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| order_id | string | 是 | 订单ID |

**请求示例**

```http
POST /api/payments/orders/ord_202401151234567890/close
```

**响应示例**

```json
{
  "code": 1,
  "message": "订单已关闭",
  "data": null
}
```

**注意事项**

- 只能关闭未支付的订单
- 关闭后订单不能再支付
- 建议在订单超时后自动调用此接口

---

### 6. 申请退款

对已支付的订单申请退款。

**接口地址**

```
POST /api/payments/refunds
```

**请求头**

```http
Authorization: Bearer {access_token}
Content-Type: application/json
```

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| order_id | string | 是 | 订单ID（路径参数） |
| reason | string | 否 | 退款原因（Query参数） |

**请求示例**

```http
POST /api/payments/refunds?order_id=ord_202401151234567890&reason=用户申请退款
```

**响应示例**

```json
{
  "code": 1,
  "message": "退款申请成功",
  "data": {
    "refund_id": "RF1234567890ABCDEF",
    "status": "PROCESSING"
  }
}
```

**注意事项**

- 只能对已支付的订单申请退款
- 退款金额按订单全额退款
- 退款需要时间处理，结果通过回调通知
- 退款成功后，会员权益不会自动扣除，需管理员手动处理

---

### 7. 获取订单详情

根据订单ID获取订单详细信息。

**接口地址**

```
GET /api/member/orders/{order_id}
```

**请求头**

```http
Authorization: Bearer {access_token}
```

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| order_id | string | 是 | 订单ID |

**请求示例**

```http
GET /api/member/orders/ord_202401151234567890
```

**响应示例**

```json
{
  "code": 1,
  "message": "操作成功",
  "data": {
    "order_id": "ord_202401151234567890",
    "user_id": "user_1234567890abcdef",
    "package_id": "vip_month",
    "package_name": "月度会员",
    "order_type": "subscription",
    "amount": 29.9,
    "actual_amount": 29.9,
    "payment_method": "wechat",
    "payment_status": "paid",
    "payment_time": "2024-01-15T12:05:00",
    "transaction_id": "4200001234567890123456789",
    "duration_days": 30,
    "original_expire_at": "2024-01-01T00:00:00",
    "new_expire_at": "2024-02-15T00:00:00",
    "status": "paid",
    "created_at": "2024-01-15T12:00:00",
    "updated_at": "2024-01-15T12:05:00"
  }
}
```

---

### 8. 获取订单列表

获取当前用户的订单列表，支持分页和筛选。

**接口地址**

```
GET /api/member/orders
```

**请求头**

```http
Authorization: Bearer {access_token}
```

**请求参数（Query）**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| payment_status | string | 否 | 支付状态筛选 |
| status | string | 否 | 订单状态筛选 |
| start_date | string | 否 | 起始日期 |
| end_date | string | 否 | 结束日期 |
| page | integer | 否 | 页码，默认1 |
| page_size | integer | 否 | 每页数量，默认20 |

**请求示例**

```http
GET /api/member/orders?payment_status=paid&page=1&page_size=20
```

**响应示例**

```json
{
  "code": 1,
  "message": "操作成功",
  "data": {
    "total": 50,
    "page": 1,
    "page_size": 20,
    "orders": [
      {
        "order_id": "ord_202401151234567890",
        "package_name": "月度会员",
        "amount": 29.9,
        "payment_status": "paid",
        "status": "paid",
        "payment_time": "2024-01-15T12:05:00",
        "created_at": "2024-01-15T12:00:00"
      }
    ]
  }
}
```

---

### 9. 取消订单

取消未支付的订单。

**接口地址**

```
POST /api/member/orders/{order_id}/cancel
```

**请求头**

```http
Authorization: Bearer {access_token}
```

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| order_id | string | 是 | 订单ID |

**请求示例**

```http
POST /api/member/orders/ord_202401151234567890/cancel
```

**响应示例**

```json
{
  "code": 1,
  "message": "订单已取消",
  "data": null
}
```

---

### 10. 测试支付模拟

**仅测试环境可用**，模拟支付结果用于前端开发测试。

**接口地址**

```
POST /api/payments/test/simulate
```

**请求头**

```http
Authorization: Bearer {access_token}
```

**请求参数（Query）**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| order_id | string | 是 | 订单ID |
| success | boolean | 是 | true=模拟支付成功，false=模拟支付失败 |

**请求示例**

```http
POST /api/payments/test/simulate?order_id=ord_202401151234567890&success=true
```

**成功响应示例**

```json
{
  "code": 1,
  "message": "测试支付成功，会员已激活",
  "data": {
    "order_id": "ord_202401151234567890",
    "new_expire_at": "2026-02-22T12:34:56",
    "transaction_id": "TEST_1737536096"
  }
}
```

**失败响应示例**

```json
{
  "code": 0,
  "message": "测试模式未启用，请设置环境变量 PAYMENT_TEST_MODE=true",
  "data": null
}
```

**注意事项**

- 此接口仅在 `PAYMENT_TEST_MODE=true` 时可用
- 生产环境必须禁用此接口
- 用于前端开发测试，无需接入真实微信支付

---

## 错误码说明

### HTTP状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 401 | 未授权（Token无效或过期） |
| 403 | 禁止访问（权限不足） |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

### 业务错误码

| 错误信息 | 场景 | 解决方案 |
|----------|------|----------|
| 订单不存在 | 查询/操作的订单不存在 | 检查订单ID是否正确 |
| 订单已支付 | 对已支付订单再次操作 | 检查订单状态 |
| 订单已关闭 | 对已关闭订单操作 | 检查订单状态 |
| 套餐不存在 | 选择套餐不存在 | 检查套餐ID是否正确 |
| 套餐已停用 | 选择套餐已停用 | 选择其他套餐 |
| 未提供认证token | 请求未携带Token | 添加Authorization头 |
| Token无效或过期 | Token验证失败 | 重新登录获取Token |
| 余额不足 | 余额支付时余额不足 | 充值或选择其他支付方式 |
| 签名验证失败 | 支付回调签名错误 | 检查微信支付配置 |
| 创建支付失败 | 调用微信支付API失败 | 检查网络和配置 |

---

## 附录

### A. 前端完整支付流程示例代码

```javascript
// 1. 选择套餐，创建订单
async function createOrder(packageId) {
  const res = await wx.request({
    url: 'http://127.0.0.1:8000/api/member/orders',
    method: 'POST',
    header: {
      'Authorization': `Bearer ${wx.getStorageSync('token')}`
    },
    data: {
      package_id: packageId,
      payment_method: 'wechat'
    }
  })
  return res.data.data.order_id
}

// 2. 发起支付
async function startPayment(orderId, openid) {
  const res = await wx.request({
    url: 'http://127.0.0.1:8000/api/payments/jsapi',
    method: 'POST',
    header: {
      'Authorization': `Bearer ${wx.getStorageSync('token')}`
    },
    data: {
      order_id: orderId,
      openid: openid
    }
  })

  if (res.data.code === 1) {
    // 调起小程序支付
    return new Promise((resolve, reject) => {
      wx.requestPayment({
        ...res.data.data.pay_params,
        success: () => resolve(true),
        fail: (err) => reject(err)
      })
    })
  }
  throw new Error(res.data.message)
}

// 3. 轮询查询订单状态
async function checkOrderStatus(orderId, maxAttempts = 10) {
  for (let i = 0; i < maxAttempts; i++) {
    const res = await wx.request({
      url: `http://127.0.0.1:8000/api/payments/${orderId}/status`,
      method: 'GET',
      header: {
        'Authorization': `Bearer ${wx.getStorageSync('token')}`
      }
    })

    const status = res.data.data.trade_state
    if (status === 'SUCCESS') {
      return true
    } else if (status === 'CLOSED' || status === 'PAYERROR') {
      return false
    }

    // 等待2秒后重试
    await new Promise(resolve => setTimeout(resolve, 2000))
  }
  return false
}

// 4. 完整支付流程
async function payForPackage(packageId, openid) {
  try {
    // 创建订单
    const orderId = await createOrder(packageId)

    // 发起支付
    await startPayment(orderId, openid)

    // 查询支付结果
    const success = await checkOrderStatus(orderId)

    if (success) {
      wx.showToast({ title: '支付成功' })
      // 刷新会员信息
      getMemberInfo()
    } else {
      wx.showToast({ title: '支付失败', icon: 'error' })
    }
  } catch (err) {
    wx.showToast({ title: err.message, icon: 'error' })
  }
}
```

### B. 订单超时处理建议

```javascript
// 订单超时时间（30分钟）
const ORDER_TIMEOUT = 30 * 60 * 1000

// 检查订单是否超时
function isOrderExpired(expiresAt) {
  return new Date(expiresAt) < new Date()
}

// 自动关闭超时订单
async function handleExpiredOrder(orderId) {
  await wx.request({
    url: `http://127.0.0.1:8000/api/payments/orders/${orderId}/close`,
    method: 'POST',
    header: {
      'Authorization': `Bearer ${wx.getStorageSync('token')}`
    }
  })
  wx.showToast({ title: '订单已超时', icon: 'error' })
}
```

### C. 微信支付回调通知（后端接口）

**接口地址**

```
POST /api/payments/notify
```

**说明**

- 此接口由微信服务器调用，无需认证
- 系统会自动验证签名和处理回调
- 前端无需关心此接口

### D. 测试环境配置

在 `.env` 文件中配置测试模式：

```env
# 启用测试支付模式（仅开发环境）
PAYMENT_TEST_MODE=true
```

**注意：生产环境务必设置为 `false` 或删除此配置！**

---

## 更新记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2026-02-12 | 初始版本，包含完整的支付流程接口 |

---

## 联系支持

如有疑问或问题，请联系后端开发团队。
