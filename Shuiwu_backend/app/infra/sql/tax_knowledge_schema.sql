-- 税务知识文档管理系统 Schema（简化版）
-- 创建税务知识文档表
CREATE SCHEMA IF NOT EXISTS business;

-- 税务知识文档主表（单表设计）
CREATE TABLE IF NOT EXISTS business.tax_knowledge_documents (
    id SERIAL PRIMARY KEY,
    doc_id VARCHAR(50) UNIQUE NOT NULL,
    doc_type VARCHAR(50) NOT NULL,          -- 文档类型: 行业通知、税收征管法规、政策解读等
    law_id VARCHAR(100),                     -- 法规ID (如: cctaa_2017_013)
    law_name VARCHAR(500) NOT NULL,          -- 法规名称

    -- 原始内容 (Markdown 格式)
    raw_content TEXT,                        -- 原始 markdown 文档内容

    -- 清洗后的 JSON 内容 (完全匹配前端 taxKnowledge.js 结构)
    json_content JSONB,                      -- 清洗后的 JSON 格式数据

    -- 系统字段
    created_by VARCHAR(50),                  -- 创建人
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active'      -- active, deleted
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_tax_knowledge_doc_id ON business.tax_knowledge_documents(doc_id);
CREATE INDEX IF NOT EXISTS idx_tax_knowledge_doc_type ON business.tax_knowledge_documents(doc_type);
CREATE INDEX IF NOT EXISTS idx_tax_knowledge_law_id ON business.tax_knowledge_documents(law_id);
CREATE INDEX IF NOT EXISTS idx_tax_knowledge_status ON business.tax_knowledge_documents(status);
CREATE INDEX IF NOT EXISTS idx_tax_knowledge_law_name ON business.tax_knowledge_documents(law_name);

-- 添加注释
COMMENT ON TABLE business.tax_knowledge_documents IS '税务知识文档表';
COMMENT ON COLUMN business.tax_knowledge_documents.doc_id IS '文档唯一ID';
COMMENT ON COLUMN business.tax_knowledge_documents.doc_type IS '文档类型';
COMMENT ON COLUMN business.tax_knowledge_documents.law_id IS '法规ID';
COMMENT ON COLUMN business.tax_knowledge_documents.law_name IS '法规名称';
COMMENT ON COLUMN business.tax_knowledge_documents.raw_content IS '原始markdown内容';
COMMENT ON COLUMN business.tax_knowledge_documents.json_content IS '清洗后的JSON内容(匹配前端结构)';
COMMENT ON COLUMN business.tax_knowledge_documents.created_by IS '创建人';
COMMENT ON COLUMN business.tax_knowledge_documents.status IS '状态: active-有效, deleted-已删除';

-- 创建触发器函数: 自动更新 updated_at
CREATE OR REPLACE FUNCTION business.update_tax_knowledge_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为 tax_knowledge_documents 表创建触发器
DROP TRIGGER IF EXISTS trigger_tax_knowledge_updated_at ON business.tax_knowledge_documents;
CREATE TRIGGER trigger_tax_knowledge_updated_at
    BEFORE UPDATE ON business.tax_knowledge_documents
    FOR EACH ROW
    EXECUTE FUNCTION business.update_tax_knowledge_updated_at();
