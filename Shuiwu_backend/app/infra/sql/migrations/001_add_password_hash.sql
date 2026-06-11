-- 为users表添加password_hash字段
-- 执行时间: 2025-01-12

ALTER TABLE business.users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);

-- 添加索引
CREATE INDEX IF NOT EXISTS idx_users_password_hash ON business.users(password_hash);

COMMENT ON COLUMN business.users.password_hash IS '密码哈希值（bcrypt加密）';
