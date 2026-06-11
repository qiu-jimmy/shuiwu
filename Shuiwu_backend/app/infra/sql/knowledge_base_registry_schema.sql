-- 知识库注册表 Schema
-- 用于存储知识库与类型的关联关系，支持通过类型筛选知识库

-- 添加知识库注册表
CREATE TABLE IF NOT EXISTS knowledge.knowledge_base_registry (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(255) NOT NULL UNIQUE, -- 知识库表名，格式: kb_{user_id}_{kb_name}
    kb_name VARCHAR(255) NOT NULL, -- 知识库名称
    user_id VARCHAR(100) NOT NULL, -- 用户ID
    type_id VARCHAR(50), -- 知识库类型ID，关联 knowledge_types.type_id
    description TEXT, -- 知识库描述
    chunking_rule VARCHAR(50) DEFAULT 'fixed_size', -- 分块规则
    chunk_size INTEGER DEFAULT 5000, -- 分块大小
    chunk_overlap INTEGER DEFAULT 200, -- 分块重叠
    embedder_model VARCHAR(100) DEFAULT 'text-embedding-3-small', -- 嵌入模型
    status VARCHAR(20) DEFAULT 'active', -- 状态: active-有效, inactive-无效, deleted-已删除
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP, -- 软删除时间
    CONSTRAINT fk_type FOREIGN KEY (type_id) REFERENCES knowledge.knowledge_types(type_id) ON DELETE SET NULL
);

COMMENT ON TABLE knowledge.knowledge_base_registry IS '知识库注册表，存储知识库元信息与类型关联';
COMMENT ON COLUMN knowledge.knowledge_base_registry.table_name IS '知识库表名，格式: kb_{user_id}_{kb_name}';
COMMENT ON COLUMN knowledge.knowledge_base_registry.kb_name IS '知识库名称';
COMMENT ON COLUMN knowledge.knowledge_base_registry.user_id IS '用户ID';
COMMENT ON COLUMN knowledge.knowledge_base_registry.type_id IS '知识库类型ID';
COMMENT ON COLUMN knowledge.knowledge_base_registry.description IS '知识库描述';
COMMENT ON COLUMN knowledge.knowledge_base_registry.chunking_rule IS '分块规则';
COMMENT ON COLUMN knowledge.knowledge_base_registry.chunk_size IS '分块大小';
COMMENT ON COLUMN knowledge.knowledge_base_registry.chunk_overlap IS '分块重叠';
COMMENT ON COLUMN knowledge.knowledge_base_registry.embedder_model IS '嵌入模型';
COMMENT ON COLUMN knowledge.knowledge_base_registry.status IS '状态: active-有效, inactive-无效, deleted-已删除';
COMMENT ON COLUMN knowledge.knowledge_base_registry.created_at IS '创建时间';
COMMENT ON COLUMN knowledge.knowledge_base_registry.updated_at IS '更新时间';
COMMENT ON COLUMN knowledge.knowledge_base_registry.deleted_at IS '软删除时间';

-- ============================================================================
-- 索引
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_knowledge_base_registry_table_name ON knowledge.knowledge_base_registry(table_name);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_registry_user_id ON knowledge.knowledge_base_registry(user_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_registry_type_id ON knowledge.knowledge_base_registry(type_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_registry_status ON knowledge.knowledge_base_registry(status);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_registry_user_type ON knowledge.knowledge_base_registry(user_id, type_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_registry_deleted_at ON knowledge.knowledge_base_registry(deleted_at);

-- 创建唯一索引：同一用户下知识库名称唯一
CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_base_registry_user_kb_name
ON knowledge.knowledge_base_registry(user_id, kb_name)
WHERE deleted_at IS NULL;
