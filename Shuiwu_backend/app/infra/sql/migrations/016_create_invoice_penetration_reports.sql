-- 发票穿透报告记录表
-- 用于存储发票穿透报告的生成记录和状态

CREATE TABLE IF NOT EXISTS business.invoice_penetration_reports (
    id BIGSERIAL PRIMARY KEY,

    -- 用户关联
    user_id VARCHAR(50) NOT NULL,

    -- 企业信息
    taxpayer_no VARCHAR(50) NOT NULL,
    company_name VARCHAR(255) NOT NULL,

    -- 订单信息（查税宝返回）
    order_no VARCHAR(100),
    report_url TEXT,

    -- 状态: pending-生成中, success-成功, failed-失败
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_message TEXT,

    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- 回调信息
    callback_received_at TIMESTAMP WITH TIME ZONE,
    callback_state VARCHAR(10),

    CONSTRAINT valid_ip_status CHECK (status IN ('pending', 'success', 'failed'))
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_ip_reports_user_id ON business.invoice_penetration_reports(user_id);
CREATE INDEX IF NOT EXISTS idx_ip_reports_order_no ON business.invoice_penetration_reports(order_no);
CREATE INDEX IF NOT EXISTS idx_ip_reports_status ON business.invoice_penetration_reports(status);
CREATE INDEX IF NOT EXISTS idx_ip_reports_created_at ON business.invoice_penetration_reports(created_at DESC);

-- 添加注释
COMMENT ON TABLE business.invoice_penetration_reports IS '发票穿透报告记录表';
COMMENT ON COLUMN business.invoice_penetration_reports.id IS '主键';
COMMENT ON COLUMN business.invoice_penetration_reports.user_id IS '用户ID';
COMMENT ON COLUMN business.invoice_penetration_reports.taxpayer_no IS '纳税人识别号';
COMMENT ON COLUMN business.invoice_penetration_reports.company_name IS '企业名称';
COMMENT ON COLUMN business.invoice_penetration_reports.order_no IS '查税宝返回的订单号';
COMMENT ON COLUMN business.invoice_penetration_reports.report_url IS '报告文件地址';
COMMENT ON COLUMN business.invoice_penetration_reports.status IS '状态: pending-生成中, success-成功, failed-失败';
COMMENT ON COLUMN business.invoice_penetration_reports.error_message IS '错误信息';
COMMENT ON COLUMN business.invoice_penetration_reports.created_at IS '创建时间';
COMMENT ON COLUMN business.invoice_penetration_reports.updated_at IS '更新时间';
COMMENT ON COLUMN business.invoice_penetration_reports.completed_at IS '完成时间';
COMMENT ON COLUMN business.invoice_penetration_reports.callback_received_at IS '回调接收时间';
COMMENT ON COLUMN business.invoice_penetration_reports.callback_state IS '回调状态（0-失败，1-成功）';
