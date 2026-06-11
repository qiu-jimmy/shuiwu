# 管理员 API 接口文档

## 基础信息

- **Base URL**: `http://127.0.0.1:8000`
- **认证方式**: Bearer Token (JWT)
- **请求头**: `Authorization: Bearer <access_token>`
- **响应格式**: JSON

---

## 目录

1. [订单管理](#1-订单管理)
2. [工商申报管理](#2-工商申报管理)
3. [智能报税管理](#3-智能报税管理)
4. [分销商管理](#4-分销商管理)
5. [分销提现管理](#5-分销提现管理)
6. [状态码说明](#6-状态码说明)

---

## 1. 订单管理

### 1.1 获取订单列表

**接口**: `GET /api/admin/orders`

**认证要求**: 管理员权限

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| keyword | string | 否 | 搜索关键词（订单号、用户ID） |
| payment_status | string | 否 | 支付状态 (unpaid/paid/refunded) |
| status | string | 否 | 订单状态 (pending/completed/cancelled/failed) |
| start_date | string | 否 | 开始日期 (YYYY-MM-DD) |
| end_date | string | 否 | 结束日期 (YYYY-MM-DD) |
| page | int | 否 | 页码（默认1） |
| page_size | int | 否 | 每页数量（默认20，最大100） |

**响应示例**:
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
        "order_id": 1,
        "order_no": "ORD2026012000001",
        "user_id": "user_123456",
        "package_name": "高级会员套餐",
        "amount": 299.00,
        "payment_status": "paid",
        "status": "completed",
        "created_at": "2026-01-20T10:00:00"
      }
    ]
  }
}
```

### 1.2 获取订单详情

**接口**: `GET /api/admin/orders/{order_id}`

**认证要求**: 管理员权限

**路径参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| order_id | int | 是 | 订单ID |

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 订单ID |
| order_no | string | 订单号 |
| user_id | string | 用户ID |
| username | string | 用户昵称 |
| phone | string | 手机号 |
| package_id | string | 套餐ID |
| package_name | string | 套餐名称 |
| duration_days | int | 有效期天数 |
| amount | float | 订单金额 |
| actual_amount | float | 实付金额 |
| payment_method | string | 支付方式 |
| payment_status | string | 支付状态 |
| payment_time | datetime | 支付时间 |
| transaction_id | string | 交易流水号 |
| status | string | 订单状态 |
| order_type | string | 订单类型 |
| original_expire_at | datetime | 原到期时间 |
| new_expire_at | datetime | 新到期时间 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

**响应示例**:
```json
{
  "code": 1,
  "message": "操作成功",
  "data": {
    "order": {
      "id": 1,
      "order_no": "ORD2026012000001",
      "user_id": "user_123456",
      "username": "张三",
      "phone": "13800138000",
      "package_id": "premium",
      "package_name": "高级会员套餐",
      "duration_days": 365,
      "amount": 299.00,
      "actual_amount": 299.00,
      "payment_method": "wechat",
      "payment_status": "paid",
      "payment_time": "2026-01-20T10:30:00",
      "transaction_id": "TX123456789",
      "status": "completed",
      "order_type": "membership",
      "original_expire_at": null,
      "new_expire_at": "2027-01-20T10:30:00",
      "created_at": "2026-01-20T10:00:00",
      "updated_at": "2026-01-20T10:30:00"
    }
  }
}
```

### 1.3 订单状态说明

| 支付状态 | 说明 |
|---------|------|
| unpaid | 未支付 |
| paid | 已支付 |
| refunded | 已退款 |

| 订单状态 | 说明 |
|---------|------|
| pending | 待处理 |
| completed | 已完成 |
| cancelled | 已取消 |
| failed | 失败 |

---

## 2. 工商申报管理

### 2.1 获取工商申报列表

**接口**: `GET /api/business-declaration/admin/list`

**认证要求**: 管理员权限

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | string | 否 | 用户ID筛选 |
| status | string | 否 | 状态筛选 |
| declaration_type | string | 否 | 申报类型筛选：annual_report/change_registration/deregistration/tax_registration/invoice_application/license_application |
| page | int | 否 | 页码（默认1） |
| page_size | int | 否 | 每页数量（默认20，范围1-100） |

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 申报ID |
| declaration_no | string | 申报单号 |
| user_id | string | 用户ID |
| business_name | string | 个体户名称 |
| operator_name | string | 经营者姓名 |
| operator_phone | string | 经营者电话 |
| declaration_type | string | 申报类型 |
| status | string | 状态 |
| created_at | datetime | 创建时间 |
| processed_at | datetime | 处理时间 |

**响应示例**:
```json
{
  "code": 1,
  "message": "操作成功",
  "data": {
    "total": 10,
    "page": 1,
    "page_size": 20,
    "declarations": [
      {
        "id": 1,
        "declaration_no": "BD2026012000001",
        "user_id": "user_123456",
        "business_name": "张三小吃店",
        "operator_name": "张三",
        "operator_phone": "138****8000",
        "declaration_type": "annual_report",
        "status": "pending",
        "created_at": "2026-01-20T10:00:00",
        "processed_at": null
      }
    ]
  }
}
```

### 2.2 获取工商申报详情

**接口**: `GET /api/business-declaration/{declaration_id}`

**认证要求**: 管理员权限

**路径参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| declaration_id | int | 是 | 申报ID |

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 申报ID |
| declaration_no | string | 申报单号 |
| user_id | string | 用户ID |
| business_name | string | 个体户名称 |
| business_license_no | string | 营业执照号 |
| business_address | string | 经营地址 |
| business_type | string | 经营类型 |
| business_scope | string | 经营范围 |
| operator_name | string | 经营者姓名 |
| operator_id_card | string | 经营者身份证 |
| operator_phone | string | 经营者电话 |
| declaration_type | string | 申报类型 |
| declaration_info | object | 申报信息(JSON) |
| attachments | string | 附件URL |
| status | string | 状态 |
| approval_no | string | 受理号 |
| approval_date | date | 受理日期 |
| approval_proof_url | string | 批准凭证URL |
| process_result | string | 处理结果 |
| process_notes | string | 处理备注 |
| processed_by | string | 处理人ID |
| processed_at | datetime | 处理时间 |
| user_remarks | string | 用户备注 |
| created_at | datetime | 创建时间 |

**响应示例**:
```json
{
  "code": 1,
  "message": "操作成功",
  "data": {
    "declaration": {
      "id": 1,
      "declaration_no": "BD2026012000001",
      "user_id": "user_123456",
      "business_name": "张三小吃店",
      "business_license_no": "92110108MA1234567X",
      "business_address": "北京市朝阳区某某街道123号",
      "business_type": "餐饮服务",
      "business_scope": "小吃制售",
      "operator_name": "张三",
      "operator_id_card": "110101199001011234",
      "operator_phone": "13800138000",
      "declaration_type": "annual_report",
      "declaration_info": {
        "annual_revenue": 500000,
        "profit": 80000,
        "employees": 3
      },
      "status": "completed",
      "approval_no": "SP2026012000001",
      "approval_date": "2026-01-20",
      "process_result": "年报审核通过",
      "process_notes": "材料齐全，符合要求",
      "processed_by": "user_admin_001",
      "processed_at": "2026-01-20T15:30:00",
      "created_at": "2026-01-20T10:00:00"
    }
  }
}
```

### 2.3 处理工商申报

**接口**: `POST /api/business-declaration/admin/{declaration_id}/process`

**认证要求**: 管理员权限

**路径参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| declaration_id | int | 是 | 申报ID |

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 是 | 处理状态 |
| approval_no | string | 否 | 受理号 |
| approval_date | string | 否 | 受理日期 |
| approval_proof_url | string | 否 | 批准凭证URL |
| process_result | string | 否 | 处理结果说明 |
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

---

## 3. 智能报税管理

### 3.1 获取报税申报列表

**接口**: `GET /api/tax-declaration/admin/list`

**认证要求**: 管理员权限

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | string | 否 | 用户ID筛选 |
| status | string | 否 | 状态筛选 |
| tax_type | string | 否 | 税种筛选 |
| tax_period | string | 否 | 税期筛选 |
| page | int | 否 | 页码（默认1） |
| page_size | int | 否 | 每页数量（默认20，范围1-100） |

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 申报ID |
| declaration_no | string | 申报单号 |
| user_id | string | 用户ID |
| taxpayer_name | string | 纳税人姓名 |
| taxpayer_phone | string | 联系电话 |
| tax_type | string | 税种 |
| tax_period | string | 税期 |
| total_income | float | 收入总额 |
| tax_amount | float | 应纳税额 |
| tax_refund | float | 应退税额 |
| status | string | 状态 |
| created_at | datetime | 创建时间 |
| processed_at | datetime | 处理时间 |

**响应示例**:
```json
{
  "code": 1,
  "message": "操作成功",
  "data": {
    "total": 10,
    "page": 1,
    "page_size": 20,
    "declarations": [
      {
        "id": 1,
        "declaration_no": "TD2026012000001",
        "user_id": "user_123456",
        "taxpayer_name": "张三",
        "taxpayer_phone": "138****8000",
        "tax_type": "pit",
        "tax_period": "2024",
        "total_income": 150000.00,
        "tax_amount": 3480.00,
        "tax_refund": 0.00,
        "status": "pending",
        "created_at": "2026-01-20T10:00:00",
        "processed_at": null
      }
    ]
  }
}
```

### 3.2 获取报税申报详情

**接口**: `GET /api/tax-declaration/{declaration_id}`

**认证要求**: 管理员权限

**路径参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| declaration_id | int | 是 | 申报ID |

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 申报ID |
| declaration_no | string | 申报单号 |
| user_id | string | 用户ID |
| taxpayer_name | string | 纳税人姓名 |
| taxpayer_id_card | string | 身份证号 |
| taxpayer_phone | string | 联系电话 |
| taxpayer_type | string | 纳税人类型 |
| tax_type | string | 税种 |
| tax_period | string | 税期 |
| income_info | object | 收入信息(JSON) |
| deduction_info | object | 扣除信息(JSON) |
| total_income | float | 收入总额 |
| total_deduction | float | 扣除总额 |
| taxable_income | float | 应纳税所得额 |
| tax_amount | float | 应纳税额 |
| tax_paid | float | 已缴税额 |
| tax_refund | float | 应退税额 |
| status | string | 状态 |
| process_result | string | 处理结果 |
| declaration_serial_no | string | 申报流水号 |
| declaration_date | date | 申报日期 |
| declaration_proof_url | string | 申报凭证URL |
| processed_by | string | 处理人ID |
| processed_at | datetime | 处理时间 |
| process_notes | string | 处理备注 |
| user_remarks | string | 用户备注 |
| created_at | datetime | 创建时间 |

**响应示例**:
```json
{
  "code": 1,
  "message": "操作成功",
  "data": {
    "declaration": {
      "id": 1,
      "declaration_no": "TD2026012000001",
      "user_id": "user_123456",
      "taxpayer_name": "张三",
      "taxpayer_id_card": "110101199001011234",
      "taxpayer_phone": "13800138000",
      "taxpayer_type": "individual",
      "tax_type": "pit",
      "tax_period": "2024",
      "income_info": {
        "salary": 120000,
        "bonus": 30000
      },
      "deduction_info": {
        "basic_deduction": 60000,
        "special_deduction": 12000
      },
      "total_income": 150000.00,
      "total_deduction": 72000.00,
      "taxable_income": 78000.00,
      "tax_amount": 3480.00,
      "tax_paid": 0.00,
      "tax_refund": 0.00,
      "status": "completed",
      "process_result": "申报完成",
      "declaration_serial_no": "TAX2026012000001",
      "declaration_date": "2026-01-20",
      "processed_by": "user_admin_001",
      "processed_at": "2026-01-20T15:30:00",
      "created_at": "2026-01-20T10:00:00"
    }
  }
}
```

### 3.3 处理报税申报

**接口**: `POST /api/tax-declaration/admin/{declaration_id}/process`

**认证要求**: 管理员权限

**路径参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| declaration_id | int | 是 | 申报ID |

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 是 | 处理状态 |
| total_income | float | 否 | 收入总额（不填则自动计算） |
| total_deduction | float | 否 | 扣除总额（不填则自动计算） |
| taxable_income | float | 否 | 应纳税所得额（不填则自动计算） |
| tax_amount | float | 否 | 应纳税额（不填则自动计算） |
| tax_paid | float | 否 | 已缴税额 |
| tax_refund | float | 否 | 应退税额（不填则自动计算） |
| declaration_serial_no | string | 否 | 申报流水号 |
| declaration_date | string | 否 | 申报日期 |
| declaration_proof_url | string | 否 | 申报凭证URL |
| process_result | string | 否 | 处理结果说明 |
| process_notes | string | 否 | 处理备注 |

**请求示例**:
```json
{
  "status": "completed",
  "declaration_serial_no": "TAX2026012000001",
  "declaration_date": "2026-01-20",
  "process_result": "申报完成"
}
```

---

## 4. 分销商管理

### 4.1 获取分销商列表

**接口**: `GET /api/distribution/admin/distributors`

**认证要求**: 管理员权限

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 否 | 状态筛选 (active/frozen/inactive) |
| page | int | 否 | 页码（默认1） |
| page_size | int | 否 | 每页数量（默认20，范围1-100） |

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | string | 用户ID |
| distributor_code | string | 推广码 |
| parent_id | string | 上级分销商ID |
| distributor_level | int | 分销等级 |
| status | string | 状态 |
| total_children_count | int | 下级用户数 |
| total_order_count | int | 订单数 |
| total_commission | float | 累计佣金 |
| available_commission | float | 可用佣金 |
| frozen_commission | float | 冻结佣金 |
| total_withdrawn | float | 已提现金额 |
| nickname | string | 昵称 |
| phone | string | 手机号 |
| created_at | datetime | 创建时间 |

**响应示例**:
```json
{
  "code": 1,
  "message": "操作成功",
  "data": {
    "total": 30,
    "page": 1,
    "page_size": 20,
    "distributors": [
      {
        "user_id": "user_123456",
        "distributor_code": "ABC123",
        "parent_id": "user_789",
        "distributor_level": 3,
        "status": "active",
        "total_children_count": 15,
        "total_order_count": 50,
        "total_commission": 5000.00,
        "available_commission": 1000.00,
        "frozen_commission": 500.00,
        "total_withdrawn": 3500.00,
        "nickname": "张三",
        "phone": "138****8000",
        "created_at": "2026-01-01T10:00:00"
      }
    ]
  }
}
```

### 4.2 获取分销商详情

**接口**: `GET /api/distribution/admin/distributors/{user_id}`

**认证要求**: 管理员权限

**路径参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | string | 是 | 分销商用户ID |

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | string | 用户ID |
| distributor_code | string | 推广码 |
| parent_id | string | 上级分销商ID |
| distributor_level | int | 分销等级 |
| status | string | 状态 |
| total_children_count | int | 下级用户数 |
| total_order_count | int | 订单数 |
| total_commission | float | 累计佣金 |
| available_commission | float | 可用佣金 |
| frozen_commission | float | 冻结佣金 |
| total_withdrawn | float | 已提现金额 |
| nickname | string | 昵称 |
| phone | string | 手机号 |
| parent_info | object | 上级分销商信息 |
| created_at | datetime | 创建时间 |

**响应示例**:
```json
{
  "code": 1,
  "message": "操作成功",
  "data": {
    "distributor": {
      "user_id": "user_123456",
      "distributor_code": "ABC123",
      "parent_id": "user_789",
      "distributor_level": 3,
      "status": "active",
      "total_children_count": 15,
      "total_order_count": 50,
      "total_commission": 5000.00,
      "available_commission": 1000.00,
      "frozen_commission": 500.00,
      "total_withdrawn": 3500.00,
      "nickname": "张三",
      "phone": "13800138000",
      "parent_info": {
        "nickname": "上级分销商",
        "distributor_code": "XYZ789"
      },
      "created_at": "2026-01-01T10:00:00"
    }
  }
}
```

### 4.3 更新分销商状态

**接口**: `PUT /api/distribution/admin/distributors/{user_id}/status`

**认证要求**: 管理员权限

**路径参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | string | 是 | 分销商用户ID |

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 是 | 状态值 (active/frozen/inactive) |

**状态说明**:
- `active`: 活跃（正常状态）
- `frozen`: 冻结（暂停分销资格）
- `inactive`: 非活跃（已禁用）

**请求示例**:
```
PUT /api/distribution/admin/distributors/user_123456/status?status=frozen
```

**响应示例**:
```json
{
  "code": 1,
  "message": "分销商状态已从 active 更新为 frozen",
  "data": null
}
```

---

## 5. 分销提现管理

### 5.1 获取提现申请列表

**接口**: `GET /api/distribution/admin/withdrawals`

**认证要求**: 管理员权限

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 否 | 状态筛选 |
| page | int | 否 | 页码（默认1） |
| page_size | int | 否 | 每页数量（默认20，范围1-100） |

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 提现申请ID |
| distributor_id | string | 分销商ID |
| distributor_name | string | 分销商昵称 |
| distributor_phone | string | 分销商手机号 |
| amount | float | 提现金额 |
| account_type | string | 账户类型 |
| bank_name | string | 银行名称 |
| account_number | string | 账号 |
| status | string | 状态 |
| created_at | datetime | 创建时间 |

**响应示例**:
```json
{
  "code": 1,
  "message": "操作成功",
  "data": {
    "total": 10,
    "page": 1,
    "page_size": 20,
    "withdrawals": [
      {
        "id": "wd_1234567890",
        "distributor_id": "user_123456",
        "distributor_name": "张三",
        "distributor_phone": "138****8000",
        "amount": 500.00,
        "account_type": "bank_card",
        "bank_name": "中国工商银行",
        "account_number": "6222***********123",
        "status": "pending",
        "created_at": "2026-01-20T10:00:00"
      }
    ]
  }
}
```

### 5.2 获取提现申请详情

**接口**: `GET /api/distribution/admin/withdrawals/{withdrawal_id}`

**认证要求**: 管理员权限

**路径参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| withdrawal_id | string | 是 | 提现申请ID |

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 提现申请ID |
| distributor_id | string | 分销商ID |
| distributor_name | string | 分销商昵称 |
| distributor_phone | string | 分销商手机号 |
| amount | float | 提现金额 |
| account_type | string | 账户类型 (bank_card/alipay/wechat) |
| bank_name | string | 银行名称 |
| bank_branch | string | 开户支行 |
| account_number | string | 账号 |
| account_holder | string | 持卡人姓名 |
| status | string | 状态 (pending/completed/rejected/cancelled) |
| created_at | datetime | 创建时间 |
| processed_at | datetime | 处理时间 |
| processed_by | string | 处理人ID |
| transaction_id | string | 交易流水号 |
| process_notes | string | 处理备注 |
| reject_reason | string | 拒绝原因 |
| total_commission | float | 总佣金 |
| available_balance | float | 可提现余额 |
| frozen_amount | float | 冻结金额 |
| withdrawn_amount | float | 已提现金额 |

**响应示例**:
```json
{
  "code": 1,
  "message": "操作成功",
  "data": {
    "withdrawal": {
      "id": "wd_1234567890",
      "distributor_id": "user_123456",
      "distributor_name": "张三",
      "distributor_phone": "13800138000",
      "amount": 500.00,
      "account_type": "bank_card",
      "bank_name": "中国工商银行",
      "bank_branch": "北京朝阳支行",
      "account_number": "6222021234567890123",
      "account_holder": "张三",
      "status": "pending",
      "created_at": "2026-01-20T10:00:00",
      "total_commission": 5000.00,
      "available_balance": 1000.00,
      "frozen_amount": 500.00,
      "withdrawn_amount": 3500.00
    }
  }
}
```

### 5.3 审核通过提现

**接口**: `POST /api/distribution/admin/withdrawals/{withdrawal_id}/approve`

**认证要求**: 管理员权限

**路径参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| withdrawal_id | string | 是 | 提现申请ID |

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| transaction_id | string | 否 | 支付平台交易流水号 |

**请求示例**:
```json
{
  "transaction_id": "TX123456789"
}
```

**响应示例**:
```json
{
  "code": 1,
  "message": "提现已完成",
  "data": null
}
```

### 5.4 拒绝提现

**接口**: `POST /api/distribution/admin/withdrawals/{withdrawal_id}/reject`

**认证要求**: 管理员权限

**路径参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| withdrawal_id | string | 是 | 提现申请ID |

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| reject_reason | string | 是 | 拒绝原因 |

**请求示例**:
```json
{
  "reject_reason": "账户信息不完整"
}
```

**响应示例**:
```json
{
  "code": 1,
  "message": "提现已拒绝",
  "data": null
}
```

---

## 6. 状态码说明

### 6.1 响应码 (code)

| 状态码 | 说明 |
|--------|------|
| 1 | 操作成功 |
| 0 | 操作失败 |

### 6.2 HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 401 | 未授权（token 无效或过期） |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

### 6.3 常见错误码

| 错误码 | 说明 |
|--------|------|
| INVALID_TOKEN | 无效的认证token |
| TOKEN_EXPIRED | Token已过期 |
| PERMISSION_DENIED | 权限不足 |
| RESOURCE_NOT_FOUND | 资源不存在 |
| INVALID_PARAMS | 参数错误 |
| INTERNAL_ERROR | 服务器内部错误 |

---

## 7. 业务状态说明

### 7.1 工商申报状态

| 状态 | 说明 |
|------|------|
| pending | 待处理 |
| processing | 处理中 |
| completed | 已完成 |
| rejected | 已拒绝 |

### 7.2 报税申报状态

| 状态 | 说明 |
|------|------|
| pending | 待处理 |
| processing | 处理中 |
| completed | 已完成 |
| rejected | 已拒绝 |

### 7.3 提现申请状态

| 状态 | 说明 |
|------|------|
| pending | 待审核 |
| processing | 处理中 |
| completed | 已完成 |
| rejected | 已拒绝 |
| cancelled | 已取消 |

### 7.4 分销商状态

| 状态 | 说明 |
|------|------|
| active | 活跃（正常） |
| frozen | 冻结（暂停分销资格） |
| inactive | 非活跃（已禁用） |
