-- 业务数据库Schema设计
-- 创建业务数据库schema
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
    status VARCHAR(20) DEFAULT 'normal', -- normal, disabled, banned, pending_review
    user_type VARCHAR(20) DEFAULT 'individual', -- individual, enterprise
    member_level VARCHAR(20) DEFAULT 'free', -- free, vip, premium, enterprise
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
    user_id VARCHAR(50) REFERENCES business.users(user_id) ON DELETE CASCADE,
    tag_name VARCHAR(50) NOT NULL,
    tag_type VARCHAR(20), -- system, custom
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, tag_name)
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
    user_id VARCHAR(50) REFERENCES business.users(user_id),
    wx_openid VARCHAR(100),
    login_type VARCHAR(20), -- login, register
    ip_address VARCHAR(50),
    user_agent TEXT,
    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    package_type VARCHAR(20), -- month, quarter, year, lifetime
    price DECIMAL(10,2) NOT NULL,
    original_price DECIMAL(10,2),
    duration_days INTEGER,
    -- 权益配置
    max_daily_chats INTEGER DEFAULT -1, -- -1表示无限制
    max_kb_count INTEGER DEFAULT 5,
    max_kb_documents INTEGER DEFAULT 100,
    max_file_storage_mb INTEGER DEFAULT 1024,
    max_file_count INTEGER DEFAULT 100,
    enable_rag BOOLEAN DEFAULT true,
    enable_web_search BOOLEAN DEFAULT false,
    enable_mcp_tools BOOLEAN DEFAULT false,
    -- 其他
    status VARCHAR(20) DEFAULT 'active', -- active, inactive
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
    user_id VARCHAR(50) REFERENCES business.users(user_id),
    package_id VARCHAR(50) REFERENCES business.member_packages(package_id),
    order_type VARCHAR(20), -- subscription, renewal, upgrade
    amount DECIMAL(10,2) NOT NULL,
    actual_amount DECIMAL(10,2),
    payment_method VARCHAR(20), -- wechat, alipay, balance
    payment_status VARCHAR(20) DEFAULT 'pending', -- pending, paid, failed, refunded
    payment_time TIMESTAMP,
    transaction_id VARCHAR(100),
    -- 订单详情
    package_name VARCHAR(100),
    duration_days INTEGER,
    original_expire_at TIMESTAMP,
    new_expire_at TIMESTAMP,
    -- 其他
    status VARCHAR(20) DEFAULT 'active', -- active, cancelled, expired
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    user_id VARCHAR(50) REFERENCES business.users(user_id),
    usage_type VARCHAR(50), -- daily_chats, kb_count, file_storage, file_count
    usage_amount INTEGER DEFAULT 1,
    usage_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, usage_type, usage_date)
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
    user_id VARCHAR(50) REFERENCES business.users(user_id),
    -- 企业信息
    enterprise_name VARCHAR(200) NOT NULL,
    credit_code VARCHAR(50) UNIQUE NOT NULL, -- 统一社会信用代码
    legal_person_name VARCHAR(50),
    legal_person_phone VARCHAR(20),
    legal_person_id_card VARCHAR(20),
    -- 企业地址
    province VARCHAR(50),
    city VARCHAR(50),
    district VARCHAR(50),
    address VARCHAR(500),
    -- 证件资料
    business_license_url TEXT, -- 营业执照图片URL
    id_card_front_url TEXT, -- 法人身份证正面
    id_card_back_url TEXT, -- 法人身份证背面
    other_files JSONB, -- 其他附件
    -- 认证状态
    status VARCHAR(20) DEFAULT 'pending', -- pending, approved, rejected, expired
    reject_reason TEXT,
    reviewed_by VARCHAR(50), -- 审核人user_id
    reviewed_at TIMESTAMP,
    cert_expire_at TIMESTAMP, -- 认证到期时间
    -- 其他
    remark TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    enterprise_id VARCHAR(50) REFERENCES business.enterprise_certifications(certification_id),
    user_id VARCHAR(50) REFERENCES business.users(user_id),
    member_role VARCHAR(20) DEFAULT 'member', -- admin, member
    status VARCHAR(20) DEFAULT 'active', -- active, inactive
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(enterprise_id, user_id)
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
    certification_id VARCHAR(50) REFERENCES business.enterprise_certifications(certification_id),
    operator_id VARCHAR(50),
    action VARCHAR(20), -- submit, approve, reject, expire
    old_status VARCHAR(20),
    new_status VARCHAR(20),
    remark TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    activity_type VARCHAR(20), -- register, order, custom
    -- 奖励规则
    reward_type VARCHAR(20), -- cash, points, member_days
    reward_amount DECIMAL(10,2),
    reward_points INTEGER,
    reward_member_days INTEGER,
    -- 条件
    min_order_amount DECIMAL(10,2),
    max_reward_per_user DECIMAL(10,2),
    -- 时间
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active', -- active, paused, ended
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
    user_id VARCHAR(50) PRIMARY KEY REFERENCES business.users(user_id),
    distributor_code VARCHAR(20) UNIQUE NOT NULL, -- 推广码
    parent_id VARCHAR(50) REFERENCES business.users(user_id), -- 上级分销商
    distributor_level INTEGER DEFAULT 1, -- 分销等级
    status VARCHAR(20) DEFAULT 'active', -- active, frozen, banned
    -- 统计
    total_children_count INTEGER DEFAULT 0, -- 下级用户数
    total_order_count INTEGER DEFAULT 0, -- 累计订单数
    total_commission DECIMAL(12,2) DEFAULT 0, -- 累计佣金
    available_commission DECIMAL(12,2) DEFAULT 0, -- 可提现佣金
    frozen_commission DECIMAL(12,2) DEFAULT 0, -- 冻结佣金
    total_withdrawn DECIMAL(12,2) DEFAULT 0, -- 累计已提现
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    promoter_id VARCHAR(50) REFERENCES business.users(user_id), -- 推广人
    new_user_id VARCHAR(50) REFERENCES business.users(user_id), -- 新用户
    order_id VARCHAR(50) REFERENCES business.orders(order_id),
    activity_id VARCHAR(50) REFERENCES business.promotion_activities(activity_id),
    -- 佣金信息
    commission_amount DECIMAL(10,2),
    commission_status VARCHAR(20) DEFAULT 'pending', -- pending, available, settled, expired
    commission_type VARCHAR(20), -- direct, indirect
    commission_rate DECIMAL(5,4), -- 佣金比例
    order_amount DECIMAL(10,2),
    -- 时间
    available_time TIMESTAMP, -- 可提现时间
    settled_time TIMESTAMP, -- 结算时间
    expire_time TIMESTAMP, -- 过期时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    user_id VARCHAR(50) REFERENCES business.users(user_id),
    amount DECIMAL(10,2) NOT NULL,
    -- 收款信息
    withdrawal_method VARCHAR(20), -- wechat, alipay, bank
    account_name VARCHAR(100),
    account_number VARCHAR(100),
    bank_name VARCHAR(100),
    bank_branch VARCHAR(200),
    -- 状态
    status VARCHAR(20) DEFAULT 'pending', -- pending, approved, rejected, completed
    reject_reason TEXT,
    -- 处理信息
    processed_by VARCHAR(50),
    processed_at TIMESTAMP,
    transaction_id VARCHAR(100),
    -- 时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    user_id VARCHAR(50) REFERENCES business.users(user_id),
    session_id VARCHAR(50),
    message_type VARCHAR(20), -- text, image, file
    sender_type VARCHAR(20), -- user, system, customer_service
    sender_id VARCHAR(50),
    content TEXT,
    file_url TEXT,
    is_read BOOLEAN DEFAULT false,
    read_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    user_id VARCHAR(50) REFERENCES business.users(user_id),
    customer_service_id VARCHAR(50),
    status VARCHAR(20) DEFAULT 'active', -- active, closed, transferred
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    -- 评价
    rating INTEGER, -- 1-5星
    feedback TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    category VARCHAR(100), -- 分类
    sort_order INTEGER DEFAULT 0,
    view_count INTEGER DEFAULT 0,
    helpful_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'published', -- draft, published, archived
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
    user_id VARCHAR(50) REFERENCES business.users(user_id),
    violation_type VARCHAR(50), -- spam, harassment, illegal_content, other
    violation_content TEXT,
    report_source VARCHAR(50), -- system, user, admin
    reporter_id VARCHAR(50),
    -- 处理
    handle_status VARCHAR(20) DEFAULT 'pending', -- pending, warning, banned, ignored
    handle_result TEXT,
    handled_by VARCHAR(50),
    handled_at TIMESTAMP,
    -- 惩罚
    penalty_days INTEGER,
    penalty_expire_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    user_id VARCHAR(50) REFERENCES business.users(user_id),
    violation_id VARCHAR(50) REFERENCES business.user_violations(violation_id),
    appeal_reason TEXT,
    appeal_evidence JSONB, -- 证据材料
    status VARCHAR(20) DEFAULT 'pending', -- pending, approved, rejected
    review_result TEXT,
    reviewed_by VARCHAR(50),
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    user_id VARCHAR(50) REFERENCES business.users(user_id),
    file_name VARCHAR(500) NOT NULL,
    file_type VARCHAR(50), -- pdf, docx, pptx, image, txt, csv, xlsx
    file_size BIGINT, -- 字节
    file_path TEXT, -- 存储路径
    file_url TEXT, -- 访问URL
    mime_type VARCHAR(100),
    -- 分类
    category VARCHAR(50), -- document, image, other
    folder_path VARCHAR(500), -- 文件夹路径
    -- 关联
    kb_name VARCHAR(50), -- 关联知识库
    -- 状态
    status VARCHAR(20) DEFAULT 'active', -- active, deleted, processing
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMP,
    -- 统计
    download_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    file_id VARCHAR(50) REFERENCES business.user_files(file_id),
    user_id VARCHAR(50) REFERENCES business.users(user_id),
    share_code VARCHAR(20) UNIQUE NOT NULL,
    share_type VARCHAR(20) DEFAULT 'private', -- private, public, password
    password VARCHAR(50),
    expire_time TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    max_access_count INTEGER,
    status VARCHAR(20) DEFAULT 'active', -- active, expired, cancelled
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    link_type VARCHAR(20), -- none, internal, external, mini_program
    -- 排序
    sort_order INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active', -- active, inactive
    -- 统计
    view_count INTEGER DEFAULT 0,
    click_count INTEGER DEFAULT 0,
    -- 时间
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
    announcement_type VARCHAR(20), -- system, activity, maintenance
    priority INTEGER DEFAULT 0, -- 优先级，越大越靠前
    target_users VARCHAR(50), -- all, vip, enterprise
    status VARCHAR(20) DEFAULT 'published', -- draft, published, archived
    -- 统计
    view_count INTEGER DEFAULT 0,
    -- 时间
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
-- 9. 系统日志表
-- ============================================================================

