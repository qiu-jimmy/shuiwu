-- 创建支付回调记录表，用于幂等性保护
-- 防止同一笔支付重复处理

-- 支付回调记录表
CREATE TABLE IF NOT EXISTS business.payment_notify_records (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(100) UNIQUE NOT NULL,
    order_id VARCHAR(50) NOT NULL,
    out_trade_no VARCHAR(50) NOT NULL,
    trade_state VARCHAR(20) NOT NULL,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notify_data TEXT,
    process_result VARCHAR(20), -- success, failed, duplicate
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引优化查询性能
CREATE INDEX IF NOT EXISTS idx_payment_notify_records_transaction_id ON business.payment_notify_records(transaction_id);
CREATE INDEX IF NOT EXISTS idx_payment_notify_records_order_id ON business.payment_notify_records(order_id);
CREATE INDEX IF NOT EXISTS idx_payment_notify_records_out_trade_no ON business.payment_notify_records(out_trade_no);

COMMENT ON TABLE business.payment_notify_records IS '支付回调记录表，用于幂等性保护';
COMMENT ON COLUMN business.payment_notify_records.id IS '主键ID';
COMMENT ON COLUMN business.payment_notify_records.transaction_id IS '微信支付交易号（唯一）';
COMMENT ON COLUMN business.payment_notify_records.order_id IS '内部订单ID';
COMMENT ON COLUMN business.payment_notify_records.out_trade_no IS '商户订单号';
COMMENT ON COLUMN business.payment_notify_records.trade_state IS '交易状态';
COMMENT ON COLUMN business.payment_notify_records.processed_at IS '处理时间';
COMMENT ON COLUMN business.payment_notify_records.notify_data IS '回调数据（JSON）';
COMMENT ON COLUMN business.payment_notify_records.process_result IS '处理结果: success-成功, failed-失败, duplicate-重复';
COMMENT ON COLUMN business.payment_notify_records.error_message IS '错误信息';
COMMENT ON COLUMN business.payment_notify_records.created_at IS '创建时间';
