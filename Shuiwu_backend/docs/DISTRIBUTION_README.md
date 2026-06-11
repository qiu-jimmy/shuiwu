# 分销推广系统使用指南

## 功能概述

实现了完整的用户推广返利系统，支持邀请他人使用获得佣金奖励。

**核心功能：**
- ✅ 生成专属推广码（后端生成，前端可生成二维码）
- ✅ 分享推广内容（分享链接 + 分享文案）
- ✅ 查看推广记录（下级用户、订单、佣金）
- ✅ 邀请用户注册追踪
- ✅ 佣金自动计算和结算
- ✅ 提现申请和审核
- ✅ 后台配置管理（佣金比例、提现门槛等）

---

## 部署步骤

### 1. 执行数据库迁移

```bash
# 在PostgreSQL中执行迁移脚本
psql -h localhost -U postgres -d Agno -f app/infra/sql/migration_distribution_20250119.sql
```

**迁移内容：**
- 创建 `system_configs` 表（系统配置）
- 为 `users` 表添加 `inviter_id` 字段（邀请人）
- 创建相关索引
- 初始化默认配置

### 2. 启动应用

```bash
# 启动应用
python main.py

# 应用启动后可访问：
# http://127.0.0.1:8000/docs  (API文档)
```

### 3. 运行测试

```bash
# 运行分销系统端到端测试
python test/test_distribution_e2e.py
```

---

## API 接口说明

### 用户端接口

#### 1. 成为分销商
```
POST /api/distribution/become-distributor
Headers: Authorization: Bearer {token}
```

#### 2. 获取我的推广码
```
GET /api/distribution/my-code
Headers: Authorization: Bearer {token}

响应示例：
{
  "code": 1,
  "data": {
    "distributor_code": "ABC123",
    "share_link": "https://yourdomain.com/register?ref=ABC123",
    "share_text": "邀请您使用我们的服务，输入邀请码：ABC123"
  }
}
```

#### 3. 获取分销商统计
```
GET /api/distribution/stats
Headers: Authorization: Bearer {token}

响应示例：
{
  "code": 1,
  "data": {
    "total_children_count": 10,
    "total_order_count": 5,
    "total_commission": 100.50,
    "available_commission": 50.00,
    "frozen_commission": 30.50,
    "total_withdrawn": 20.00
  }
}
```

#### 4. 获取分销记录
```
GET /api/distribution/records?status=available&page=1&page_size=20
Headers: Authorization: Bearer {token}
```

#### 5. 创建提现申请
```
POST /api/distribution/withdraw
Headers: Authorization: Bearer {token}
Body: {
  "amount": 50.00,
  "withdrawal_method": "wechat",  // wechat/alipay/bank
  "account_name": "张三",
  "account_number": "wx123456"
}
```

#### 6. 获取提现记录
```
GET /api/distribution/withdrawals?page=1&page_size=20
Headers: Authorization: Bearer {token}
```

### 推广码验证接口

#### 验证推广码（无需登录）
```
GET /api/distribution/validate-code?code=ABC123

响应示例：
{
  "code": 1,
  "data": {
    "valid": true,
    "promoter_id": "user_1234567890"
  }
}
```

### 管理员接口

#### 1. 获取分销商列表
```
GET /api/distribution/admin/distributors?status=active&page=1&page_size=20
Headers: Authorization: Bearer {admin_token}
```

#### 2. 获取提现申请列表
```
GET /api/distribution/admin/withdrawals?status=pending&page=1&page_size=20
Headers: Authorization: Bearer {admin_token}
```

#### 3. 审核通过提现
```
POST /api/distribution/admin/withdrawals/{withdrawal_id}/approve
Headers: Authorization: Bearer {admin_token}
Body: {
  "transaction_id": "TXN123456"
}
```

#### 4. 拒绝提现
```
POST /api/distribution/admin/withdrawals/{withdrawal_id}/reject
Headers: Authorization: Bearer {admin_token}
Body: {
  "reject_reason": "账户信息错误"
}
```

### 系统配置接口

#### 1. 获取分销配置
```
GET /api/config/distribution

响应示例：
{
  "code": 1,
  "data": {
    "commission_rate": 10.0,        // 佣金比例 %
    "min_withdraw_amount": 50.0,    // 最低提现金额（元）
    "settlement_days": 7,          // 佣金结算天数
    "enabled": true                 // 分销系统开关
  }
}
```

#### 2. 更新分销配置（管理员）
```
POST /api/config/distribution
Headers: Authorization: Bearer {admin_token}
Body: {
  "commission_rate": 15.0,
  "min_withdraw_amount": 50.0,
  "settlement_days": 7,
  "enabled": true
}
```

---

## 业务流程

### 1. 注册时使用推广码

```
POST /api/auth/register
Body: {
  "phone": "13800002222",
  "password": "test123456",
  "nickname": "新用户",
  "sms_code": "123456",
  "referral_code": "ABC123"  // 推广码
}
```

系统会：
- 验证推广码有效性
- 创建用户时绑定邀请人关系（inviter_id）

### 2. 订单支付后自动计算佣金

