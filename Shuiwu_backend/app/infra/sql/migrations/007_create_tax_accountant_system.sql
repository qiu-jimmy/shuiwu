-- 创建税务师入驻模块的表
-- 执行时间: 2026-02-02

-- 税务师申请表
CREATE TABLE IF NOT EXISTS business.tax_accountant_applications (
    application_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    real_name VARCHAR(100) NOT NULL,
    birth_date DATE,  -- 出生日期
    id_card VARCHAR(20) NOT NULL,
    address VARCHAR(500),  -- 现住地
    phone VARCHAR(20) NOT NULL,
    certificate_number VARCHAR(100) NOT NULL,
    certificate_date DATE,  -- 证书取得时间
    certificate_images TEXT[],  -- 证书图片URL列表
    signature_image TEXT,  -- 签字确认图片URL
    work_experiences JSONB,  -- 工作经历JSON数组
    specialty_area VARCHAR(100)[],  -- 专长领域
    introduction TEXT,  -- 个人简介
    additional_info TEXT,  -- 补充说明
    has_settled BOOLEAN DEFAULT false,  -- 是否已入驻其他平台
    status VARCHAR(20) DEFAULT 'pending',  -- pending, approved, rejected
    reject_reason TEXT,  -- 拒绝原因
    reviewed_by VARCHAR(50),  -- 审核人ID
    reviewed_at TIMESTAMP,  -- 审核时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES business.users(user_id) ON DELETE CASCADE
);

-- 税务师信息表（审核通过的税务师）
CREATE TABLE IF NOT EXISTS business.tax_accountants (
    accountant_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) UNIQUE NOT NULL,
    application_id VARCHAR(50) UNIQUE NOT NULL,
    real_name VARCHAR(100) NOT NULL,
    birth_date DATE,  -- 出生日期
    id_card VARCHAR(20) NOT NULL,
    address VARCHAR(500),  -- 现住地
    phone VARCHAR(20) NOT NULL,
    certificate_number VARCHAR(100) NOT NULL,
    certificate_date DATE,  -- 证书取得时间
    signature_image TEXT,  -- 签字确认图片URL
    work_experiences JSONB,  -- 工作经历JSON数组
    specialty_area VARCHAR(100)[],  -- 专长领域
    introduction TEXT,  -- 个人简介
    additional_info TEXT,  -- 补充说明
    status VARCHAR(20) DEFAULT 'active',  -- active, suspended
    service_count INTEGER DEFAULT 0,  -- 服务次数
    rating DECIMAL(3,2) DEFAULT 0.00,  -- 评分
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_ta_user FOREIGN KEY (user_id) REFERENCES business.users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_ta_application FOREIGN KEY (application_id) REFERENCES business.tax_accountant_applications(application_id) ON DELETE CASCADE
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_tax_applications_user_id ON business.tax_accountant_applications(user_id);
CREATE INDEX IF NOT EXISTS idx_tax_applications_status ON business.tax_accountant_applications(status);
CREATE INDEX IF NOT EXISTS idx_tax_applications_created_at ON business.tax_accountant_applications(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_tax_accountants_user_id ON business.tax_accountants(user_id);
CREATE INDEX IF NOT EXISTS idx_tax_accountants_status ON business.tax_accountants(status);
CREATE INDEX IF NOT EXISTS idx_tax_accountants_rating ON business.tax_accountants(rating DESC);

-- 添加表注释
COMMENT ON TABLE business.tax_accountant_applications IS '税务师申请表';
COMMENT ON TABLE business.tax_accountants IS '税务师信息表';

-- 添加列注释
COMMENT ON COLUMN business.tax_accountant_applications.application_id IS '申请ID';
COMMENT ON COLUMN business.tax_accountant_applications.real_name IS '真实姓名';
COMMENT ON COLUMN business.tax_accountant_applications.birth_date IS '出生日期';
COMMENT ON COLUMN business.tax_accountant_applications.id_card IS '身份证号';
COMMENT ON COLUMN business.tax_accountant_applications.address IS '现住地';
COMMENT ON COLUMN business.tax_accountant_applications.phone IS '联系电话';
COMMENT ON COLUMN business.tax_accountant_applications.certificate_number IS '税务师职业资格证书编号';
COMMENT ON COLUMN business.tax_accountant_applications.certificate_date IS '证书取得时间';
COMMENT ON COLUMN business.tax_accountant_applications.certificate_images IS '证书图片URL数组';
COMMENT ON COLUMN business.tax_accountant_applications.signature_image IS '签字确认图片URL';
COMMENT ON COLUMN business.tax_accountant_applications.work_experiences IS '工作经历JSON数组，包含开始时间、结束时间、工作单位、职务、工作内容';
COMMENT ON COLUMN business.tax_accountant_applications.status IS '申请状态: pending-待审核, approved-已通过, rejected-已拒绝';
COMMENT ON COLUMN business.tax_accountant_applications.specialty_area IS '专长领域数组';
COMMENT ON COLUMN business.tax_accountant_applications.introduction IS '个人简介';
COMMENT ON COLUMN business.tax_accountant_applications.additional_info IS '补充说明';
COMMENT ON COLUMN business.tax_accountant_applications.has_settled IS '是否已入驻其他平台';

COMMENT ON COLUMN business.tax_accountants.accountant_id IS '税务师ID';
COMMENT ON COLUMN business.tax_accountants.service_count IS '服务次数';
COMMENT ON COLUMN business.tax_accountants.rating IS '评分(0-5)';
