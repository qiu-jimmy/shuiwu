-- 业务数据库Schema设计 (DrawDB兼容版本)
-- 使用显式外键约束，确保DrawDB等工具能正确识别表关系

-- ============================================================================
-- 创建业务数据库schema
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS business;

-- ============================================================================
-- 1. 用户管理模块
-- ============================================================================

-- 用户表
CREATE TABLE IF NOT EXISTS business.users (
    user_id VARCHAR(50) PRIMARY KEY,
    wx_openid VARCHAR(100) UNIQUE,
    wx_unionid VARCHAR(100),
    phone VARCHAR(20) UNIQUE,
    nickname VARCHAR(100),
    avatar_url TEXT,
    password_hash VARCHAR(255),
    status VARCHAR(20) DEFAULT 'normal',
    user_type VARCHAR(20) DEFAULT 'individual',
    member_level VARCHAR(20) DEFAULT 'free',
    member_expire_at TIMESTAMP,
    register_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE business.users IS '用户表';
COMMENT ON COLUMN business.users.user_id IS '用户ID';
COMMENT ON COLUMN business.users.wx_openid IS '微信OpenID';
COMMENT ON COLUMN business.users.wx_unionid IS '微信UnionID';
COMMENT ON COLUMN business.users.phone IS '手机号';
COMMENT ON COLUMN business.users.nickname IS '昵称';
COMMENT ON COLUMN business.users.avatar_url IS '头像URL';
COMMENT ON COLUMN business.users.password_hash IS '密码哈希值（bcrypt加密）';
COMMENT ON COLUMN business.users.status IS '用户状态: normal-正常, disabled-禁用, banned-封禁, pending_review-待审核';
COMMENT ON COLUMN business.users.user_type IS '用户类型: individual-个人, enterprise-企业';
COMMENT ON COLUMN business.users.member_level IS '会员等级: free-免费, vip-VIP, premium-高级, enterprise-企业';
COMMENT ON COLUMN business.users.member_expire_at IS '会员到期时间';
COMMENT ON COLUMN business.users.register_time IS '注册时间';
COMMENT ON COLUMN business.users.last_login_time IS '最后登录时间';
COMMENT ON COLUMN business.users.created_at IS '创建时间';
COMMENT ON COLUMN business.users.updated_at IS '更新时间';

-- 用户标签表
CREATE TABLE IF NOT EXISTS business.user_tags (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    tag_name VARCHAR(50) NOT NULL,
    tag_type VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, tag_name),
    CONSTRAINT fk_user_tags_user FOREIGN KEY (user_id)
        REFERENCES business.users(user_id)
        ON DELETE CASCADE
);

COMMENT ON TABLE business.user_tags IS '用户标签表';
COMMENT ON COLUMN business.user_tags.id IS '主键ID';
COMMENT ON COLUMN business.user_tags.user_id IS '用户ID';
COMMENT ON COLUMN business.user_tags.tag_name IS '标签名称';
COMMENT ON COLUMN business.user_tags.tag_type IS '标签类型: system-系统标签, custom-自定义标签';
COMMENT ON COLUMN business.user_tags.created_at IS '创建时间';

-- 微信登录记录表
CREATE TABLE IF NOT EXISTS business.wx_login_logs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50),
    wx_openid VARCHAR(100),
    login_type VARCHAR(20),
    ip_address VARCHAR(50),
    user_agent TEXT,
    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_wx_login_logs_user FOREIGN KEY (user_id)
        REFERENCES business.users(user_id)
        ON DELETE SET NULL
);

COMMENT ON TABLE business.wx_login_logs IS '微信登录记录表';
COMMENT ON COLUMN business.wx_login_logs.id IS '主键ID';
COMMENT ON COLUMN business.wx_login_logs.user_id IS '用户ID';
COMMENT ON COLUMN business.wx_login_logs.wx_openid IS '微信OpenID';
COMMENT ON COLUMN business.wx_login_logs.login_type IS '登录类型: login-登录, register-注册';
COMMENT ON COLUMN business.wx_login_logs.ip_address IS 'IP地址';
COMMENT ON COLUMN business.wx_login_logs.user_agent IS '用户代理';
COMMENT ON COLUMN business.wx_login_logs.login_time IS '登录时间';

-- ============================================================================
-- 2. 会员订阅模块
-- ============================================================================