-- 用户行为日志表
CREATE TABLE IF NOT EXISTS business.user_action_logs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES business.users(user_id),
    action_type VARCHAR(50), -- login, logout, upload, chat, subscribe, etc.
    action_module VARCHAR(50), -- chat, knowledge, member, etc.
    action_detail JSONB,
    ip_address VARCHAR(50),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
-- 创建索引
-- ============================================================================

-- ------------------------------------------------------------------------------
-- 1. 用户管理模块索引
-- ------------------------------------------------------------------------------

-- 用户表索引
CREATE INDEX IF NOT EXISTS idx_users_wx_openid ON business.users(wx_openid);
CREATE INDEX IF NOT EXISTS idx_users_phone ON business.users(phone);
CREATE INDEX IF NOT EXISTS idx_users_status ON business.users(status);
CREATE INDEX IF NOT EXISTS idx_users_user_type ON business.users(user_type);
CREATE INDEX IF NOT EXISTS idx_users_member_level ON business.users(member_level);
CREATE INDEX IF NOT EXISTS idx_users_member_expire_at ON business.users(member_expire_at);
CREATE INDEX IF NOT EXISTS idx_users_register_time ON business.users(register_time);
CREATE INDEX IF NOT EXISTS idx_users_last_login_time ON business.users(last_login_time);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON business.users(created_at);
-- 复合索引：会员查询
CREATE INDEX IF NOT EXISTS idx_users_member_expire_status ON business.users(member_expire_at, status);
-- 复合索引：用户类型和状态
CREATE INDEX IF NOT EXISTS idx_users_type_status ON business.users(user_type, status);

