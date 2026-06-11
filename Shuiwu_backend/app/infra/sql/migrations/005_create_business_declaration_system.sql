-- 个体户工商申报系统
-- Migration: 005_create_business_declaration_system.sql

-- 创建个体户工商申报表
CREATE TABLE IF NOT EXISTS business.business_declarations (
    id SERIAL PRIMARY KEY,
    declaration_no VARCHAR(50) UNIQUE NOT NULL,  -- 申报单号：BD + YYYYMMDD + 6位序号

    -- 用户信息
    user_id VARCHAR(100) NOT NULL,

    -- 个体户基本信息
    business_name VARCHAR(200) NOT NULL,  -- 个体户名称
    business_license_no VARCHAR(50),  -- 营业执照号
    business_address VARCHAR(500),  -- 经营地址
    business_type VARCHAR(50),  -- 经营类型（零售、餐饮、服务等）
    business_scope TEXT,  -- 经营范围

    -- 负责人信息
    operator_name VARCHAR(100) NOT NULL,  -- 经营者姓名
    operator_id_card VARCHAR(20),  -- 身份证号
    operator_phone VARCHAR(20) NOT NULL,  -- 联系电话

    -- 申报类型
    declaration_type VARCHAR(50) NOT NULL,  -- 申报类型
    -- annual_report: 年报
    -- change_registration: 变更登记
    -- deregistration: 注销登记
    -- tax_registration: 税务登记
    -- invoice_application: 发票申请

    -- 申报数据 (JSONB格式)
    declaration_info JSONB,  -- 申报详细信息
    -- 年报示例: {"annual_revenue": 100000, "profit": 20000, "employees": 2}
    -- 变更示例: {"change_type": "address", "old_value": "...", "new_value": "..."}
    -- 注销示例: {"deregistration_reason": "...", "creditor_clearance": true}

    attachments JSONB,  -- 附件信息
    -- [{"file_name": "营业执照.pdf", "file_id": "xxx", "upload_time": "..."}]

    -- 管理员处理结果
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- pending: 待处理
    -- processing: 处理中
    -- completed: 已完成
    -- rejected: 已拒绝
    -- need_supplement: 需要补充材料

    -- 申报结果
    approval_no VARCHAR(100),  -- 受理号
    approval_date DATE,  -- 受理日期
    approval_proof_url VARCHAR(500),  -- 批准凭证URL

    process_result TEXT,  -- 处理结果说明
    process_notes TEXT,  -- 处理备注

    -- 管理员信息
    processed_by VARCHAR(100),  -- 处理人ID
    processed_at TIMESTAMP,  -- 处理时间

    -- 用户备注
    user_remarks TEXT,  -- 用户备注

    -- 时间戳
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_business_declarations_user_id ON business.business_declarations(user_id);
CREATE INDEX IF NOT EXISTS idx_business_declarations_status ON business.business_declarations(status);
CREATE INDEX IF NOT EXISTS idx_business_declarations_type ON business.business_declarations(declaration_type);
CREATE INDEX IF NOT EXISTS idx_business_declarations_no ON business.business_declarations(declaration_no);
CREATE INDEX IF NOT EXISTS idx_business_declarations_created_at ON business.business_declarations(created_at DESC);

-- 添加注释
COMMENT ON TABLE business.business_declarations IS '个体户工商申报表';
COMMENT ON COLUMN business.business_declarations.declaration_no IS '申报单号：BD + YYYYMMDD + 6位序号';
COMMENT ON COLUMN business.business_declarations.declaration_type IS '申报类型：annual_report年报, change_registration变更登记, deregistration注销登记, tax_registration税务登记, invoice_application发票申请';
COMMENT ON COLUMN business.business_declarations.status IS '状态：pending待处理, processing处理中, completed已完成, rejected已拒绝, need_supplement需要补充材料';
COMMENT ON COLUMN business.business_declarations.declaration_info IS '申报详细信息（JSONB格式）';
COMMENT ON COLUMN business.business_declarations.attachments IS '附件信息（JSONB数组）';

-- 创建自动更新 updated_at 触发器
CREATE OR REPLACE FUNCTION update_business_declarations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_business_declarations_updated_at ON business.business_declarations;
CREATE TRIGGER trigger_update_business_declarations_updated_at
    BEFORE UPDATE ON business.business_declarations
    FOR EACH ROW
    EXECUTE FUNCTION update_business_declarations_updated_at();
