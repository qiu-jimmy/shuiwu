-- ============================================================================
-- 积分系统迁移 - 删除旧表并创建双表
-- Version: 008
-- Description: 删除旧的单表设计，创建新的双表设计
-- ============================================================================

-- ============================================================================
-- 1. 删除旧的对象（如果存在）
-- ============================================================================

-- 删除旧视图
DROP VIEW IF EXISTS business.v_points_statistics CASCADE;
DROP VIEW IF EXISTS business.v_user_points_summary CASCADE;

-- 删除旧表
DROP TABLE IF EXISTS business.point_records CASCADE;

-- ============================================================================
-- 2. 创建新的双表结构
-- ============================================================================

-- 2.1 用户积分余额表
CREATE TABLE IF NOT EXISTS business.user_points (
    user_id VARCHAR(50) PRIMARY KEY REFERENCES business.users(user_id) ON DELETE CASCADE,
    points_balance INTEGER DEFAULT 0,           -- 当前积分余额
    total_points_earned INTEGER DEFAULT 0,      -- 累计获得积分
    total_points_used INTEGER DEFAULT 0,        -- 累计使用积分（预留）
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE business.user_points IS '用户积分余额表';
COMMENT ON COLUMN business.user_points.user_id IS '用户ID';
COMMENT ON COLUMN business.user_points.points_balance IS '当前积分余额';
COMMENT ON COLUMN business.user_points.total_points_earned IS '累计获得积分';
COMMENT ON COLUMN business.user_points.total_points_used IS '累计使用积分（预留）';
COMMENT ON COLUMN business.user_points.updated_at IS '更新时间';

-- 2.2 积分变动记录表（流水表）
CREATE TABLE IF NOT EXISTS business.point_records (
    record_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL REFERENCES business.users(user_id) ON DELETE CASCADE,
    points INTEGER NOT NULL,                    -- 积分变动数量（正数=获得）
    change_type VARCHAR(50) NOT NULL,           -- 变化类型：order_payment/invitation_reward/register_reward
    change_reason VARCHAR(200),                 -- 变化说明
    related_order_id VARCHAR(50),               -- 关联订单ID（支付送积分）
    related_user_id VARCHAR(50),                -- 关联用户ID（邀请送积分时的被邀请人）
    balance_after INTEGER NOT NULL,             -- 变动后的余额
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE business.point_records IS '积分变动记录表（流水表）';
COMMENT ON COLUMN business.point_records.record_id IS '记录ID';
COMMENT ON COLUMN business.point_records.user_id IS '用户ID';
COMMENT ON COLUMN business.point_records.points IS '积分变动数量（正数）';
COMMENT ON COLUMN business.point_records.change_type IS '变化类型: order_payment-订单支付, invitation_reward-邀请奖励, register_reward-注册奖励';
COMMENT ON COLUMN business.point_records.change_reason IS '变化说明';
COMMENT ON COLUMN business.point_records.related_order_id IS '关联订单ID';
COMMENT ON COLUMN business.point_records.related_user_id IS '关联用户ID';
COMMENT ON COLUMN business.point_records.balance_after IS '变动后余额';
COMMENT ON COLUMN business.point_records.created_at IS '创建时间';

-- ============================================================================
-- 3. 创建索引
-- ============================================================================

-- 用户积分余额表索引
CREATE INDEX IF NOT EXISTS idx_user_points_updated_at ON business.user_points(updated_at);

-- 积分记录表索引
CREATE INDEX IF NOT EXISTS idx_point_records_user_id ON business.point_records(user_id);
CREATE INDEX IF NOT EXISTS idx_point_records_change_type ON business.point_records(change_type);
CREATE INDEX IF NOT EXISTS idx_point_records_created_at ON business.point_records(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_point_records_order_id ON business.point_records(related_order_id);
CREATE INDEX IF NOT EXISTS idx_point_records_related_user_id ON business.point_records(related_user_id);

-- ============================================================================
-- 4. 创建视图
-- ============================================================================

-- 积分统计视图
CREATE OR REPLACE VIEW business.v_points_statistics AS
SELECT
    pr.change_type,
    COUNT(*) as record_count,
    SUM(pr.points) as total_points
FROM business.point_records pr
GROUP BY pr.change_type;

COMMENT ON VIEW business.v_points_statistics IS '积分统计视图';

-- ============================================================================
-- 5. 验证创建结果
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE '积分表重建完成！';
    RAISE NOTICE '========================================';
    RAISE NOTICE '创建的对象:';
    RAISE NOTICE '- 表: business.user_points (积分余额表)';
    RAISE NOTICE '- 表: business.point_records (积分变动记录表)';
    RAISE NOTICE '- 索引: 6个索引';
    RAISE NOTICE '- 视图: business.v_points_statistics';
    RAISE NOTICE '========================================';
END $$;