-- 用户标签表索引
CREATE INDEX IF NOT EXISTS idx_user_tags_user_id ON business.user_tags(user_id);
CREATE INDEX IF NOT EXISTS idx_user_tags_tag_name ON business.user_tags(tag_name);
CREATE INDEX IF NOT EXISTS idx_user_tags_tag_type ON business.user_tags(tag_type);
CREATE INDEX IF NOT EXISTS idx_user_tags_created_at ON business.user_tags(created_at);

-- 微信登录记录表索引
CREATE INDEX IF NOT EXISTS idx_wx_login_user_id ON business.wx_login_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_wx_login_wx_openid ON business.wx_login_logs(wx_openid);
CREATE INDEX IF NOT EXISTS idx_wx_login_login_type ON business.wx_login_logs(login_type);
CREATE INDEX IF NOT EXISTS idx_wx_login_login_time ON business.wx_login_logs(login_time);
CREATE INDEX IF NOT EXISTS idx_wx_login_user_login_time ON business.wx_login_logs(user_id, login_time);

-- ------------------------------------------------------------------------------
-- 2. 会员订阅模块索引
-- ------------------------------------------------------------------------------

-- 会员套餐表索引
CREATE INDEX IF NOT EXISTS idx_member_packages_status ON business.member_packages(status);
CREATE INDEX IF NOT EXISTS idx_member_packages_package_type ON business.member_packages(package_type);
CREATE INDEX IF NOT EXISTS idx_member_packages_sort_order ON business.member_packages(sort_order);
CREATE INDEX IF NOT EXISTS idx_member_packages_created_at ON business.member_packages(created_at);

