-- 创建智能报税系统表
-- 执行时间: 2026-01-20

-- ============================================================================
-- 1. 报税申报主表
-- ============================================================================

CREATE TABLE IF NOT EXISTS business.tax_declarations (
    id BIGSERIAL PRIMARY KEY,
    declaration_no VARCHAR(50) UNIQUE NOT NULL,     -- 申报单号
    user_id VARCHAR(50) NOT NULL,                   -- 用户ID

    -- 纳税人基本信息
    taxpayer_name VARCHAR(100) NOT NULL,            -- 纳税人姓名
    taxpayer_id_card VARCHAR(20),                   -- 身份证号
    taxpayer_phone VARCHAR(20),                     -- 联系电话
    taxpayer_type VARCHAR(20) DEFAULT 'individual',  -- 纳税人类型: individual-个人, enterprise-企业

    -- 税种信息
    tax_type VARCHAR(50) NOT NULL,                  -- 税种: vat-增值税, pit-个人所得税, cit-企业所得税, etc.
    tax_period VARCHAR(20) NOT NULL,                -- 税期: 2024Q1, 2024-01, etc.

    -- 收入信息 (JSONB格式，灵活存储不同税种的数据)
    income_info JSONB,                              -- 收入信息

    -- 扣除信息
    deduction_info JSONB,                           -- 扣除信息

    -- 计算结果
    total_income DECIMAL(15,2) DEFAULT 0,           -- 收入总额
    total_deduction DECIMAL(15,2) DEFAULT 0,         -- 扣除总额
    taxable_income DECIMAL(15,2) DEFAULT 0,         -- 应纳税所得额
    tax_amount DECIMAL(15,2) DEFAULT 0,             -- 应纳税额
    tax_paid DECIMAL(15,2) DEFAULT 0,               -- 已缴税额
    tax_refund DECIMAL(15,2) DEFAULT 0,             -- 应退税额

    -- 状态管理
    status VARCHAR(20) DEFAULT 'pending',           -- 状态: pending-待处理, processing-处理中, completed-已完成, rejected-已拒绝
    process_result TEXT,                            -- 处理结果说明

    -- 申报信息
    declaration_serial_no VARCHAR(100),             -- 税务局申报流水号
    declaration_date TIMESTAMP,                      -- 申报日期
    declaration_proof_url VARCHAR(500),              -- 申报凭证URL

    -- 管理员处理信息
    processed_by VARCHAR(50),                       -- 处理人ID
    processed_at TIMESTAMP,                         -- 处理时间
    process_notes TEXT,                             -- 处理备注

    -- 用户备注
    user_remarks TEXT,                              -- 用户备注

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 外键
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES business.users(user_id)
);

-- ============================================================================
-- 2. 索引
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_tax_declarations_user_id ON business.tax_declarations(user_id);
CREATE INDEX IF NOT EXISTS idx_tax_declarations_status ON business.tax_declarations(status);
CREATE INDEX IF NOT EXISTS idx_tax_declarations_tax_type ON business.tax_declarations(tax_type);
CREATE INDEX IF NOT EXISTS idx_tax_declarations_tax_period ON business.tax_declarations(tax_period);
CREATE INDEX IF NOT EXISTS idx_tax_declarations_created_at ON business.tax_declarations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tax_declarations_user_status ON business.tax_declarations(user_id, status);

-- 复合索引：管理员查询用
CREATE INDEX IF NOT EXISTS idx_tax_declarations_status_created ON business.tax_declarations(status, created_at DESC);

-- ============================================================================
-- 3. 表注释
-- ============================================================================

COMMENT ON TABLE business.tax_declarations IS '智能报税申报表';
COMMENT ON COLUMN business.tax_declarations.id IS '主键ID';
COMMENT ON COLUMN business.tax_declarations.declaration_no IS '申报单号（唯一）';
COMMENT ON COLUMN business.tax_declarations.user_id IS '用户ID';
COMMENT ON COLUMN business.tax_declarations.taxpayer_name IS '纳税人姓名';
COMMENT ON COLUMN business.tax_declarations.taxpayer_id_card IS '身份证号';
COMMENT ON COLUMN business.tax_declarations.taxpayer_phone IS '联系电话';
COMMENT ON COLUMN business.tax_declarations.taxpayer_type IS '纳税人类型: individual-个人, enterprise-企业';
COMMENT ON COLUMN business.tax_declarations.tax_type IS '税种: vat-增值税, pit-个人所得税, cit-企业所得税';
COMMENT ON COLUMN business.tax_declarations.tax_period IS '税期: 2024Q1, 2024-01';
COMMENT ON COLUMN business.tax_declarations.income_info IS '收入信息（JSONB格式）';
COMMENT ON COLUMN business.tax_declarations.deduction_info IS '扣除信息（JSONB格式）';
COMMENT ON COLUMN business.tax_declarations.total_income IS '收入总额';
COMMENT ON COLUMN business.tax_declarations.total_deduction IS '扣除总额';
COMMENT ON COLUMN business.tax_declarations.taxable_income IS '应纳税所得额';
COMMENT ON COLUMN business.tax_declarations.tax_amount IS '应纳税额';
COMMENT ON COLUMN business.tax_declarations.tax_paid IS '已缴税额';
COMMENT ON COLUMN business.tax_declarations.tax_refund IS '应退税额';
COMMENT ON COLUMN business.tax_declarations.status IS '状态: pending-待处理, processing-处理中, completed-已完成, rejected-已拒绝';
COMMENT ON COLUMN business.tax_declarations.process_result IS '处理结果说明';
COMMENT ON COLUMN business.tax_declarations.declaration_serial_no IS '税务局申报流水号';
COMMENT ON COLUMN business.tax_declarations.declaration_date IS '申报日期';
COMMENT ON COLUMN business.tax_declarations.declaration_proof_url IS '申报凭证URL';
COMMENT ON COLUMN business.tax_declarations.processed_by IS '处理人ID（管理员）';
COMMENT ON COLUMN business.tax_declarations.processed_at IS '处理时间';
COMMENT ON COLUMN business.tax_declarations.process_notes IS '处理备注';
COMMENT ON COLUMN business.tax_declarations.user_remarks IS '用户备注';

-- ============================================================================
-- 4. 触发器：自动更新 updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION business.update_tax_declarations_updated_at()
RETURNS TRIGGER AS '
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
' LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_tax_declarations_updated_at
    BEFORE UPDATE ON business.tax_declarations
    FOR EACH ROW
    EXECUTE FUNCTION business.update_tax_declarations_updated_at();

-- ============================================================================
-- 5. 初始化数据示例（可选）
-- ============================================================================

-- 插入示例数据（用于测试）
-- INSERT INTO business.tax_declarations (
--     declaration_no, user_id, taxpayer_name, taxpayer_phone,
--     tax_type, tax_period, income_info, total_income, status
-- ) VALUES (
--     'TD2026012000001', 'user_123', '张三', '13800138000',
--     'pit', '2024Q4', '{"salary": 50000, "bonus": 10000}'::jsonb,
--     60000, 'pending'
-- );
