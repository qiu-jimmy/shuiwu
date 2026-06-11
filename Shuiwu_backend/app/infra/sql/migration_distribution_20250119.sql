-- ============================================================================
-- 分销系统数据库迁移
-- 日期: 2025-01-19
-- 说明: 添加系统配置表和用户邀请人字段
-- ============================================================================

-- 1. 添加系统配置表
CREATE TABLE IF NOT EXISTS business.system_configs (
    config_key VARCHAR(50) PRIMARY KEY,
    config_value TEXT NOT NULL,
    config_type VARCHAR(20) DEFAULT 'string', -- string, number, boolean, json
    description VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE business.system_configs IS '系统配置表';
COMMENT ON COLUMN business.system_configs.config_key IS '配置键';
COMMENT ON COLUMN business.system_configs.config_value IS '配置值';
COMMENT ON COLUMN business.system_configs.config_type IS '配置类型: string-字符串, number-数字, boolean-布尔, json-JSON';
COMMENT ON COLUMN business.system_configs.description IS '配置描述';
COMMENT ON COLUMN business.system_configs.created_at IS '创建时间';
COMMENT ON COLUMN business.system_configs.updated_at IS '更新时间';

-- 2. 为用户表添加邀请人字段
ALTER TABLE business.users ADD COLUMN IF NOT EXISTS inviter_id VARCHAR(50);
ALTER TABLE business.users ADD CONSTRAINT fk_users_inviter FOREIGN KEY (inviter_id) REFERENCES business.users(user_id) ON DELETE SET NULL;

COMMENT ON COLUMN business.users.inviter_id IS '邀请人ID（注册来源）';

-- 3. 为分销商表添加索引
CREATE INDEX IF NOT EXISTS idx_distributors_status ON business.distributors(status);
CREATE INDEX IF NOT EXISTS idx_distributors_level ON business.distributors(distributor_level);

-- 4. 为分销记录表添加索引
CREATE INDEX IF NOT EXISTS idx_distribution_records_promoter ON business.distribution_records(promoter_id);
CREATE INDEX IF NOT EXISTS idx_distribution_records_new_user ON business.distribution_records(new_user_id);
CREATE INDEX IF NOT EXISTS idx_distribution_records_order ON business.distribution_records(order_id);
CREATE INDEX IF NOT EXISTS idx_distribution_records_status ON business.distribution_records(commission_status);
CREATE INDEX IF NOT EXISTS idx_distribution_records_created ON business.distribution_records(created_at);

-- 5. 为提现申请表添加索引
CREATE INDEX IF NOT EXISTS idx_withdrawal_requests_user ON business.withdrawal_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_withdrawal_requests_status ON business.withdrawal_requests(status);
CREATE INDEX IF NOT EXISTS idx_withdrawal_requests_created ON business.withdrawal_requests(created_at);

-- 6. 为用户表添加邀请人索引
CREATE INDEX IF NOT EXISTS idx_users_inviter ON business.users(inviter_id);

-- ============================================================================
-- 初始化分销系统默认配置
-- ============================================================================

-- 分销佣金比例（百分比，如 10 表示 10%）
INSERT INTO business.system_configs (config_key, config_value, config_type, description)
VALUES ('distribution_commission_rate', '10', 'number', '分销佣金比例（百分比，例如 10 表示 10%）')
ON CONFLICT (config_key) DO NOTHING;

-- 提现最低金额（元）
INSERT INTO business.system_configs (config_key, config_value, config_type, description)
VALUES ('distribution_min_withdraw_amount', '50', 'number', '提现最低金额（元）')
ON CONFLICT (config_key) DO NOTHING;

-- 佣金结算天数（订单支付后多少天佣金变为可提现）
INSERT INTO business.system_configs (config_key, config_value, config_type, description)
VALUES ('distribution_settlement_days', '7', 'number', '佣金结算天数（订单支付后多少天佣金变为可提现）')
ON CONFLICT (config_key) DO NOTHING;

-- 分销系统开关（true=开启，false=关闭）
INSERT INTO business.system_configs (config_key, config_value, config_type, description)
VALUES ('distribution_enabled', 'true', 'boolean', '分销系统开关（true=开启，false=关闭）')
ON CONFLICT (config_key) DO NOTHING;

-- ============================================================================
-- 更新时间触发器
-- ============================================================================

CREATE OR REPLACE FUNCTION business.update_system_config_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_system_config_updated_at ON business.system_configs;
CREATE TRIGGER trigger_update_system_config_updated_at
BEFORE UPDATE ON business.system_configs
FOR EACH ROW
EXECUTE FUNCTION business.update_system_config_updated_at();
