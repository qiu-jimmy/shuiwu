-- =====================================================
-- 会员套餐扩展字段迁移
-- 添加 JSON 配置字段和权益列表字段
-- =====================================================

-- 1. 添加自定义配置 JSON 字段
ALTER TABLE business.member_packages
ADD COLUMN IF NOT EXISTS custom_config JSONB DEFAULT '{}';

COMMENT ON COLUMN business.member_packages.custom_config IS '自定义配置（JSON格式），用于存储扩展字段，例如：{"max_ai_calls": 1000, "enable_feature_x": true}';

-- 2. 添加权益描述列表字段
ALTER TABLE business.member_packages
ADD COLUMN IF NOT EXISTS benefits JSONB DEFAULT '[]';

COMMENT ON COLUMN business.member_packages.benefits IS '权益描述列表（JSON数组），供前端渲染展示，例如：[{"title": "无限对话", "desc": "每日无限制聊天次数"}]';

-- 3. 创建索引以支持 JSON 字段查询
CREATE INDEX IF NOT EXISTS idx_member_packages_custom_config
ON business.member_packages USING GIN (custom_config);

CREATE INDEX IF NOT EXISTS idx_member_packages_benefits
ON business.member_packages USING GIN (benefits);

-- =====================================================
-- 示例数据更新
-- =====================================================

-- 更新免费套餐示例
UPDATE business.member_packages
SET custom_config = '{"level": "free", "priority": 0}',
    benefits = '[
        {"title": "每日10次对话", "desc": "每天可以免费使用10次AI对话"},
        {"title": "1个知识库", "desc": "支持创建1个个人知识库"},
        {"title": "10份文档", "desc": "最多可上传10份文档"}
    ]'::jsonb
WHERE package_type = 'free';

-- 更新高级套餐示例
UPDATE business.member_packages
SET custom_config = '{"level": "premium", "priority": 2, "features": ["rag", "web_search"]}',
    benefits = '[
        {"title": "无限对话", "desc": "每日无限制AI对话次数"},
        {"title": "10个知识库", "desc": "支持创建10个知识库"},
        {"title": "100份文档", "desc": "每个知识库最多100份文档"},
        {"title": "网络搜索", "desc": "支持实时网络搜索功能"},
        {"title": "RAG增强", "desc": "知识库检索增强生成"},
        {"title": "1GB存储", "desc": "云端文件存储空间"}
    ]'::jsonb
WHERE package_type = 'premium';

-- =====================================================
-- 完成迁移
-- =====================================================
