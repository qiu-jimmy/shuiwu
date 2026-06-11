-- 为knowledge_base_registry表添加is_system字段
-- 执行时间: 2026-01-13

ALTER TABLE knowledge.knowledge_base_registry ADD COLUMN IF NOT EXISTS is_system BOOLEAN DEFAULT FALSE;

-- 添加索引
CREATE INDEX IF NOT EXISTS idx_knowledge_base_registry_is_system ON knowledge.knowledge_base_registry(is_system);

COMMENT ON COLUMN knowledge.knowledge_base_registry.is_system IS '是否为系统知识库（true=系统知识库，false=用户知识库）';