-- 订单表索引
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON business.orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_package_id ON business.orders(package_id);
CREATE INDEX IF NOT EXISTS idx_orders_order_type ON business.orders(order_type);
CREATE INDEX IF NOT EXISTS idx_orders_payment_status ON business.orders(payment_status);
CREATE INDEX IF NOT EXISTS idx_orders_payment_method ON business.orders(payment_method);
CREATE INDEX IF NOT EXISTS idx_orders_payment_time ON business.orders(payment_time);
CREATE INDEX IF NOT EXISTS idx_orders_status ON business.orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON business.orders(created_at);
CREATE INDEX IF NOT EXISTS idx_orders_updated_at ON business.orders(updated_at);
-- 复合索引：用户订单查询
CREATE INDEX IF NOT EXISTS idx_orders_user_payment_status ON business.orders(user_id, payment_status);
CREATE INDEX IF NOT EXISTS idx_orders_user_created_at ON business.orders(user_id, created_at DESC);
-- 复合索引：支付状态和时间
CREATE INDEX IF NOT EXISTS idx_orders_payment_status_time ON business.orders(payment_status, created_at);

-- 会员权益使用记录表索引
CREATE INDEX IF NOT EXISTS idx_usage_logs_user_id ON business.member_usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_usage_type ON business.member_usage_logs(usage_type);
CREATE INDEX IF NOT EXISTS idx_usage_logs_usage_date ON business.member_usage_logs(usage_date);
CREATE INDEX IF NOT EXISTS idx_usage_logs_user_type_date ON business.member_usage_logs(user_id, usage_type, usage_date);

-- ------------------------------------------------------------------------------
-- 3. 企业认证模块索引
-- ------------------------------------------------------------------------------

-- 企业认证申请表索引
CREATE INDEX IF NOT EXISTS idx_cert_user_id ON business.enterprise_certifications(user_id);
CREATE INDEX IF NOT EXISTS idx_cert_status ON business.enterprise_certifications(status);
CREATE INDEX IF NOT EXISTS idx_cert_credit_code ON business.enterprise_certifications(credit_code);
CREATE INDEX IF NOT EXISTS idx_cert_enterprise_name ON business.enterprise_certifications(enterprise_name);
CREATE INDEX IF NOT EXISTS idx_cert_legal_person_phone ON business.enterprise_certifications(legal_person_phone);
CREATE INDEX IF NOT EXISTS idx_cert_province ON business.enterprise_certifications(province);
CREATE INDEX IF NOT EXISTS idx_cert_city ON business.enterprise_certifications(city);
CREATE INDEX IF NOT EXISTS idx_cert_reviewed_by ON business.enterprise_certifications(reviewed_by);
CREATE INDEX IF NOT EXISTS idx_cert_reviewed_at ON business.enterprise_certifications(reviewed_at);
CREATE INDEX IF NOT EXISTS idx_cert_cert_expire_at ON business.enterprise_certifications(cert_expire_at);
CREATE INDEX IF NOT EXISTS idx_cert_created_at ON business.enterprise_certifications(created_at);
CREATE INDEX IF NOT EXISTS idx_cert_updated_at ON business.enterprise_certifications(updated_at);
-- 复合索引：状态和创建时间
CREATE INDEX IF NOT EXISTS idx_cert_status_created_at ON business.enterprise_certifications(status, created_at DESC);
-- 复合索引：地区查询
CREATE INDEX IF NOT EXISTS idx_cert_province_city ON business.enterprise_certifications(province, city);
-- 复合索引：审核待处理
CREATE INDEX IF NOT EXISTS idx_cert_status_reviewed ON business.enterprise_certifications(status, reviewed_at);