当用户完成订单支付后：
```python
# 在 member_service.complete_payment() 中自动触发
distribution_service.process_order_commission(
    order_id=order_id,
    new_user_id=user_id,
    order_amount=order_amount
)
```

系统会：
- 检查用户是否有邀请人
- 验证邀请人是否是分销商
- 按配置的佣金比例计算佣金
- 创建分销记录（状态：pending）
- 增加分销商冻结佣金

### 3. 佣金结算

定时任务需定期调用：
```python
distribution_service.settle_pending_commissions()
```

系统会：
- 查询已过期的pending佣金
- 更新状态为available（可提现）
- 增加可提现余额，减少冻结余额

### 4. 用户提现

用户创建提现申请后：
- 检查可提现余额
- 检查最低提现金额
- 创建提现申请（状态：pending）
- 扣减可提现余额，增加冻结金额

管理员审核通过后：
- 更新提现状态为completed
- 扣减冻结金额，增加已提现金额

管理员拒绝后：
- 更新提现状态为rejected
- 将冻结金额退回可提现余额

---

## 前端集成指南

### 1. 生成二维码（前端）

后端返回推广码后，前端可使用 `qrcode.js` 生成二维码：

```javascript
import QRCode from 'qrcode';

// 获取推广码
const response = await fetch('/api/distribution/my-code', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const { distributor_code, share_link, share_text } = response.data;

// 生成二维码
const qrCode = await QRCode.toDataURL(share_link);
document.getElementById('qrcode').src = qrCode;

// 显示分享链接和文案
document.getElementById('share-link').textContent = share_link;
document.getElementById('share-text').textContent = share_text;
```

### 2. 注册时使用推广码

```javascript
// 注册表单
const registerForm = {
  phone: '13800002222',
  password: 'test123456',
  nickname: '新用户',
  sms_code: '123456',
  referral_code: 'ABC123'  // 从URL参数获取或用户输入
};

// 如果URL带 ?ref=ABC123
const urlParams = new URLSearchParams(window.location.search);
registerForm.referral_code = urlParams.get('ref');
```

---

## 默认配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| commission_rate | 10 | 佣金比例 10% |
| min_withdraw_amount | 50 | 最低提现金额 50元 |
| settlement_days | 7 | 佣金结算 7天 |
| enabled | true | 分销系统开关 |

修改配置通过 `POST /api/config/distribution` 接口。

---

## 数据库表结构

### system_configs（系统配置表）
- config_key: 配置键
- config_value: 配置值
- config_type: 配置类型
- description: 配置描述

### distributors（分销商表）
- user_id: 用户ID
- distributor_code: 推广码
- parent_id: 上级分销商ID
- status: 状态
- total_children_count: 下级用户数
- total_order_count: 累计订单数
- total_commission: 累计佣金
- available_commission: 可提现佣金
- frozen_commission: 冻结佣金
- total_withdrawn: 已提现金额

### distribution_records（分销记录表）
- record_id: 记录ID
- promoter_id: 推广人ID
- new_user_id: 新用户ID
- order_id: 订单ID
- commission_amount: 佣金金额
- commission_status: 佣金状态
- commission_type: 佣金类型
- commission_rate: 佣金比例
- order_amount: 订单金额
- available_time: 可提现时间
- settled_time: 结算时间

### withdrawal_requests（提现申请表）
- withdrawal_id: 提现ID
- user_id: 用户ID
- amount: 提现金额
- withdrawal_method: 提现方式
- account_name: 账户名称
- account_number: 账户号码
- bank_name: 银行名称
- bank_branch: 银行支行
- status: 状态
- reject_reason: 拒绝原因
- processed_by: 处理人
- transaction_id: 交易ID

---

## 常见问题

### Q1: 如何修改佣金比例？
A: 调用 `POST /api/config/distribution` 接口修改 `commission_rate` 参数。

### Q2: 佣金什么时候变成可提现？
A: 订单支付后，佣金状态为 `pending`，经过配置的结算天数（默认7天）后变为 `available`（可提现）。

### Q3: 如何结算佣金？
A: 需要配置定时任务定期调用 `distribution_service.settle_pending_commissions()` 方法。

### Q4: 前端如何生成二维码？
A: 后端只返回推广码和分享链接，前端使用 `qrcode.js` 等库生成二维码。

### Q5: 支持多级分销吗？
A: 目前只支持单级分销（只给直接推荐人返佣），未来可扩展。

---

## 测试说明

运行测试脚本：
```bash
python test/test_distribution_e2e.py
```

测试流程：
1. 注册推广人
2. 成为分销商
3. 获取推广码
4. 验证推广码
5. 通过推广码注册新用户
6. 新用户创建订单
7. 完成支付（触发佣金计算）
8. 检查推广人佣金
9. 获取分销配置

---

## 注意事项

1. **二维码生成**：后端只返回推广码，前端需自己生成二维码
2. **定时任务**：佣金结算需要定时任务定期触发
3. **权限控制**：管理员接口需配置权限中间件
4. **提现审核**：需管理员手动审核提现申请
5. **数据迁移**：部署前务必执行数据库迁移脚本
