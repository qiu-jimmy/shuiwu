-- 知识库类型表 Schema
-- 用于支持创建知识库时选择知识库类型

CREATE SCHEMA IF NOT EXISTS knowledge;

-- ============================================================================
-- 知识库类型表
-- ============================================================================

CREATE TABLE IF NOT EXISTS knowledge.knowledge_types (
    type_id VARCHAR(50) PRIMARY KEY,
    type_name VARCHAR(100) NOT NULL UNIQUE,
    type_code VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    icon VARCHAR(255),
    sort_order INTEGER DEFAULT 0,
    is_system BOOLEAN DEFAULT true, -- 是否系统内置类型
    status VARCHAR(20) DEFAULT 'active', -- active-有效, inactive-无效
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE knowledge.knowledge_types IS '知识库类型表';
COMMENT ON COLUMN knowledge.knowledge_types.type_id IS '类型ID';
COMMENT ON COLUMN knowledge.knowledge_types.type_name IS '类型名称';
COMMENT ON COLUMN knowledge.knowledge_types.type_code IS '类型代码（英文标识）';
COMMENT ON COLUMN knowledge.knowledge_types.description IS '类型描述';
COMMENT ON COLUMN knowledge.knowledge_types.icon IS '图标URL或图标类名';
COMMENT ON COLUMN knowledge.knowledge_types.sort_order IS '排序顺序（数字越小越靠前）';
COMMENT ON COLUMN knowledge.knowledge_types.is_system IS '是否系统内置类型';
COMMENT ON COLUMN knowledge.knowledge_types.status IS '状态: active-有效, inactive-无效';
COMMENT ON COLUMN knowledge.knowledge_types.created_at IS '创建时间';
COMMENT ON COLUMN knowledge.knowledge_types.updated_at IS '更新时间';

-- ============================================================================
-- 索引
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_knowledge_types_type_code ON knowledge.knowledge_types(type_code);
CREATE INDEX IF NOT EXISTS idx_knowledge_types_status ON knowledge.knowledge_types(status);
CREATE INDEX IF NOT EXISTS idx_knowledge_types_sort_order ON knowledge.knowledge_types(sort_order);
CREATE INDEX IF NOT EXISTS idx_knowledge_types_is_system ON knowledge.knowledge_types(is_system);

-- ============================================================================
-- 初始化数据 - 插入默认知识库类型
-- ============================================================================

INSERT INTO knowledge.knowledge_types (type_id, type_name, type_code, description, icon, sort_order, is_system, status)
VALUES
    ('type_001', '税收基础知识', 'tax_basics', '包含税收基础理论、税收分类、税制结构等基础知识', 'book', 1, true, 'active'),
    ('type_002', '政策文件', 'policy_docs', '国家和地方税收政策文件、法律法规、司法解释等', 'file-text', 2, true, 'active'),
    ('type_003', '发票相关知识', 'invoice_knowledge', '发票开具、管理、抵扣等相关知识', 'receipt', 3, true, 'active'),
    ('type_004', '税务筹划', 'tax_planning', '企业税务筹划方案、案例、方法等', 'lightbulb', 4, true, 'active'),
    ('type_005', '税务会计', 'tax_accounting', '税务会计处理、核算方法、账务处理等', 'calculator', 5, true, 'active'),
    ('type_006', '税务风险', 'tax_risk', '税务风险识别、防范、应对等', 'shield', 6, true, 'active'),
    ('type_007', '税务优惠', 'tax_incentives', '各类税收优惠政策、减免政策等', 'gift', 7, true, 'active'),
    ('type_008', '税务稽查', 'tax_audit', '税务稽查相关知识、案例、应对方法等', 'search', 8, true, 'active'),
    ('type_009', '国际税收', 'international_tax', '国际税收、跨境税收、转让定价等', 'globe', 9, true, 'active'),
    ('type_010', '个人所得税', 'personal_tax', '个人所得税相关政策、计算、申报等', 'user', 10, true, 'active'),
    ('type_011', '企业所得税', 'corporate_tax', '企业所得税相关政策、计算、申报等', 'building', 11, true, 'active'),
    ('type_012', '增值税', 'vat_tax', '增值税相关政策、计算、申报等', 'percent', 12, true, 'active'),
    ('type_013', '其他税种', 'other_taxes', '消费税、营业税、印花税等其他税种相关知识', 'layers', 13, true, 'active'),
    ('type_014', '税务实务', 'tax_practice', '税务实务操作、流程、技巧等', 'tool', 14, true, 'active'),
    ('type_015', '税务问答', 'tax_qa', '常见税务问题解答、疑难问题分析等', 'help-circle', 15, true, 'active'),
    ('type_099', '自定义类型', 'custom', '用户自定义的知识库类型', 'folder', 99, true, 'active')
ON CONFLICT (type_id) DO NOTHING;
