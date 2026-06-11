-- 为 knowledge_base_registry 表添加 document_ids 字段
-- 用于存储已成功导入RAG的文件ID列表
-- 执行时间: 2026-01-20

-- 添加 document_ids 数组字段
ALTER TABLE knowledge.knowledge_base_registry
ADD COLUMN IF NOT EXISTS document_ids JSONB DEFAULT '[]'::jsonb;

-- 添加索引（用于查询包含特定文件ID的知识库）
CREATE INDEX IF NOT EXISTS idx_knowledge_base_registry_document_ids
ON knowledge.knowledge_base_registry USING GIN(document_ids);

-- 添加注释
COMMENT ON COLUMN knowledge.knowledge_base_registry.document_ids IS '已导入的文档ID列表，格式: [{"file_id": "xxx", "filename": "xxx", "created_at": "2026-01-20T10:00:00"}]';
