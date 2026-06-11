-- 用户个人中心功能迁移
-- 执行时间: 2025-01-19

-- 创建用户隐私设置表
CREATE TABLE IF NOT EXISTS business.user_privacy_settings (
    user_id VARCHAR(50) PRIMARY KEY REFERENCES business.users(user_id) ON DELETE CASCADE,
    show_phone BOOLEAN DEFAULT FALSE,
    show_member_info BOOLEAN DEFAULT FALSE,
    allow_search BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE business.user_privacy_settings IS '用户隐私设置表';
COMMENT ON COLUMN business.user_privacy_settings.user_id IS '用户ID';
COMMENT ON COLUMN business.user_privacy_settings.show_phone IS '是否公开手机号';
COMMENT ON COLUMN business.user_privacy_settings.show_member_info IS '是否公开会员信息';
COMMENT ON COLUMN business.user_privacy_settings.allow_search IS '是否允许通过手机号搜索';
COMMENT ON COLUMN business.user_privacy_settings.created_at IS '创建时间';
COMMENT ON COLUMN business.user_privacy_settings.updated_at IS '更新时间';

-- 为现有用户创建默认隐私设置
INSERT INTO business.user_privacy_settings (user_id)
SELECT user_id FROM business.users
ON CONFLICT (user_id) DO NOTHING;

-- 创建索引以提升查询性能
CREATE INDEX IF NOT EXISTS idx_users_phone ON business.users(phone) WHERE phone IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_nickname ON business.users(nickname) WHERE nickname IS NOT NULL;
