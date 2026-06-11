-- 修复全景报告表的 user_id 字段类型
-- 从 bigint 改为 varchar(50) 以匹配用户表

-- 1. 删除旧的索引
DROP INDEX IF EXISTS business.idx_panoramic_reports_user_id;

-- 2. 修改列类型
ALTER TABLE business.panoramic_reports
    ALTER COLUMN user_id TYPE varchar(50);

-- 3. 重新创建索引
CREATE INDEX IF NOT EXISTS idx_panoramic_reports_user_id ON business.panoramic_reports(user_id);

-- 4. 添加注释
COMMENT ON COLUMN business.panoramic_reports.user_id IS '用户ID（字符串格式）';