-- 会员套餐表
CREATE TABLE IF NOT EXISTS business.member_packages (
    package_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    package_type VARCHAR(20),
    price DECIMAL(10,2) NOT NULL,
    original_price DECIMAL(10,2),
    duration_days INTEGER,
    max_daily_chats INTEGER DEFAULT -1,
    max_kb_count INTEGER DEFAULT 5,
    max_kb_documents INTEGER DEFAULT 100,
    max_file_storage_mb INTEGER DEFAULT 1024,
    max_file_count INTEGER DEFAULT 100,
    enable_rag BOOLEAN DEFAULT true,
    enable_web_search BOOLEAN DEFAULT false,
    enable_mcp_tools BOOLEAN DEFAULT false,
    status VARCHAR(20) DEFAULT 'active',
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE business.member_packages IS '会员套餐表';
COMMENT ON COLUMN business.member_packages.package_id IS '套餐ID';
COMMENT ON COLUMN business.member_packages.name IS '套餐名称';
COMMENT ON COLUMN business.member_packages.description IS '套餐描述';
COMMENT ON COLUMN business.member_packages.package_type IS '套餐类型: month-月卡, quarter-季卡, year-年卡, lifetime-终身';
COMMENT ON COLUMN business.member_packages.price IS '价格';
COMMENT ON COLUMN business.member_packages.original_price IS '原价';
COMMENT ON COLUMN business.member_packages.duration_days IS '有效天数';
COMMENT ON COLUMN business.member_packages.max_daily_chats IS '每日最大对话次数（-1表示无限制）';
COMMENT ON COLUMN business.member_packages.max_kb_count IS '最大知识库数量';
COMMENT ON COLUMN business.member_packages.max_kb_documents IS '最大文档数量';
COMMENT ON COLUMN business.member_packages.max_file_storage_mb IS '最大文件存储空间（MB）';
COMMENT ON COLUMN business.member_packages.max_file_count IS '最大文件数量';
COMMENT ON COLUMN business.member_packages.enable_rag IS '是否启用RAG功能';
COMMENT ON COLUMN business.member_packages.enable_web_search IS '是否启用网络搜索';
COMMENT ON COLUMN business.member_packages.enable_mcp_tools IS '是否启用MCP工具';
COMMENT ON COLUMN business.member_packages.status IS '状态: active-有效, inactive-无效';
COMMENT ON COLUMN business.member_packages.sort_order IS '排序顺序';
COMMENT ON COLUMN business.member_packages.created_at IS '创建时间';
COMMENT ON COLUMN business.member_packages.updated_at IS '更新时间';

-- 订单表
CREATE TABLE IF NOT EXISTS business.orders (
    order_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    package_id VARCHAR(50),
    order_type VARCHAR(20),
    amount DECIMAL(10,2) NOT NULL,
    actual_amount DECIMAL(10,2),
    payment_method VARCHAR(20),
    payment_status VARCHAR(20) DEFAULT 'pending',
    payment_time TIMESTAMP,
    transaction_id VARCHAR(100),
    package_name VARCHAR(100),
    duration_days INTEGER,
    original_expire_at TIMESTAMP,
    new_expire_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_orders_user FOREIGN KEY (user_id)
        REFERENCES business.users(user_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_orders_package FOREIGN KEY (package_id)
        REFERENCES business.member_packages(package_id)
        ON DELETE SET NULL
);

COMMENT ON TABLE business.orders IS '订单表';
COMMENT ON COLUMN business.orders.order_id IS '订单ID';
COMMENT ON COLUMN business.orders.user_id IS '用户ID';
COMMENT ON COLUMN business.orders.package_id IS '套餐ID';
COMMENT ON COLUMN business.orders.order_type IS '订单类型: subscription-订阅, renewal-续费, upgrade-升级';
COMMENT ON COLUMN business.orders.amount IS '订单金额';
COMMENT ON COLUMN business.orders.actual_amount IS '实际支付金额';
COMMENT ON COLUMN business.orders.payment_method IS '支付方式: wechat-微信, alipay-支付宝, balance-余额';
COMMENT ON COLUMN business.orders.payment_status IS '支付状态: pending-待支付, paid-已支付, failed-失败, refunded-已退款';
COMMENT ON COLUMN business.orders.payment_time IS '支付时间';
COMMENT ON COLUMN business.orders.transaction_id IS '第三方交易ID';
COMMENT ON COLUMN business.orders.package_name IS '套餐名称（快照）';
COMMENT ON COLUMN business.orders.duration_days IS '有效天数';
COMMENT ON COLUMN business.orders.original_expire_at IS '原会员到期时间';
COMMENT ON COLUMN business.orders.new_expire_at IS '新会员到期时间';
COMMENT ON COLUMN business.orders.status IS '订单状态: active-有效, cancelled-已取消, expired-已过期';
COMMENT ON COLUMN business.orders.created_at IS '创建时间';
COMMENT ON COLUMN business.orders.updated_at IS '更新时间';

-- 会员权益使用记录表
CREATE TABLE IF NOT EXISTS business.member_usage_logs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    usage_type VARCHAR(50),
    usage_amount INTEGER DEFAULT 1,
    usage_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, usage_type, usage_date),
    CONSTRAINT fk_usage_logs_user FOREIGN KEY (user_id)
        REFERENCES business.users(user_id)
        ON DELETE CASCADE
);

COMMENT ON TABLE business.member_usage_logs IS '会员权益使用记录表';
COMMENT ON COLUMN business.member_usage_logs.id IS '主键ID';
COMMENT ON COLUMN business.member_usage_logs.user_id IS '用户ID';
COMMENT ON COLUMN business.member_usage_logs.usage_type IS '使用类型: daily_chats-每日对话, kb_count-知识库, file_storage-文件存储, file_count-文件数量';
COMMENT ON COLUMN business.member_usage_logs.usage_amount IS '使用数量';
COMMENT ON COLUMN business.member_usage_logs.usage_date IS '使用日期';
COMMENT ON COLUMN business.member_usage_logs.created_at IS '创建时间';

-- ============================================================================
-- 3. 企业认证模块
-- ============================================================================

