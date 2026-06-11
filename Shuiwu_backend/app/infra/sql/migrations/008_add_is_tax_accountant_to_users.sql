-- 添加 is_tax_accountant 字段到 users 表
-- 执行时间: 2026-02-02

-- 添加 is_tax_accountant 字段（标记用户是否是认证税务师）
ALTER TABLE business.users
ADD COLUMN IF NOT EXISTS is_tax_accountant BOOLEAN DEFAULT false;

-- 添加字段注释
COMMENT ON COLUMN business.users.is_tax_accountant IS '是否是认证税务师: true-是, false-否';

-- 创建索引（用于查询税务师用户）
CREATE INDEX IF NOT EXISTS idx_users_is_tax_accountant ON business.users(is_tax_accountant);