-- 企业成员表索引
CREATE INDEX IF NOT EXISTS idx_enterprise_members_enterprise_id ON business.enterprise_members(enterprise_id);
CREATE INDEX IF NOT EXISTS idx_enterprise_members_user_id ON business.enterprise_members(user_id);
CREATE INDEX IF NOT EXISTS idx_enterprise_members_member_role ON business.enterprise_members(member_role);
CREATE INDEX IF NOT EXISTS idx_enterprise_members_status ON business.enterprise_members(status);
CREATE INDEX IF NOT EXISTS idx_enterprise_members_joined_at ON business.enterprise_members(joined_at);
-- 复合索引：企业成员查询
CREATE INDEX IF NOT EXISTS idx_enterprise_members_ent_status ON business.enterprise_members(enterprise_id, status);

-- 企业认证审核日志表索引
CREATE INDEX IF NOT EXISTS idx_audit_logs_certification_id ON business.enterprise_audit_logs(certification_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_operator_id ON business.enterprise_audit_logs(operator_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON business.enterprise_audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON business.enterprise_audit_logs(created_at);
-- 复合索引：认证日志查询
CREATE INDEX IF NOT EXISTS idx_audit_logs_cert_created_at ON business.enterprise_audit_logs(certification_id, created_at DESC);

-- ------------------------------------------------------------------------------
-- 4. 分销推广模块索引
-- ------------------------------------------------------------------------------

-- 推广活动表索引
CREATE INDEX IF NOT EXISTS idx_promotion_activities_activity_type ON business.promotion_activities(activity_type);
CREATE INDEX IF NOT EXISTS idx_promotion_activities_reward_type ON business.promotion_activities(reward_type);
CREATE INDEX IF NOT EXISTS idx_promotion_activities_status ON business.promotion_activities(status);
CREATE INDEX IF NOT EXISTS idx_promotion_activities_start_time ON business.promotion_activities(start_time);
CREATE INDEX IF NOT EXISTS idx_promotion_activities_end_time ON business.promotion_activities(end_time);
CREATE INDEX IF NOT EXISTS idx_promotion_activities_created_at ON business.promotion_activities(created_at);
-- 复合索引：活动时间范围
CREATE INDEX IF NOT EXISTS idx_promotion_activities_start_end ON business.promotion_activities(start_time, end_time);
-- 复合索引：有效活动
CREATE INDEX IF NOT EXISTS idx_promotion_activities_status_start ON business.promotion_activities(status, start_time);

-- 分销用户表索引
CREATE INDEX IF NOT EXISTS idx_distributors_distributor_code ON business.distributors(distributor_code);
CREATE INDEX IF NOT EXISTS idx_distributors_parent_id ON business.distributors(parent_id);
CREATE INDEX IF NOT EXISTS idx_distributors_distributor_level ON business.distributors(distributor_level);
CREATE INDEX IF NOT EXISTS idx_distributors_status ON business.distributors(status);
CREATE INDEX IF NOT EXISTS idx_distributors_created_at ON business.distributors(created_at);
CREATE INDEX IF NOT EXISTS idx_distributors_updated_at ON business.distributors(updated_at);
-- 复合索引：上级和状态
CREATE INDEX IF NOT EXISTS idx_distributors_parent_status ON business.distributors(parent_id, status);

-- 分销记录表索引
CREATE INDEX IF NOT EXISTS idx_dist_promoter ON business.distribution_records(promoter_id);
CREATE INDEX IF NOT EXISTS idx_dist_new_user ON business.distribution_records(new_user_id);
CREATE INDEX IF NOT EXISTS idx_dist_order_id ON business.distribution_records(order_id);
CREATE INDEX IF NOT EXISTS idx_dist_activity_id ON business.distribution_records(activity_id);
CREATE INDEX IF NOT EXISTS idx_dist_commission_status ON business.distribution_records(commission_status);
CREATE INDEX IF NOT EXISTS idx_dist_commission_type ON business.distribution_records(commission_type);
CREATE INDEX IF NOT EXISTS idx_dist_available_time ON business.distribution_records(available_time);
CREATE INDEX IF NOT EXISTS idx_dist_settled_time ON business.distribution_records(settled_time);
CREATE INDEX IF NOT EXISTS idx_dist_expire_time ON business.distribution_records(expire_time);
CREATE INDEX IF NOT EXISTS idx_dist_created_at ON business.distribution_records(created_at);
-- 复合索引：推广人记录查询
CREATE INDEX IF NOT EXISTS idx_dist_promoter_status ON business.distribution_records(promoter_id, commission_status);
CREATE INDEX IF NOT EXISTS idx_dist_promoter_created_at ON business.distribution_records(promoter_id, created_at DESC);
-- 复合索引：佣金结算时间
CREATE INDEX IF NOT EXISTS idx_dist_status_available_time ON business.distribution_records(commission_status, available_time);

-- 提现申请表索引
CREATE INDEX IF NOT EXISTS idx_withdrawal_user_id ON business.withdrawal_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_withdrawal_withdrawal_method ON business.withdrawal_requests(withdrawal_method);
CREATE INDEX IF NOT EXISTS idx_withdrawal_status ON business.withdrawal_requests(status);
CREATE INDEX IF NOT EXISTS idx_withdrawal_processed_by ON business.withdrawal_requests(processed_by);
CREATE INDEX IF NOT EXISTS idx_withdrawal_processed_at ON business.withdrawal_requests(processed_at);
CREATE INDEX IF NOT EXISTS idx_withdrawal_created_at ON business.withdrawal_requests(created_at);
CREATE INDEX IF NOT EXISTS idx_withdrawal_updated_at ON business.withdrawal_requests(updated_at);
-- 复合索引：用户提现查询
CREATE INDEX IF NOT EXISTS idx_withdrawal_user_status ON business.withdrawal_requests(user_id, status);
CREATE INDEX IF NOT EXISTS idx_withdrawal_user_created_at ON business.withdrawal_requests(user_id, created_at DESC);
-- 复合索引：待处理提现
CREATE INDEX IF NOT EXISTS idx_withdrawal_status_created_at ON business.withdrawal_requests(status, created_at);

-- ------------------------------------------------------------------------------
-- 5. 客服管理模块索引
-- ------------------------------------------------------------------------------

-- 客服消息表索引
CREATE INDEX IF NOT EXISTS idx_customer_messages_user_id ON business.customer_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_customer_messages_session_id ON business.customer_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_customer_messages_message_type ON business.customer_messages(message_type);
CREATE INDEX IF NOT EXISTS idx_customer_messages_sender_type ON business.customer_messages(sender_type);
CREATE INDEX IF NOT EXISTS idx_customer_messages_sender_id ON business.customer_messages(sender_id);
CREATE INDEX IF NOT EXISTS idx_customer_messages_is_read ON business.customer_messages(is_read);
CREATE INDEX IF NOT EXISTS idx_customer_messages_read_time ON business.customer_messages(read_time);
CREATE INDEX IF NOT EXISTS idx_customer_messages_created_at ON business.customer_messages(created_at);
-- 复合索引：会话消息查询
CREATE INDEX IF NOT EXISTS idx_customer_messages_session_created_at ON business.customer_messages(session_id, created_at);
-- 复合索引：用户未读消息
CREATE INDEX IF NOT EXISTS idx_customer_messages_user_read ON business.customer_messages(user_id, is_read);

-- 客服会话表索引
CREATE INDEX IF NOT EXISTS idx_customer_sessions_user_id ON business.customer_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_customer_sessions_customer_service_id ON business.customer_sessions(customer_service_id);
CREATE INDEX IF NOT EXISTS idx_customer_sessions_status ON business.customer_sessions(status);
CREATE INDEX IF NOT EXISTS idx_customer_sessions_start_time ON business.customer_sessions(start_time);
CREATE INDEX IF NOT EXISTS idx_customer_sessions_end_time ON business.customer_sessions(end_time);
CREATE INDEX IF NOT EXISTS idx_customer_sessions_created_at ON business.customer_sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_customer_sessions_updated_at ON business.customer_sessions(updated_at);
-- 复合索引：客服活跃会话
CREATE INDEX IF NOT EXISTS idx_customer_sessions_cs_status ON business.customer_sessions(customer_service_id, status);
-- 复合索引：用户会话查询
CREATE INDEX IF NOT EXISTS idx_customer_sessions_user_start_time ON business.customer_sessions(user_id, start_time DESC);

-- 常见问题表索引
CREATE INDEX IF NOT EXISTS idx_faqs_category ON business.faqs(category);
CREATE INDEX IF NOT EXISTS idx_faqs_status ON business.faqs(status);
CREATE INDEX IF NOT EXISTS idx_faqs_sort_order ON business.faqs(sort_order);
CREATE INDEX IF NOT EXISTS idx_faqs_created_at ON business.faqs(created_at);
CREATE INDEX IF NOT EXISTS idx_faqs_updated_at ON business.faqs(updated_at);
-- 复合索引：分类和状态
CREATE INDEX IF NOT EXISTS idx_faqs_category_status_sort ON business.faqs(category, status, sort_order);

-- ------------------------------------------------------------------------------
-- 6. 用户审核模块索引
-- ------------------------------------------------------------------------------

-- 用户违规记录表索引
CREATE INDEX IF NOT EXISTS idx_violations_user_id ON business.user_violations(user_id);
CREATE INDEX IF NOT EXISTS idx_violations_violation_type ON business.user_violations(violation_type);
CREATE INDEX IF NOT EXISTS idx_violations_report_source ON business.user_violations(report_source);
CREATE INDEX IF NOT EXISTS idx_violations_reporter_id ON business.user_violations(reporter_id);
CREATE INDEX IF NOT EXISTS idx_violations_handle_status ON business.user_violations(handle_status);
CREATE INDEX IF NOT EXISTS idx_violations_handled_by ON business.user_violations(handled_by);
CREATE INDEX IF NOT EXISTS idx_violations_handled_at ON business.user_violations(handled_at);
CREATE INDEX IF NOT EXISTS idx_violations_penalty_expire_at ON business.user_violations(penalty_expire_at);
CREATE INDEX IF NOT EXISTS idx_violations_created_at ON business.user_violations(created_at);
CREATE INDEX IF NOT EXISTS idx_violations_updated_at ON business.user_violations(updated_at);
-- 复合索引：待处理违规
CREATE INDEX IF NOT EXISTS idx_violations_status_created_at ON business.user_violations(handle_status, created_at);
-- 复合索引：用户违规记录
CREATE INDEX IF NOT EXISTS idx_violations_user_created_at ON business.user_violations(user_id, created_at DESC);

-- 用户申诉表索引
CREATE INDEX IF NOT EXISTS idx_appeals_user_id ON business.user_appeals(user_id);
CREATE INDEX IF NOT EXISTS idx_appeals_violation_id ON business.user_appeals(violation_id);
CREATE INDEX IF NOT EXISTS idx_appeals_status ON business.user_appeals(status);
CREATE INDEX IF NOT EXISTS idx_appeals_reviewed_by ON business.user_appeals(reviewed_by);
CREATE INDEX IF NOT EXISTS idx_appeals_reviewed_at ON business.user_appeals(reviewed_at);
CREATE INDEX IF NOT EXISTS idx_appeals_created_at ON business.user_appeals(created_at);
CREATE INDEX IF NOT EXISTS idx_appeals_updated_at ON business.user_appeals(updated_at);
-- 复合索引：待审核申诉
CREATE INDEX IF NOT EXISTS idx_appeals_status_created_at ON business.user_appeals(status, created_at);
-- 复合索引：违规申诉查询
CREATE INDEX IF NOT EXISTS idx_appeals_violation_created_at ON business.user_appeals(violation_id, created_at DESC);

-- ------------------------------------------------------------------------------
-- 7. 文件管理模块索引
-- ------------------------------------------------------------------------------

-- 用户文件表索引
CREATE INDEX IF NOT EXISTS idx_files_user_id ON business.user_files(user_id);
CREATE INDEX IF NOT EXISTS idx_files_file_type ON business.user_files(file_type);
CREATE INDEX IF NOT EXISTS idx_files_category ON business.user_files(category);
CREATE INDEX IF NOT EXISTS idx_files_kb_name ON business.user_files(kb_name);
CREATE INDEX IF NOT EXISTS idx_files_folder_path ON business.user_files(folder_path);
CREATE INDEX IF NOT EXISTS idx_files_status ON business.user_files(status);
CREATE INDEX IF NOT EXISTS idx_files_is_deleted ON business.user_files(is_deleted);
CREATE INDEX IF NOT EXISTS idx_files_deleted_at ON business.user_files(deleted_at);
CREATE INDEX IF NOT EXISTS idx_files_created_at ON business.user_files(created_at);
CREATE INDEX IF NOT EXISTS idx_files_updated_at ON business.user_files(updated_at);
-- 复合索引：用户文件查询
CREATE INDEX IF NOT EXISTS idx_files_user_status ON business.user_files(user_id, status);
CREATE INDEX IF NOT EXISTS idx_files_user_created_at ON business.user_files(user_id, created_at DESC);
-- 复合索引：知识库文件
CREATE INDEX IF NOT EXISTS idx_files_kb_status ON business.user_files(kb_name, status);
-- 复合索引：文件夹文件
CREATE INDEX IF NOT EXISTS idx_files_folder_status ON business.user_files(folder_path, status);

-- 文件分享表索引
CREATE INDEX IF NOT EXISTS idx_shares_file_id ON business.file_shares(file_id);
CREATE INDEX IF NOT EXISTS idx_shares_user_id ON business.file_shares(user_id);
CREATE INDEX IF NOT EXISTS idx_shares_share_code ON business.file_shares(share_code);
CREATE INDEX IF NOT EXISTS idx_shares_share_type ON business.file_shares(share_type);
CREATE INDEX IF NOT EXISTS idx_shares_expire_time ON business.file_shares(expire_time);
CREATE INDEX IF NOT EXISTS idx_shares_status ON business.file_shares(status);
CREATE INDEX IF NOT EXISTS idx_shares_created_at ON business.file_shares(created_at);
CREATE INDEX IF NOT EXISTS idx_shares_updated_at ON business.file_shares(updated_at);
-- 复合索引：用户分享查询
CREATE INDEX IF NOT EXISTS idx_shares_user_status ON business.file_shares(user_id, status);
-- 复合索引：分享码和状态
CREATE INDEX IF NOT EXISTS idx_shares_code_status ON business.file_shares(share_code, status);
-- 复合索引：过期分享
CREATE INDEX IF NOT EXISTS idx_shares_status_expire_time ON business.file_shares(status, expire_time);

-- ------------------------------------------------------------------------------
-- 8. 首页管理模块索引
-- ------------------------------------------------------------------------------

-- 轮播图表索引
CREATE INDEX IF NOT EXISTS idx_banners_status ON business.banners(status);
CREATE INDEX IF NOT EXISTS idx_banners_sort_order ON business.banners(sort_order);
CREATE INDEX IF NOT EXISTS idx_banners_start_time ON business.banners(start_time);
CREATE INDEX IF NOT EXISTS idx_banners_end_time ON business.banners(end_time);
CREATE INDEX IF NOT EXISTS idx_banners_created_at ON business.banners(created_at);
CREATE INDEX IF NOT EXISTS idx_banners_updated_at ON business.banners(updated_at);
-- 复合索引：有效轮播图
CREATE INDEX IF NOT EXISTS idx_banners_status_sort_order ON business.banners(status, sort_order);
-- 复合索引：时间范围
CREATE INDEX IF NOT EXISTS idx_banners_start_end_status ON business.banners(start_time, end_time, status);

-- 系统公告表索引
CREATE INDEX IF NOT EXISTS idx_announcements_announcement_type ON business.announcements(announcement_type);
CREATE INDEX IF NOT EXISTS idx_announcements_target_users ON business.announcements(target_users);
CREATE INDEX IF NOT EXISTS idx_announcements_status ON business.announcements(status);
CREATE INDEX IF NOT EXISTS idx_announcements_priority ON business.announcements(priority);
CREATE INDEX IF NOT EXISTS idx_announcements_publish_time ON business.announcements(publish_time);
CREATE INDEX IF NOT EXISTS idx_announcements_created_at ON business.announcements(created_at);
CREATE INDEX IF NOT EXISTS idx_announcements_updated_at ON business.announcements(updated_at);
-- 复合索引：有效公告
CREATE INDEX IF NOT EXISTS idx_announcements_status_priority ON business.announcements(status, priority DESC);
-- 复合索引：目标用户公告
CREATE INDEX IF NOT EXISTS idx_announcements_target_status_priority ON business.announcements(target_users, status, priority DESC);

-- ------------------------------------------------------------------------------
-- 9. 系统日志模块索引
-- ------------------------------------------------------------------------------

-- 用户行为日志表索引
CREATE INDEX IF NOT EXISTS idx_action_logs_user_id ON business.user_action_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_action_logs_action_type ON business.user_action_logs(action_type);
CREATE INDEX IF NOT EXISTS idx_action_logs_action_module ON business.user_action_logs(action_module);
CREATE INDEX IF NOT EXISTS idx_action_logs_ip_address ON business.user_action_logs(ip_address);
CREATE INDEX IF NOT EXISTS idx_action_logs_created_at ON business.user_action_logs(created_at);
-- 复合索引：用户行为查询
CREATE INDEX IF NOT EXISTS idx_action_logs_user_created_at ON business.user_action_logs(user_id, created_at DESC);
-- 复合索引：模块和时间
CREATE INDEX IF NOT EXISTS idx_action_logs_module_created_at ON business.user_action_logs(action_module, created_at DESC);
-- 复合索引：操作类型和时间
CREATE INDEX IF NOT EXISTS idx_action_logs_type_created_at ON business.user_action_logs(action_type, created_at DESC);

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
