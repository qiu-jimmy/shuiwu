-- 全景报告系统表
-- 用于存储查税宝全景报告的生成记录和状态

CREATE TABLE IF NOT EXISTS business.panoramic_reports (
    -- 主键
    id BIGSERIAL PRIMARY KEY,

    -- 用户关联
    user_id VARCHAR(50) NOT NULL,

    -- 企业信息
    taxpayer_no VARCHAR(50) NOT NULL,
    taxpayer_name VARCHAR(255) NOT NULL,

    -- 报告信息
    report_id BIGINT,
    report_url TEXT,

    -- 完整报告数据（JSON格式存储）
    report_data JSONB,

    -- 状态: pending-生成中, success-成功, failed-失败
    status VARCHAR(20) NOT NULL DEFAULT 'pending',

    -- 错误信息（如果失败）
    error_message TEXT,

    -- 报告配置
    report_logo TEXT,
    watermark TEXT,
    cover_url TEXT,
    is_anonymity INTEGER DEFAULT 0,

    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- 回调信息
    callback_received_at TIMESTAMP WITH TIME ZONE,
    callback_state VARCHAR(10),

    -- 索引
    CONSTRAINT valid_status CHECK (status IN ('pending', 'success', 'failed'))
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_panoramic_reports_user_id ON business.panoramic_reports(user_id);
CREATE INDEX IF NOT EXISTS idx_panoramic_reports_taxpayer_no ON business.panoramic_reports(taxpayer_no);
CREATE INDEX IF NOT EXISTS idx_panoramic_reports_report_id ON business.panoramic_reports(report_id);
CREATE INDEX IF NOT EXISTS idx_panoramic_reports_status ON business.panoramic_reports(status);
CREATE INDEX IF NOT EXISTS idx_panoramic_reports_created_at ON business.panoramic_reports(created_at DESC);

-- 添加注释
COMMENT ON TABLE business.panoramic_reports IS '全景报告记录表';
COMMENT ON COLUMN business.panoramic_reports.id IS '主键';
COMMENT ON COLUMN business.panoramic_reports.user_id IS '用户ID';
COMMENT ON COLUMN business.panoramic_reports.taxpayer_no IS '纳税人识别号';
COMMENT ON COLUMN business.panoramic_reports.taxpayer_name IS '企业名称';
COMMENT ON COLUMN business.panoramic_reports.report_id IS '查税宝返回的报告ID';
COMMENT ON COLUMN business.panoramic_reports.report_url IS '报告PDF下载地址';
COMMENT ON COLUMN business.panoramic_reports.report_data IS '完整报告数据（JSONB格式）';
COMMENT ON COLUMN business.panoramic_reports.status IS '状态: pending-生成中, success-成功, failed-失败';
COMMENT ON COLUMN business.panoramic_reports.error_message IS '错误信息';
COMMENT ON COLUMN business.panoramic_reports.report_logo IS '封面logo URL';
COMMENT ON COLUMN business.panoramic_reports.watermark IS '水印 URL';
COMMENT ON COLUMN business.panoramic_reports.cover_url IS '封面 URL';
COMMENT ON COLUMN business.panoramic_reports.is_anonymity IS '是否匿名（0-否，1-是）';
COMMENT ON COLUMN business.panoramic_reports.created_at IS '创建时间';
COMMENT ON COLUMN business.panoramic_reports.updated_at IS '更新时间';
COMMENT ON COLUMN business.panoramic_reports.completed_at IS '完成时间';
COMMENT ON COLUMN business.panoramic_reports.callback_received_at IS '回调接收时间';
COMMENT ON COLUMN business.panoramic_reports.callback_state IS '回调状态（0-失败，1-成功）';
