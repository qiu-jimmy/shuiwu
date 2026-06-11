-- ============================================================================
-- 问题反馈系统表结构
-- ============================================================================

-- 问题反馈表
CREATE TABLE IF NOT EXISTS business.user_feedback (
    feedback_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES business.users(user_id),

    -- 反馈内容
    feedback_type VARCHAR(50) NOT NULL,  -- 问题类型（前端写死）：bug, feature, complaint, other
    feedback_content TEXT NOT NULL,  -- 问题描述
    feedback_images JSONB,  -- 反馈图片数组（可选）

    -- 管理员回复
    admin_reply TEXT,  -- 管理员回复内容
    admin_id VARCHAR(50) REFERENCES business.users(user_id),  -- 处理管理员ID
    replied_at TIMESTAMP,  -- 回复时间

    -- 状态
    status VARCHAR(20) DEFAULT 'pending',  -- pending-待处理, processing-处理中, resolved-已解决, closed-已关闭

    -- 优先级（管理员可设置）
    priority VARCHAR(20) DEFAULT 'normal',  -- low-低, normal-中, high-高, urgent-紧急

    -- 时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE business.user_feedback IS '用户问题反馈表';
COMMENT ON COLUMN business.user_feedback.feedback_id IS '反馈ID';
COMMENT ON COLUMN business.user_feedback.user_id IS '用户ID';
COMMENT ON COLUMN business.user_feedback.feedback_type IS '问题类型: bug-系统错误, feature-功能建议, complaint-投诉, other-其他';
COMMENT ON COLUMN business.user_feedback.feedback_content IS '问题描述';
COMMENT ON COLUMN business.user_feedback.feedback_images IS '反馈图片（JSON数组）';
COMMENT ON COLUMN business.user_feedback.admin_reply IS '管理员回复内容';
COMMENT ON COLUMN business.user_feedback.admin_id IS '处理管理员ID';
COMMENT ON COLUMN business.user_feedback.replied_at IS '回复时间';
COMMENT ON COLUMN business.user_feedback.status IS '状态: pending-待处理, processing-处理中, resolved-已解决, closed-已关闭';
COMMENT ON COLUMN business.user_feedback.priority IS '优先级: low-低, normal-中, high-高, urgent-紧急';
COMMENT ON COLUMN business.user_feedback.created_at IS '创建时间';
COMMENT ON COLUMN business.user_feedback.updated_at IS '更新时间';

-- ============================================================================
-- 创建索引
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON business.user_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_status ON business.user_feedback(status);
CREATE INDEX IF NOT EXISTS idx_feedback_type ON business.user_feedback(feedback_type);
CREATE INDEX IF NOT EXISTS idx_feedback_priority ON business.user_feedback(priority);
CREATE INDEX IF NOT EXISTS idx_feedback_admin_id ON business.user_feedback(admin_id);
CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON business.user_feedback(created_at);
CREATE INDEX IF NOT EXISTS idx_feedback_updated_at ON business.user_feedback(updated_at);

-- 复合索引：用户反馈查询
CREATE INDEX IF NOT EXISTS idx_feedback_user_status ON business.user_feedback(user_id, status);
CREATE INDEX IF NOT EXISTS idx_feedback_status_created ON business.user_feedback(status, created_at DESC);

-- ============================================================================
-- 创建视图（管理员统计用）
-- ============================================================================

CREATE OR REPLACE VIEW business.v_feedback_stats AS
SELECT
    status,
    priority,
    COUNT(*) as count
FROM business.user_feedback
GROUP BY status, priority;

COMMENT ON VIEW business.v_feedback_stats IS '问题反馈统计视图';