-- 企业认证申请表
CREATE TABLE IF NOT EXISTS business.enterprise_certifications (
    certification_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    enterprise_name VARCHAR(200) NOT NULL,
    credit_code VARCHAR(50) UNIQUE NOT NULL,
    legal_person_name VARCHAR(50),
    legal_person_phone VARCHAR(20),
    legal_person_id_card VARCHAR(20),
    province VARCHAR(50),
    city VARCHAR(50),
    district VARCHAR(50),
    address VARCHAR(500),
    business_license_url TEXT,
    id_card_front_url TEXT,
    id_card_back_url TEXT,
    other_files JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    reject_reason TEXT,
    reviewed_by VARCHAR(50),
    reviewed_at TIMESTAMP,
    cert_expire_at TIMESTAMP,
    remark TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_cert_user FOREIGN KEY (user_id)
        REFERENCES business.users(user_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_cert_reviewer FOREIGN KEY (reviewed_by)
        REFERENCES business.users(user_id)
        ON DELETE SET NULL
);

COMMENT ON TABLE business.enterprise_certifications IS '企业认证申请表';
COMMENT ON COLUMN business.enterprise_certifications.certification_id IS '认证ID';
COMMENT ON COLUMN business.enterprise_certifications.user_id IS '用户ID';
COMMENT ON COLUMN business.enterprise_certifications.enterprise_name IS '企业名称';
COMMENT ON COLUMN business.enterprise_certifications.credit_code IS '统一社会信用代码';
COMMENT ON COLUMN business.enterprise_certifications.legal_person_name IS '法人姓名';
COMMENT ON COLUMN business.enterprise_certifications.legal_person_phone IS '法人电话';
COMMENT ON COLUMN business.enterprise_certifications.legal_person_id_card IS '法人身份证号';
COMMENT ON COLUMN business.enterprise_certifications.province IS '省份';
COMMENT ON COLUMN business.enterprise_certifications.city IS '城市';
COMMENT ON COLUMN business.enterprise_certifications.district IS '区县';
COMMENT ON COLUMN business.enterprise_certifications.address IS '详细地址';
COMMENT ON COLUMN business.enterprise_certifications.business_license_url IS '营业执照图片URL';
COMMENT ON COLUMN business.enterprise_certifications.id_card_front_url IS '法人身份证正面URL';
COMMENT ON COLUMN business.enterprise_certifications.id_card_back_url IS '法人身份证背面URL';
COMMENT ON COLUMN business.enterprise_certifications.other_files IS '其他附件（JSON格式）';
COMMENT ON COLUMN business.enterprise_certifications.status IS '认证状态: pending-待审核, approved-已通过, rejected-已拒绝, expired-已过期';
COMMENT ON COLUMN business.enterprise_certifications.reject_reason IS '拒绝原因';
COMMENT ON COLUMN business.enterprise_certifications.reviewed_by IS '审核人ID';
COMMENT ON COLUMN business.enterprise_certifications.reviewed_at IS '审核时间';
COMMENT ON COLUMN business.enterprise_certifications.cert_expire_at IS '认证到期时间';
COMMENT ON COLUMN business.enterprise_certifications.remark IS '备注';
COMMENT ON COLUMN business.enterprise_certifications.created_at IS '创建时间';
COMMENT ON COLUMN business.enterprise_certifications.updated_at IS '更新时间';

-- 企业成员表
CREATE TABLE IF NOT EXISTS business.enterprise_members (
    id SERIAL PRIMARY KEY,
    enterprise_id VARCHAR(50) NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    member_role VARCHAR(20) DEFAULT 'member',
    status VARCHAR(20) DEFAULT 'active',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(enterprise_id, user_id),
    CONSTRAINT fk_enterprise_members_enterprise FOREIGN KEY (enterprise_id)
        REFERENCES business.enterprise_certifications(certification_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_enterprise_members_user FOREIGN KEY (user_id)
        REFERENCES business.users(user_id)
        ON DELETE CASCADE
);

COMMENT ON TABLE business.enterprise_members IS '企业成员表';
COMMENT ON COLUMN business.enterprise_members.id IS '主键ID';
COMMENT ON COLUMN business.enterprise_members.enterprise_id IS '企业认证ID';
COMMENT ON COLUMN business.enterprise_members.user_id IS '用户ID';
COMMENT ON COLUMN business.enterprise_members.member_role IS '成员角色: admin-管理员, member-普通成员';
COMMENT ON COLUMN business.enterprise_members.status IS '状态: active-有效, inactive-无效';
COMMENT ON COLUMN business.enterprise_members.joined_at IS '加入时间';

-- 企业认证审核日志表
CREATE TABLE IF NOT EXISTS business.enterprise_audit_logs (
    id SERIAL PRIMARY KEY,
    certification_id VARCHAR(50) NOT NULL,
    operator_id VARCHAR(50),
    action VARCHAR(20),
    old_status VARCHAR(20),
    new_status VARCHAR(20),
    remark TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_audit_logs_certification FOREIGN KEY (certification_id)
        REFERENCES business.enterprise_certifications(certification_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_audit_logs_operator FOREIGN KEY (operator_id)
        REFERENCES business.users(user_id)
        ON DELETE SET NULL
);

COMMENT ON TABLE business.enterprise_audit_logs IS '企业认证审核日志表';
COMMENT ON COLUMN business.enterprise_audit_logs.id IS '主键ID';
COMMENT ON COLUMN business.enterprise_audit_logs.certification_id IS '认证ID';
COMMENT ON COLUMN business.enterprise_audit_logs.operator_id IS '操作人ID';
COMMENT ON COLUMN business.enterprise_audit_logs.action IS '操作: submit-提交, approve-通过, reject-拒绝, expire-过期';
COMMENT ON COLUMN business.enterprise_audit_logs.old_status IS '原状态';
COMMENT ON COLUMN business.enterprise_audit_logs.new_status IS '新状态';
COMMENT ON COLUMN business.enterprise_audit_logs.remark IS '备注';
COMMENT ON COLUMN business.enterprise_audit_logs.created_at IS '创建时间';

-- ============================================================================
-- 4. 分销推广模块
-- ============================================================================

-- 推广活动表
CREATE TABLE IF NOT EXISTS business.promotion_activities (
    activity_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    activity_type VARCHAR(20),
    reward_type VARCHAR(20),
    reward_amount DECIMAL(10,2),
    reward_points INTEGER,
    reward_member_days INTEGER,
    min_order_amount DECIMAL(10,2),
    max_reward_per_user DECIMAL(10,2),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE business.promotion_activities IS '推广活动表';
COMMENT ON COLUMN business.promotion_activities.activity_id IS '活动ID';
COMMENT ON COLUMN business.promotion_activities.name IS '活动名称';
COMMENT ON COLUMN business.promotion_activities.description IS '活动描述';
COMMENT ON COLUMN business.promotion_activities.activity_type IS '活动类型: register-注册, order-订单, custom-自定义';
COMMENT ON COLUMN business.promotion_activities.reward_type IS '奖励类型: cash-现金, points-积分, member_days-会员天数';
COMMENT ON COLUMN business.promotion_activities.reward_amount IS '奖励金额';
COMMENT ON COLUMN business.promotion_activities.reward_points IS '奖励积分';
COMMENT ON COLUMN business.promotion_activities.reward_member_days IS '奖励会员天数';
COMMENT ON COLUMN business.promotion_activities.min_order_amount IS '最低订单金额';
COMMENT ON COLUMN business.promotion_activities.max_reward_per_user IS '单用户最大奖励';
COMMENT ON COLUMN business.promotion_activities.start_time IS '开始时间';
COMMENT ON COLUMN business.promotion_activities.end_time IS '结束时间';
COMMENT ON COLUMN business.promotion_activities.status IS '状态: active-有效, paused-暂停, ended-已结束';
COMMENT ON COLUMN business.promotion_activities.created_at IS '创建时间';
COMMENT ON COLUMN business.promotion_activities.updated_at IS '更新时间';

-- 分销用户表
CREATE TABLE IF NOT EXISTS business.distributors (
    user_id VARCHAR(50) PRIMARY KEY,
    distributor_code VARCHAR(20) UNIQUE NOT NULL,
    parent_id VARCHAR(50),
    distributor_level INTEGER DEFAULT 1,
    status VARCHAR(20) DEFAULT 'active',
    total_children_count INTEGER DEFAULT 0,
    total_order_count INTEGER DEFAULT 0,
    total_commission DECIMAL(12,2) DEFAULT 0,
    available_commission DECIMAL(12,2) DEFAULT 0,
    frozen_commission DECIMAL(12,2) DEFAULT 0,
    total_withdrawn DECIMAL(12,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_distributors_user FOREIGN KEY (user_id)
        REFERENCES business.users(user_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_distributors_parent FOREIGN KEY (parent_id)
        REFERENCES business.users(user_id)
        ON DELETE SET NULL
);

COMMENT ON TABLE business.distributors IS '分销用户表';
COMMENT ON COLUMN business.distributors.user_id IS '用户ID';
COMMENT ON COLUMN business.distributors.distributor_code IS '推广码';
COMMENT ON COLUMN business.distributors.parent_id IS '上级分销商ID';
COMMENT ON COLUMN business.distributors.distributor_level IS '分销等级';
COMMENT ON COLUMN business.distributors.status IS '状态: active-有效, frozen-冻结, banned-封禁';
COMMENT ON COLUMN business.distributors.total_children_count IS '下级用户总数';
COMMENT ON COLUMN business.distributors.total_order_count IS '累计订单数';
COMMENT ON COLUMN business.distributors.total_commission IS '累计佣金';
COMMENT ON COLUMN business.distributors.available_commission IS '可提现佣金';
COMMENT ON COLUMN business.distributors.frozen_commission IS '冻结佣金';
COMMENT ON COLUMN business.distributors.total_withdrawn IS '累计已提现金额';
COMMENT ON COLUMN business.distributors.created_at IS '创建时间';
COMMENT ON COLUMN business.distributors.updated_at IS '更新时间';

-- 分销记录表
CREATE TABLE IF NOT EXISTS business.distribution_records (
    record_id VARCHAR(50) PRIMARY KEY,
    promoter_id VARCHAR(50) NOT NULL,
    new_user_id VARCHAR(50) NOT NULL,
    order_id VARCHAR(50),
    activity_id VARCHAR(50),
    commission_amount DECIMAL(10,2),
    commission_status VARCHAR(20) DEFAULT 'pending',
    commission_type VARCHAR(20),
    commission_rate DECIMAL(5,4),
    order_amount DECIMAL(10,2),
    available_time TIMESTAMP,
    settled_time TIMESTAMP,
    expire_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_dist_promoter FOREIGN KEY (promoter_id)
        REFERENCES business.users(user_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_dist_new_user FOREIGN KEY (new_user_id)
        REFERENCES business.users(user_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_dist_order FOREIGN KEY (order_id)
        REFERENCES business.orders(order_id)
        ON DELETE SET NULL,
    CONSTRAINT fk_dist_activity FOREIGN KEY (activity_id)
        REFERENCES business.promotion_activities(activity_id)
        ON DELETE SET NULL
);

COMMENT ON TABLE business.distribution_records IS '分销记录表';
COMMENT ON COLUMN business.distribution_records.record_id IS '记录ID';
COMMENT ON COLUMN business.distribution_records.promoter_id IS '推广人ID';
COMMENT ON COLUMN business.distribution_records.new_user_id IS '新用户ID';
COMMENT ON COLUMN business.distribution_records.order_id IS '订单ID';
COMMENT ON COLUMN business.distribution_records.activity_id IS '活动ID';
COMMENT ON COLUMN business.distribution_records.commission_amount IS '佣金金额';
COMMENT ON COLUMN business.distribution_records.commission_status IS '佣金状态: pending-待结算, available-可提现, settled-已结算, expired-已过期';
COMMENT ON COLUMN business.distribution_records.commission_type IS '佣金类型: direct-直接, indirect-间接';
COMMENT ON COLUMN business.distribution_records.commission_rate IS '佣金比例';
COMMENT ON COLUMN business.distribution_records.order_amount IS '订单金额';
COMMENT ON COLUMN business.distribution_records.available_time IS '可提现时间';
COMMENT ON COLUMN business.distribution_records.settled_time IS '结算时间';
COMMENT ON COLUMN business.distribution_records.expire_time IS '过期时间';
COMMENT ON COLUMN business.distribution_records.created_at IS '创建时间';

-- 提现申请表
CREATE TABLE IF NOT EXISTS business.withdrawal_requests (
    withdrawal_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    withdrawal_method VARCHAR(20),
    account_name VARCHAR(100),
    account_number VARCHAR(100),
    bank_name VARCHAR(100),
    bank_branch VARCHAR(200),
    status VARCHAR(20) DEFAULT 'pending',
    reject_reason TEXT,
    processed_by VARCHAR(50),
    processed_at TIMESTAMP,
    transaction_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_withdrawal_user FOREIGN KEY (user_id)
        REFERENCES business.users(user_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_withdrawal_processor FOREIGN KEY (processed_by)
        REFERENCES business.users(user_id)
        ON DELETE SET NULL
);

COMMENT ON TABLE business.withdrawal_requests IS '提现申请表';
COMMENT ON COLUMN business.withdrawal_requests.withdrawal_id IS '提现ID';
COMMENT ON COLUMN business.withdrawal_requests.user_id IS '用户ID';
COMMENT ON COLUMN business.withdrawal_requests.amount IS '提现金额';
COMMENT ON COLUMN business.withdrawal_requests.withdrawal_method IS '提现方式: wechat-微信, alipay-支付宝, bank-银行卡';
COMMENT ON COLUMN business.withdrawal_requests.account_name IS '账户名称';
COMMENT ON COLUMN business.withdrawal_requests.account_number IS '账户号码';
COMMENT ON COLUMN business.withdrawal_requests.bank_name IS '银行名称';
COMMENT ON COLUMN business.withdrawal_requests.bank_branch IS '银行支行';
COMMENT ON COLUMN business.withdrawal_requests.status IS '状态: pending-待审核, approved-已通过, rejected-已拒绝, completed-已完成';
COMMENT ON COLUMN business.withdrawal_requests.reject_reason IS '拒绝原因';
COMMENT ON COLUMN business.withdrawal_requests.processed_by IS '处理人ID';
COMMENT ON COLUMN business.withdrawal_requests.processed_at IS '处理时间';
COMMENT ON COLUMN business.withdrawal_requests.transaction_id IS '交易ID';
COMMENT ON COLUMN business.withdrawal_requests.created_at IS '创建时间';
COMMENT ON COLUMN business.withdrawal_requests.updated_at IS '更新时间';

-- ============================================================================
-- 5. 客服管理模块
-- ============================================================================

-- 客服消息表
CREATE TABLE IF NOT EXISTS business.customer_messages (
    message_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    session_id VARCHAR(50),
    message_type VARCHAR(20),
    sender_type VARCHAR(20),
    sender_id VARCHAR(50),
    content TEXT,
    file_url TEXT,
    is_read BOOLEAN DEFAULT false,
    read_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_customer_messages_user FOREIGN KEY (user_id)
        REFERENCES business.users(user_id)
        ON DELETE CASCADE
);

COMMENT ON TABLE business.customer_messages IS '客服消息表';
COMMENT ON COLUMN business.customer_messages.message_id IS '消息ID';
COMMENT ON COLUMN business.customer_messages.user_id IS '用户ID';
COMMENT ON COLUMN business.customer_messages.session_id IS '会话ID';
COMMENT ON COLUMN business.customer_messages.message_type IS '消息类型: text-文本, image-图片, file-文件';
COMMENT ON COLUMN business.customer_messages.sender_type IS '发送者类型: user-用户, system-系统, customer_service-客服';
COMMENT ON COLUMN business.customer_messages.sender_id IS '发送者ID';
COMMENT ON COLUMN business.customer_messages.content IS '消息内容';
COMMENT ON COLUMN business.customer_messages.file_url IS '文件URL';
COMMENT ON COLUMN business.customer_messages.is_read IS '是否已读';
COMMENT ON COLUMN business.customer_messages.read_time IS '阅读时间';
COMMENT ON COLUMN business.customer_messages.created_at IS '创建时间';

-- 客服会话表
CREATE TABLE IF NOT EXISTS business.customer_sessions (
    session_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    customer_service_id VARCHAR(50),
    status VARCHAR(20) DEFAULT 'active',
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    rating INTEGER,
    feedback TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_customer_sessions_user FOREIGN KEY (user_id)
        REFERENCES business.users(user_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_customer_sessions_service FOREIGN KEY (customer_service_id)
        REFERENCES business.users(user_id)
        ON DELETE SET NULL
);

COMMENT ON TABLE business.customer_sessions IS '客服会话表';
COMMENT ON COLUMN business.customer_sessions.session_id IS '会话ID';
COMMENT ON COLUMN business.customer_sessions.user_id IS '用户ID';
COMMENT ON COLUMN business.customer_sessions.customer_service_id IS '客服ID';
COMMENT ON COLUMN business.customer_sessions.status IS '状态: active-进行中, closed-已关闭, transferred-已转移';
COMMENT ON COLUMN business.customer_sessions.start_time IS '开始时间';
COMMENT ON COLUMN business.customer_sessions.end_time IS '结束时间';
COMMENT ON COLUMN business.customer_sessions.rating IS '评分（1-5星）';
COMMENT ON COLUMN business.customer_sessions.feedback IS '反馈内容';
COMMENT ON COLUMN business.customer_sessions.created_at IS '创建时间';
COMMENT ON COLUMN business.customer_sessions.updated_at IS '更新时间';

-- 常见问题表
CREATE TABLE IF NOT EXISTS business.faqs (
    faq_id VARCHAR(50) PRIMARY KEY,
    question VARCHAR(500) NOT NULL,
    answer TEXT NOT NULL,
    category VARCHAR(100),
    sort_order INTEGER DEFAULT 0,
    view_count INTEGER DEFAULT 0,
    helpful_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'published',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE business.faqs IS '常见问题表';
COMMENT ON COLUMN business.faqs.faq_id IS 'FAQ ID';
COMMENT ON COLUMN business.faqs.question IS '问题';
COMMENT ON COLUMN business.faqs.answer IS '答案';
COMMENT ON COLUMN business.faqs.category IS '分类';
COMMENT ON COLUMN business.faqs.sort_order IS '排序顺序';
COMMENT ON COLUMN business.faqs.view_count IS '浏览次数';
COMMENT ON COLUMN business.faqs.helpful_count IS '有用次数';
COMMENT ON COLUMN business.faqs.status IS '状态: draft-草稿, published-已发布, archived-已归档';
COMMENT ON COLUMN business.faqs.created_at IS '创建时间';
COMMENT ON COLUMN business.faqs.updated_at IS '更新时间';

-- ============================================================================
-- 6. 用户审核模块
-- ============================================================================

-- 用户违规记录表
CREATE TABLE IF NOT EXISTS business.user_violations (
    violation_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    violation_type VARCHAR(50),
    violation_content TEXT,
    report_source VARCHAR(50),
    reporter_id VARCHAR(50),
    handle_status VARCHAR(20) DEFAULT 'pending',
    handle_result TEXT,
    handled_by VARCHAR(50),
    handled_at TIMESTAMP,
    penalty_days INTEGER,
    penalty_expire_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_violations_user FOREIGN KEY (user_id)
        REFERENCES business.users(user_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_violations_reporter FOREIGN KEY (reporter_id)
        REFERENCES business.users(user_id)
        ON DELETE SET NULL,
    CONSTRAINT fk_violations_handler FOREIGN KEY (handled_by)
        REFERENCES business.users(user_id)
        ON DELETE SET NULL
);

COMMENT ON TABLE business.user_violations IS '用户违规记录表';
COMMENT ON COLUMN business.user_violations.violation_id IS '违规ID';
COMMENT ON COLUMN business.user_violations.user_id IS '用户ID';
COMMENT ON COLUMN business.user_violations.violation_type IS '违规类型: spam-垃圾信息, harassment-骚扰, illegal_content-非法内容, other-其他';
COMMENT ON COLUMN business.user_violations.violation_content IS '违规内容';
COMMENT ON COLUMN business.user_violations.report_source IS '举报来源: system-系统, user-用户, admin-管理员';
COMMENT ON COLUMN business.user_violations.reporter_id IS '举报人ID';
COMMENT ON COLUMN business.user_violations.handle_status IS '处理状态: pending-待处理, warning-警告, banned-封禁, ignored-忽略';
COMMENT ON COLUMN business.user_violations.handle_result IS '处理结果';
COMMENT ON COLUMN business.user_violations.handled_by IS '处理人ID';
COMMENT ON COLUMN business.user_violations.handled_at IS '处理时间';
COMMENT ON COLUMN business.user_violations.penalty_days IS '惩罚天数';
COMMENT ON COLUMN business.user_violations.penalty_expire_at IS '惩罚到期时间';
COMMENT ON COLUMN business.user_violations.created_at IS '创建时间';
COMMENT ON COLUMN business.user_violations.updated_at IS '更新时间';

-- 用户申诉表
CREATE TABLE IF NOT EXISTS business.user_appeals (
    appeal_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    violation_id VARCHAR(50) NOT NULL,
    appeal_reason TEXT,
    appeal_evidence JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    review_result TEXT,
    reviewed_by VARCHAR(50),
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_appeals_user FOREIGN KEY (user_id)
        REFERENCES business.users(user_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_appeals_violation FOREIGN KEY (violation_id)
        REFERENCES business.user_violations(violation_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_appeals_reviewer FOREIGN KEY (reviewed_by)
        REFERENCES business.users(user_id)
        ON DELETE SET NULL
);

COMMENT ON TABLE business.user_appeals IS '用户申诉表';
COMMENT ON COLUMN business.user_appeals.appeal_id IS '申诉ID';
COMMENT ON COLUMN business.user_appeals.user_id IS '用户ID';
COMMENT ON COLUMN business.user_appeals.violation_id IS '违规记录ID';
COMMENT ON COLUMN business.user_appeals.appeal_reason IS '申诉原因';
COMMENT ON COLUMN business.user_appeals.appeal_evidence IS '申诉证据（JSON格式）';
COMMENT ON COLUMN business.user_appeals.status IS '状态: pending-待审核, approved-已通过, rejected-已拒绝';
COMMENT ON COLUMN business.user_appeals.review_result IS '审核结果';
COMMENT ON COLUMN business.user_appeals.reviewed_by IS '审核人ID';
COMMENT ON COLUMN business.user_appeals.reviewed_at IS '审核时间';
COMMENT ON COLUMN business.user_appeals.created_at IS '创建时间';
COMMENT ON COLUMN business.user_appeals.updated_at IS '更新时间';

-- ============================================================================
-- 7. 文件管理模块
-- ============================================================================

-- 用户文件表
CREATE TABLE IF NOT EXISTS business.user_files (
    file_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    file_name VARCHAR(500) NOT NULL,
    file_type VARCHAR(50),
    file_size BIGINT,
    file_path TEXT,
    file_url TEXT,
    mime_type VARCHAR(100),
    category VARCHAR(50),
    folder_path VARCHAR(500),
    kb_name VARCHAR(50),
    status VARCHAR(20) DEFAULT 'active',
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMP,
    download_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user_files_user FOREIGN KEY (user_id)
        REFERENCES business.users(user_id)
        ON DELETE CASCADE
);

COMMENT ON TABLE business.user_files IS '用户文件表';
COMMENT ON COLUMN business.user_files.file_id IS '文件ID';
COMMENT ON COLUMN business.user_files.user_id IS '用户ID';
COMMENT ON COLUMN business.user_files.file_name IS '文件名';
COMMENT ON COLUMN business.user_files.file_type IS '文件类型: pdf, docx, pptx, image, txt, csv, xlsx';
COMMENT ON COLUMN business.user_files.file_size IS '文件大小（字节）';
COMMENT ON COLUMN business.user_files.file_path IS '存储路径';
COMMENT ON COLUMN business.user_files.file_url IS '访问URL';
COMMENT ON COLUMN business.user_files.mime_type IS 'MIME类型';
COMMENT ON COLUMN business.user_files.category IS '分类: document-文档, image-图片, other-其他';
COMMENT ON COLUMN business.user_files.folder_path IS '文件夹路径';
COMMENT ON COLUMN business.user_files.kb_name IS '关联知识库名称';
COMMENT ON COLUMN business.user_files.status IS '状态: active-有效, deleted-已删除, processing-处理中';
COMMENT ON COLUMN business.user_files.is_deleted IS '是否已删除（软删除）';
COMMENT ON COLUMN business.user_files.deleted_at IS '删除时间';
COMMENT ON COLUMN business.user_files.download_count IS '下载次数';
COMMENT ON COLUMN business.user_files.created_at IS '创建时间';
COMMENT ON COLUMN business.user_files.updated_at IS '更新时间';

-- 文件分享表
CREATE TABLE IF NOT EXISTS business.file_shares (
    share_id VARCHAR(50) PRIMARY KEY,
    file_id VARCHAR(50) NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    share_code VARCHAR(20) UNIQUE NOT NULL,
    share_type VARCHAR(20) DEFAULT 'private',
    password VARCHAR(50),
    expire_time TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    max_access_count INTEGER,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_file_shares_file FOREIGN KEY (file_id)
        REFERENCES business.user_files(file_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_file_shares_user FOREIGN KEY (user_id)
        REFERENCES business.users(user_id)
        ON DELETE CASCADE
);

COMMENT ON TABLE business.file_shares IS '文件分享表';
COMMENT ON COLUMN business.file_shares.share_id IS '分享ID';
COMMENT ON COLUMN business.file_shares.file_id IS '文件ID';
COMMENT ON COLUMN business.file_shares.user_id IS '用户ID';
COMMENT ON COLUMN business.file_shares.share_code IS '分享码';
COMMENT ON COLUMN business.file_shares.share_type IS '分享类型: private-私密, public-公开, password-密码保护';
COMMENT ON COLUMN business.file_shares.password IS '访问密码';
COMMENT ON COLUMN business.file_shares.expire_time IS '过期时间';
COMMENT ON COLUMN business.file_shares.access_count IS '访问次数';
COMMENT ON COLUMN business.file_shares.max_access_count IS '最大访问次数';
COMMENT ON COLUMN business.file_shares.status IS '状态: active-有效, expired-已过期, cancelled-已取消';
COMMENT ON COLUMN business.file_shares.created_at IS '创建时间';
COMMENT ON COLUMN business.file_shares.updated_at IS '更新时间';

-- ============================================================================
-- 8. 首页管理模块
-- ============================================================================

-- 轮播图表
CREATE TABLE IF NOT EXISTS business.banners (
    banner_id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(200),
    image_url TEXT NOT NULL,
    link_url TEXT,
    link_type VARCHAR(20),
    sort_order INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active',
    view_count INTEGER DEFAULT 0,
    click_count INTEGER DEFAULT 0,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE business.banners IS '轮播图表';
COMMENT ON COLUMN business.banners.banner_id IS '轮播图ID';
COMMENT ON COLUMN business.banners.title IS '标题';
COMMENT ON COLUMN business.banners.image_url IS '图片URL';
COMMENT ON COLUMN business.banners.link_url IS '链接URL';
COMMENT ON COLUMN business.banners.link_type IS '链接类型: none-无, internal-内部链接, external-外部链接, mini_program-小程序';
COMMENT ON COLUMN business.banners.sort_order IS '排序顺序';
COMMENT ON COLUMN business.banners.status IS '状态: active-有效, inactive-无效';
COMMENT ON COLUMN business.banners.view_count IS '浏览次数';
COMMENT ON COLUMN business.banners.click_count IS '点击次数';
COMMENT ON COLUMN business.banners.start_time IS '开始时间';
COMMENT ON COLUMN business.banners.end_time IS '结束时间';
COMMENT ON COLUMN business.banners.created_at IS '创建时间';
COMMENT ON COLUMN business.banners.updated_at IS '更新时间';

-- 系统公告表
CREATE TABLE IF NOT EXISTS business.announcements (
    announcement_id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    announcement_type VARCHAR(20),
    priority INTEGER DEFAULT 0,
    target_users VARCHAR(50),
    status VARCHAR(20) DEFAULT 'published',
    view_count INTEGER DEFAULT 0,
    publish_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE business.announcements IS '系统公告表';
COMMENT ON COLUMN business.announcements.announcement_id IS '公告ID';
COMMENT ON COLUMN business.announcements.title IS '标题';
COMMENT ON COLUMN business.announcements.content IS '内容';
COMMENT ON COLUMN business.announcements.announcement_type IS '公告类型: system-系统公告, activity-活动公告, maintenance-维护公告';
COMMENT ON COLUMN business.announcements.priority IS '优先级（越大越靠前）';
COMMENT ON COLUMN business.announcements.target_users IS '目标用户: all-全部, vip-VIP用户, enterprise-企业用户';
COMMENT ON COLUMN business.announcements.status IS '状态: draft-草稿, published-已发布, archived-已归档';
COMMENT ON COLUMN business.announcements.view_count IS '浏览次数';
COMMENT ON COLUMN business.announcements.publish_time IS '发布时间';
COMMENT ON COLUMN business.announcements.created_at IS '创建时间';
COMMENT ON COLUMN business.announcements.updated_at IS '更新时间';

-- ============================================================================
-- 9. 系统日志模块
-- ============================================================================

-- 用户行为日志表
CREATE TABLE IF NOT EXISTS business.user_action_logs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    action_type VARCHAR(50),
    action_module VARCHAR(50),
    action_detail JSONB,
    ip_address VARCHAR(50),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_action_logs_user FOREIGN KEY (user_id)
        REFERENCES business.users(user_id)
        ON DELETE CASCADE
);

COMMENT ON TABLE business.user_action_logs IS '用户行为日志表';
COMMENT ON COLUMN business.user_action_logs.id IS '主键ID';
COMMENT ON COLUMN business.user_action_logs.user_id IS '用户ID';
COMMENT ON COLUMN business.user_action_logs.action_type IS '操作类型: login-登录, logout-登出, upload-上传, chat-对话, subscribe-订阅等';
COMMENT ON COLUMN business.user_action_logs.action_module IS '操作模块: chat-对话, knowledge-知识库, member-会员等';
COMMENT ON COLUMN business.user_action_logs.action_detail IS '操作详情（JSON格式）';
COMMENT ON COLUMN business.user_action_logs.ip_address IS 'IP地址';
COMMENT ON COLUMN business.user_action_logs.user_agent IS '用户代理';
COMMENT ON COLUMN business.user_action_logs.created_at IS '创建时间';

-- ============================================================================
-- 创建视图
-- ============================================================================

-- 用户会员信息视图
CREATE OR REPLACE VIEW business.v_user_member_info AS
SELECT
    u.user_id,
    u.nickname,
    u.member_level,
    u.member_expire_at,
    u.user_type,
    u.status,
    mp.name as package_name,
    mp.max_daily_chats,
    mp.max_kb_count,
    mp.max_file_storage_mb
FROM business.users u
LEFT JOIN business.member_packages mp ON u.member_level = mp.package_id;

COMMENT ON VIEW business.v_user_member_info IS '用户会员信息视图';

-- 分销统计视图
CREATE OR REPLACE VIEW business.v_distributor_stats AS
SELECT
    d.user_id,
    d.distributor_code,
    d.distributor_level,
    d.total_children_count,
    d.total_commission,
    d.available_commission,
    u.nickname,
    u.phone
FROM business.distributors d
JOIN business.users u ON d.user_id = u.user_id;

COMMENT ON VIEW business.v_distributor_stats IS '分销统计视图';

-- ============================================================================
-- 初始化数据
-- ============================================================================

-- 插入默认会员套餐
INSERT INTO business.member_packages (package_id, name, description, package_type, price, duration_days, max_daily_chats, max_kb_count, max_kb_documents, max_file_storage_mb, enable_rag, enable_web_search, enable_mcp_tools, sort_order)
VALUES
    ('free', '免费版', '基础功能体验', 'lifetime', 0, NULL, 20, 2, 20, 100, true, false, false, 0),
    ('vip_month', 'VIP月卡', '月度会员，解锁更多功能', 'month', 29.9, 30, -1, 10, 500, 2048, true, true, false, 1),
    ('vip_quarter', 'VIP季卡', '季度会员，超值优惠', 'quarter', 79.9, 90, -1, 20, 2000, 5120, true, true, true, 2),
    ('vip_year', 'VIP年卡', '年度会员，最佳性价比', 'year', 299.9, 365, -1, 50, 10000, 10240, true, true, true, 3)
ON CONFLICT (package_id) DO NOTHING;

-- 插入默认FAQ
INSERT INTO business.faqs (faq_id, question, answer, category, sort_order, status)
VALUES
    ('faq_001', '如何升级会员？', '请前往个人中心-会员中心，选择合适的套餐进行购买。', '会员', 1, 'published'),
    ('faq_002', '如何创建知识库？', '在文件管理页面点击"创建知识库"，填写名称和描述后即可创建。', '知识库', 2, 'published'),
    ('faq_003', '支持哪些文件格式？', '目前支持PDF、DOCX、PPTX、TXT、CSV、XLSX以及常见图片格式。', '文件', 3, 'published'),
    ('faq_004', '如何申请企业认证？', '请前往个人中心-企业认证，填写企业信息并上传营业执照，提交后等待审核。', '认证', 4, 'published'),
    ('faq_005', '如何参与分销推广？', '在个人中心-分销推广中可以获取您的专属推广码，分享给他人注册即可获得佣金奖励。', '分销', 5, 'published')
ON CONFLICT (faq_id) DO NOTHING;
