# 订单系统设计方案

> 微信支付集成订单系统完整设计方案
>
> 版本: v1.0
> 日期: 2025-01-15

---

## 目录

- [一、整体架构设计](#一整体架构设计)
- [二、数据库设计](#二数据库设计)
- [三、API 端点设计](#三api-端点设计)
- [四、核心服务分层设计](#四核心服务分层设计)
- [五、微信支付集成方案](#五微信支付集成方案)
- [六、与现有架构的集成](#六与现有架构的集成)
- [七、安全设计](#七安全设计)
- [八、开发优先级](#八开发优先级)
- [九、需要确认的问题](#九需要确认的问题)

---

## 一、整体架构设计

### 1.1 目录结构规划

```
app/
├── infra/
│   ├── order_db.py              # 订单数据库初始化
│   ├── sql/migrations/
│   │   ├── 005_orders_schema.sql
│   │   ├── 006_order_tables.sql
│   │   └── 007_order_indexes.sql
│   └── wechat_pay_client.py     # 微信支付 HTTP 客户端
│
├── schemas/
│   ├── order/                   # 订单相关 Schema
│   │   ├── __init__.py
│   │   ├── order_request.py     # 创建订单、查询请求
│   │   ├── order_response.py    # 订单响应模型
│   │   └── order_models.py      # Order、OrderItem ORM
│   │
│   └── payment/                 # 支付相关 Schema
│       ├── __init__.py
│       ├── payment_request.py   # 支付请求模型
│       ├── payment_response.py  # 支付响应模型
│       └── payment_models.py    # Payment、Refund ORM
│
├── services/
│   ├── order/                   # 订单服务层
│   │   ├── __init__.py
│   │   ├── order_service.py     # 订单业务逻辑
│   │   ├── order_repository.py  # 订单数据访问
│   │   └── payment_service.py   # 支付业务逻辑
│   │
│   └── wechat_pay/              # 微信支付服务层
│       ├── __init__.py
│       ├── wechat_pay_service.py    # 微信支付 API 封装
│       ├── wechat_pay_repository.py # 微信支付配置管理
│       └── signature.py            # 签名/验签工具
│
└── api/
    ├── order.py                 # 订单路由
    └── payment.py               # 支付/退款路由
```

### 1.2 架构设计原则

- **分层架构**: API层 → Service层 → Repository层
- **职责分离**: 每层有明确的职责边界
- **领域驱动**: 按业务域划分服务模块
- **独立Schema**: 订单系统使用独立的 `orders` PostgreSQL schema
- **异步优先**: 全链路使用 async/await

---

## 二、数据库设计

### 2.1 PostgreSQL Schema

创建独立的 `orders` schema:

```sql
-- 005_orders_schema.sql
CREATE SCHEMA IF NOT EXISTS orders;
COMMENT ON SCHEMA orders IS '订单系统专用schema';
```

### 2.2 核心表结构

| 表名 | 说明 | 关键字段 |
|------|------|----------|
| `orders.orders` | 订单主表 | id, user_id, order_no, status, total_amount |
| `orders.order_items` | 订单商品明细 | id, order_id, product_id, quantity, price |
| `orders.payments` | 支付记录 | id, order_id, transaction_id, status, amount |
| `orders.refunds` | 退款记录 | id, payment_id, refund_id, status, amount |
| `orders.order_status_log` | 状态变更日志 | id, order_id, old_status, new_status |

### 2.3 订单状态枚举

```sql
CREATE TYPE orders.order_status AS ENUM (
    'PENDING',       -- 待支付
    'PAID',          -- 已支付
    'SHIPPED',       -- 已发货
    'COMPLETED',     -- 已完成
    'CANCELLED',     -- 已取消
    'REFUNDING',     -- 退款中
    'REFUNDED'       -- 已退款
);
```

### 2.4 支付状态枚举

```sql
CREATE TYPE orders.payment_status AS ENUM (
    'PENDING',       -- 待支付
    'PROCESSING',    -- 支付处理中
    'SUCCESS',       -- 支付成功
    'FAILED',        -- 支付失败
    'REFUNDING',     -- 退款中
    'REFUNDED',      -- 已退款
    'CANCELLED'      -- 已取消
);
```

### 2.5 表结构详细设计

#### 2.5.1 订单主表 (orders)

```sql
CREATE TABLE orders.orders (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    order_no VARCHAR(32) UNIQUE NOT NULL,
    status orders.order_status DEFAULT 'PENDING',
    total_amount INTEGER NOT NULL,  -- 单位:分
    discount_amount INTEGER DEFAULT 0,  -- 优惠金额(分)
    actual_amount INTEGER NOT NULL,  -- 实付金额(分)
    remark TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    paid_at TIMESTAMP,

    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_orders_user_id ON orders.orders(user_id);
CREATE INDEX idx_orders_order_no ON orders.orders(order_no);
CREATE INDEX idx_orders_status ON orders.orders(status);
CREATE INDEX idx_orders_created_at ON orders.orders(created_at DESC);
```

#### 2.5.2 订单商品明细表 (order_items)

```sql
CREATE TABLE orders.order_items (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    product_image VARCHAR(500),
    quantity INTEGER NOT NULL,
    unit_price INTEGER NOT NULL,  -- 单价(分)
    total_price INTEGER NOT NULL,  -- 小计(分)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_order FOREIGN KEY (order_id) REFERENCES orders.orders(id) ON DELETE CASCADE
);

CREATE INDEX idx_order_items_order_id ON orders.order_items(order_id);
CREATE INDEX idx_order_items_product_id ON orders.order_items(product_id);
```

#### 2.5.3 支付记录表 (payments)

```sql
CREATE TABLE orders.payments (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL,
    payment_no VARCHAR(32) UNIQUE NOT NULL,
    transaction_id VARCHAR(64),  -- 微信支付交易号
    status orders.payment_status DEFAULT 'PENDING',
    amount INTEGER NOT NULL,  -- 支付金额(分)
    payment_method VARCHAR(20) DEFAULT 'WECHAT_JSAPI',
    prepay_id VARCHAR(64),  -- 预支付交易会话标识
    openid VARCHAR(128),  -- 用户openid
    notify_data JSONB,  -- 回调通知原始数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    paid_at TIMESTAMP,

    CONSTRAINT fk_payment_order FOREIGN KEY (order_id) REFERENCES orders.orders(id)
);

CREATE INDEX idx_payments_order_id ON orders.payments(order_id);
CREATE INDEX idx_payments_payment_no ON orders.payments(payment_no);
CREATE INDEX idx_payments_transaction_id ON orders.payments(transaction_id);
CREATE INDEX idx_payments_status ON orders.payments(status);
```

#### 2.5.4 退款记录表 (refunds)

```sql
CREATE TABLE orders.refunds (
    id BIGSERIAL PRIMARY KEY,
    payment_id BIGINT NOT NULL,
    refund_no VARCHAR(32) UNIQUE NOT NULL,
    refund_id VARCHAR(64),  -- 微信退款单号
    status orders.payment_status DEFAULT 'PENDING',
    amount INTEGER NOT NULL,  -- 退款金额(分)
    reason VARCHAR(255),
    notify_data JSONB,  -- 回调通知原始数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    refunded_at TIMESTAMP,

    CONSTRAINT fk_refund_payment FOREIGN KEY (payment_id) REFERENCES orders.payments(id)
);

CREATE INDEX idx_refunds_payment_id ON orders.refunds(payment_id);
CREATE INDEX idx_refunds_refund_no ON orders.refunds(refund_no);
CREATE INDEX idx_refunds_refund_id ON orders.refunds(refund_id);
```

#### 2.5.5 订单状态日志表 (order_status_log)

```sql
CREATE TABLE orders.order_status_log (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL,
    old_status orders.order_status,
    new_status orders.order_status NOT NULL,
    remark VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_log_order FOREIGN KEY (order_id) REFERENCES orders.orders(id) ON DELETE CASCADE
);

CREATE INDEX idx_status_log_order_id ON orders.order_status_log(order_id);
```

### 2.6 订单状态流转图

```
                    ┌─────────────┐
                    │   PENDING   │ (待支付)
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
       ┌──────────┐  ┌──────────┐  ┌──────────┐
       │ CANCELLED│  │   PAID   │  │  超时关闭  │
       └──────────┘  └────┬─────┘  └──────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   SHIPPED   │ (已发货)
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  COMPLETED  │ (已完成)
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
       ┌─────────────┐          ┌─────────────┐
       │  REFUNDING  │          │   (结束)     │
       └──────┬──────┘          └─────────────┘
              │
              ▼
       ┌─────────────┐
       │  REFUNDED   │
       └─────────────┘
```

---

## 三、API 端点设计

### 3.1 订单相关接口

| 端点 | 方法 | 描述 | 认证 |
|------|------|------|------|
| `/api/orders` | POST | 创建订单 | JWT |
| `/api/orders/{order_id}` | GET | 查询订单详情 | JWT |
| `/api/orders` | GET | 订单列表(分页) | JWT |
| `/api/orders/{order_id}/cancel` | POST | 取消订单 | JWT |

### 3.2 支付相关接口

| 端点 | 方法 | 描述 | 认证 |
|------|------|------|------|
| `/api/payments/jsapi` | POST | 发起JSAPI支付 | JWT |
| `/api/payments/notify` | POST | 微信支付回调 | **无需认证**(验签) |
| `/api/payments/{payment_id}` | GET | 查询支付状态 | JWT |
| `/api/refunds` | POST | 申请退款 | JWT |
| `/api/refunds/notify` | POST | 微信退款回调 | **无需认证**(验签) |

### 3.3 API 响应格式

统一使用项目现有的响应格式:

```json
{
  "code": 1,
  "message": "success",
  "data": {
    // 具体业务数据
  }
}
```

---

## 四、核心服务分层设计

### 4.1 API 层 (Route层)

**职责**: HTTP 请求/响应处理,参数验证,用户认证

```python
# app/api/order.py
from fastapi import APIRouter, Depends
from app.schemas.order.order_request import CreateOrderRequest
from app.schemas.order.order_response import OrderResponse
from app.services.order.order_service import OrderService
from app.infra.db import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/orders", tags=["订单"])

@router.post("/", summary="创建订单")
async def create_order(
    request: CreateOrderRequest,
    current_user: User = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. 参数验证
    # 2. 调用 OrderService.create_order()
    # 3. 返回统一响应格式
    pass
```

### 4.2 Service 层 (业务逻辑层)

**职责**: 核心业务逻辑,事务管理,跨表操作

```python
# app/services/order/order_service.py
class OrderService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = OrderRepository(db)

    async def create_order(self, user_id: int, items: List[OrderItem]) -> Order:
        # 1. 生成订单号
        # 2. 计算金额
        # 3. 创建订单记录
        # 4. 创建订单明细
        # 5. 记录状态日志
        pass
```

### 4.3 Repository 层 (数据访问层)

**职责**: 数据库 CRUD 操作,SQL 查询封装

```python
# app/services/order/order_repository.py
class OrderRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, order: Order) -> Order:
        self.db.add(order)
        await self.db.commit()
        await self.db.refresh(order)
        return order

    async def get_by_order_no(self, order_no: str) -> Optional[Order]:
        result = await self.db.execute(
            select(Order).where(Order.order_no == order_no)
        )
        return result.scalar_one_or_none()
```

---

## 五、微信支付集成方案

### 5.1 环境变量配置

```env
# 微信支付配置
WECHAT_PAY_APPID=wx1234567890abcdef
WECHAT_PAY_MCHID=1234567890
WECHAT_PAY_API_V3_KEY=your_api_v3_key_32bytes
WECHAT_PAY_CERT_SERIAL_NO=your_cert_serial_no
WECHAT_PAY_PRIVATE_KEY_PATH=./certs/apiclient_key.pem
WECHAT_PAY_PUBLIC_KEY_PATH=./certs/wxpay_pubkey.pem
WECHAT_PAY_NOTIFY_URL=https://yourdomain.com/api/payments/notify
```

### 5.2 微信支付核心流程

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│ 小程序前端   │         │  后端服务     │         │  微信支付    │
└──────┬──────┘         └──────┬───────┘         └──────┬──────┘
       │                       │                         │
       │  1. 发起下单请求       │                         │
       │──────────────────────>│                         │
       │                       │                         │
       │                       │  2. 调用JSAPI下单接口    │
       │                       │────────────────────────>│
       │                       │                         │
       │                       │  3. 返回 prepay_id      │
       │                       │<────────────────────────│
       │                       │                         │
       │  4. 返回支付参数       │                         │
       │<──────────────────────│                         │
       │                       │                         │
       │  5. 调起支付           │                         │
       │────────────────────────────────────────────────>│
       │                       │                         │
       │  6. 支付完成           │                         │
       │<────────────────────────────────────────────────│
       │                       │                         │
       │                       │  7. 异步通知支付结果     │
       │                       │<────────────────────────│
       │                       │                         │
       │  8. 查询订单状态       │                         │
       │<──────────────────────│                         │
```

### 5.3 关键技术点

| 技术点 | 实现方案 |
|--------|----------|
| **签名生成** | RSA2048 + SHA256,使用商户私钥 |
| **签名验证** | 使用微信支付公钥验证回调签名 |
| **证书序列号** | 从商户证书中提取,放在请求头 |
| **时间戳** | Unix时间戳(秒级) |
| **随机串** | 32位随机字符串 |

### 5.4 微信支付 API 列表

| API | 端点 | 说明 |
|-----|------|------|
| JSAPI下单 | POST /v3/pay/transactions/jsapi | 获取预支付ID |
| 查询订单 | GET /v3/pay/transactions/out-trade-no/{no} | 查询订单状态 |
| 关闭订单 | POST /v3/pay/transactions/out-trade-no/{no}/close | 关闭订单 |
| 申请退款 | POST /v3/refund/domestic/refunds | 发起退款 |
| 查询退款 | GET /v3/refund/domestic/refunds/{id} | 查询退款状态 |

---

## 六、与现有架构的集成

### 6.1 复用现有组件

- ✅ **数据库依赖注入**: 复用 `app/infra/db.py` 的 `get_db()`
- ✅ **JWT认证**: 复用现有中间件获取 `current_user`
- ✅ **响应格式**: 复用 `app.utils.response` 的统一响应
- ✅ **异常处理**: 复用全局异常处理器
- ✅ **配置管理**: 复用环境变量配置模式

### 6.2 新增独立组件

- 🆕 **订单数据库**: 独立的 `orders` schema
- 🆕 **微信支付客户端**: 封装 HTTP 请求和签名逻辑
- 🆕 **订单服务管理器**: 类似 `mcp_service_manager` 的单例模式

### 6.3 主程序注册

```python
# app/main.py

# 导入订单路由
from app.api import order, payment

# 注册路由
app.include_router(order.router)
app.include_router(payment.router)

# 启动时初始化订单数据库
@app.on_event("startup")
async def startup_event():
    # 现有的初始化逻辑...

    # 初始化订单数据库
    from app.infra.order_db import init_order_db
    await init_order_db()

    # 初始化微信支付配置
    from app.services.wechat_pay.wechat_pay_repository import wechat_pay_config
    await wechat_pay_config.load_config()
```

---

## 七、安全设计

### 7.1 数据安全

| 措施 | 说明 |
|------|------|
| **金额存储** | 使用整数(分),避免浮点误差 |
| **订单号唯一性** | 数据库唯一索引 + 分布式锁 |
| **幂等性** | 使用 `out_trade_no` 防重复 |
| **敏感信息** | 私钥文件权限限制,不进Git |
| **SQL注入防护** | 使用 ORM 参数化查询 |

### 7.2 支付安全

| 措施 | 说明 |
|------|------|
| **签名验证** | 所有回调必须验签 |
| **双重验证** | 回调后主动查询订单状态 |
| **时间窗口** | 回调时间戳检查(5分钟内) |
| **金额校验** | 回调金额与订单金额对比 |
| **防重放攻击** | 回调请求唯一性校验 |

### 7.3 接口安全

| 措施 | 说明 |
|------|------|
| **JWT认证** | 所有业务接口需认证 |
| **权限控制** | 用户只能访问自己的订单 |
| **限流保护** | 防止恶意刷单 |
| **日志审计** | 记录所有支付操作 |

---

## 八、开发优先级

### 第一阶段: MVP(最小可用产品)

**目标**: 实现核心支付流程

1. ✅ 数据库表设计和迁移
2. ✅ 订单创建和查询接口
3. ✅ 微信支付 JSAPI 下单
4. ✅ 支付回调处理和状态更新

**交付物**:
- 用户可以创建订单
- 用户可以完成支付
- 支付后订单状态正确更新

### 第二阶段: 完整功能

**目标**: 完善订单和支付功能

5. ✅ 订单取消功能
6. ✅ 退款申请和回调
7. ✅ 订单列表和分页
8. ✅ 订单状态日志查询

**交付物**:
- 完整的订单管理功能
- 支持退款流程
- 订单查询和筛选

### 第三阶段: 增强功能

**目标**: 增加业务扩展能力

9. ✅ 商品管理(如需要)
10. ✅ 优惠券系统
11. ✅ 发票集成
12. ✅ 对账报表

**交付物**:
- 完整的电商功能
- 运营数据分析能力

---

## 九、需要确认的问题

在开始编码前,请确认以下问题:

### 9.1 商品管理

- [ ] 是否已有商品表?还是需要新建?
- [ ] 商品信息是否需要 SKU 管理?
- [ ] 是否需要库存管理?

### 9.2 用户体系

- [ ] 订单关联现有的 `users` 表吗?
- [ ] 是否已实现微信小程序登录(获取 openid)?
- [ ] OpenID 存储在哪里?

### 9.3 支付场景

- [ ] 仅支持小程序 JSAPI 支付?
- [ ] 是否需要支持 H5/APP 支付?
- [ ] 是否需要支持分账功能?

### 9.4 业务扩展

- [ ] 是否需要优惠券/积分功能?
- [ ] 是否需要发票功能?
- [ ] 是否需要物流信息跟踪?

### 9.5 通知方式

- [ ] 支付成功后是否需要发送小程序订阅消息?
- [ ] 是否需要邮件/短信通知?
- [ ] 是否需要商户后台通知?

---

## 附录

### A. 参考文档

- [微信支付 JSAPI 下单文档](https://pay.weixin.qq.com/doc/v3/merchant/4012791897)
- [微信支付API v3签名规则](https://pay.weixin.qq.com/doc/v3/merchant/4012791897)
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 文档](https://docs.sqlalchemy.org/en/20/)

### B. 技术栈

| 组件 | 版本 | 说明 |
|------|------|------|
| FastAPI | 0.115.0 | Web框架 |
| SQLAlchemy | 2.0.36 | ORM |
| asyncpg | - | 异步PostgreSQL驱动 |
| Pydantic | 2.x | 数据验证 |
| httpx | - | 异步HTTP客户端 |
| cryptography | - | RSA签名 |

### C. 联系方式

- 项目负责人: [待填写]
- 技术支持: [待填写]
- 文档更新: 2025-01-15

---

**© 2025 税务后端系统 | 版本 v1.0**
