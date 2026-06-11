-- =====================================================
-- 税务知识文档 remark 字段迁移
-- 将 remark 从 json_content 中提取为独立列
-- =====================================================

-- 1. 添加 remark 列
ALTER TABLE business.tax_knowledge_documents
ADD COLUMN IF NOT EXISTS remark TEXT;

COMMENT ON COLUMN business.tax_knowledge_documents.remark IS '备注摘要内容（从 json_content 提取）';

-- 2. 创建索引以支持 remark 搜索
CREATE INDEX IF NOT EXISTS idx_tax_knowledge_remark
ON business.tax_knowledge_documents(remark);

-- 3. 迁移现有数据：从 json_content 提取 remark
UPDATE business.tax_knowledge_documents
SET remark = json_content->>'remark'
WHERE json_content IS NOT NULL
  AND json_content->>'remark' IS NOT NULL
  AND remark IS NULL;

-- 4. 创建触发器函数：当 json_content 中的 remark 更新时，同步更新 remark 列
CREATE OR REPLACE FUNCTION business.sync_tax_knowledge_remark()
RETURNS TRIGGER AS $$
BEGIN
    -- 从 json_content 中提取 remark 并同步到 remark 列
    NEW.remark = NEW.json_content->>'remark';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 5. 创建触发器
DROP TRIGGER IF EXISTS trigger_sync_tax_knowledge_remark ON business.tax_knowledge_documents;
CREATE TRIGGER trigger_sync_tax_knowledge_remark
    BEFORE INSERT OR UPDATE OF json_content ON business.tax_knowledge_documents
    FOR EACH ROW
    WHEN (NEW.json_content IS NOT NULL)
    EXECUTE FUNCTION business.sync_tax_knowledge_remark();
