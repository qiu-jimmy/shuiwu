-- 管理员系统表结构
-- 创建管理员相关的数据库表

-- ============================================================================
-- 管理员表
-- ============================================================================

CREATE TABLE IF NOT EXISTS business.admins (
    admin_id VARCHAR(50) PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nickname VARCHAR(100),
    avatar_url TEXT,
    email VARCHAR(100),
    phone VARCHAR(20),
    -- 角色和权限
    role VARCHAR(50) NOT NULL DEFAULT 'admin', -- super_admin, admin, operator
    permissions TEXT[], -- PostgreSQL 数组类型,存储权限代码
    -- 状态
    status VARCHAR(20) DEFAULT 'active', -- active, disabled, locked
    -- 登录信息
    last_login_time TIMESTAMP,
    last_login_ip VARCHAR(50),
    failed_login_count INTEGER DEFAULT 0,
    locked_until TIMESTAMP,
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50) -- 创建人admin_id
);

COMMENT ON TABLE business.admins IS '管理员表';
COMMENT ON COLUMN business.admins.admin_id IS '管理员ID';
COMMENT ON COLUMN business.admins.username IS '用户名(登录账号)';
COMMENT ON COLUMN business.admins.password_hash IS '密码哈希值(bcrypt加密)';
COMMENT ON COLUMN business.admins.nickname IS '昵称';
COMMENT ON COLUMN business.admins.avatar_url IS '头像URL';
COMMENT ON COLUMN business.admins.email IS '邮箱';
COMMENT ON COLUMN business.admins.phone IS '手机号';
COMMENT ON COLUMN business.admins.role IS '角色: super_admin-超级管理员, admin-管理员, operator-操作员';
COMMENT ON COLUMN business.admins.permissions IS '权限列表(数组)';
COMMENT ON COLUMN business.admins.status IS '状态: active-正常, disabled-禁用, locked-锁定';
COMMENT ON COLUMN business.admins.last_login_time IS '最后登录时间';
COMMENT ON COLUMN business.admins.last_login_ip IS '最后登录IP';
COMMENT ON COLUMN business.admins.failed_login_count IS '登录失败次数';
COMMENT ON COLUMN business.admins.locked_until IS '锁定到期时间';
COMMENT ON COLUMN business.admins.created_at IS '创建时间';
COMMENT ON COLUMN business.admins.updated_at IS '更新时间';
COMMENT ON COLUMN business.admins.created_by IS '创建人ID';

-- ============================================================================
-- 管理员操作日志表
-- ============================================================================

CREATE TABLE IF NOT EXISTS business.admin_action_logs (
    id SERIAL PRIMARY KEY,
    admin_id VARCHAR(50) REFERENCES business.admins(admin_id),
    admin_name VARCHAR(100), -- 冗余存储管理员名称,防止管理员被删除后无法追溯
    action_type VARCHAR(50) NOT NULL, -- login, logout, create_user, update_user, delete_user, etc.
    action_module VARCHAR(50) NOT NULL, -- user, member, knowledge, mcp, distribution, order, system
    action_detail JSONB, -- 操作详情(JSON格式)
    target_user_id VARCHAR(50), -- 目标用户ID(如果有)
    target_type VARCHAR(50), -- 目标类型: user, order, knowledge_base, etc.
    target_id VARCHAR(50), -- 目标ID
    -- 请求信息
    ip_address VARCHAR(50),
    user_agent TEXT,
    request_method VARCHAR(10),
    request_path TEXT,
    -- 响应信息
    response_status INTEGER, -- HTTP状态码
    response_message TEXT,
    -- 时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE business.admin_action_logs IS '管理员操作日志表';
COMMENT ON COLUMN business.admin_action_logs.id IS '主键ID';
COMMENT ON COLUMN business.admin_action_logs.admin_id IS '管理员ID';
COMMENT ON COLUMN business.admin_action_logs.admin_name IS '管理员名称';
COMMENT ON COLUMN business.admin_action_logs.action_type IS '操作类型';
COMMENT ON COLUMN business.admin_action_logs.action_module IS '操作模块';
COMMENT ON COLUMN business.admin_action_logs.action_detail IS '操作详情(JSON)';
COMMENT ON COLUMN business.admin_action_logs.target_user_id IS '目标用户ID';
COMMENT ON COLUMN business.admin_action_logs.target_type IS '目标类型';
COMMENT ON COLUMN business.admin_action_logs.target_id IS '目标ID';
COMMENT ON COLUMN business.admin_action_logs.ip_address IS 'IP地址';
COMMENT ON COLUMN business.admin_action_logs.user_agent IS '用户代理';
COMMENT ON COLUMN business.admin_action_logs.request_method IS '请求方法(GET,POST,PUT,DELETE)';
COMMENT ON COLUMN business.admin_action_logs.request_path IS '请求路径';
COMMENT ON COLUMN business.admin_action_logs.response_status IS '响应状态码';
COMMENT ON COLUMN business.admin_action_logs.response_message IS '响应消息';
COMMENT ON COLUMN business.admin_action_logs.created_at IS '创建时间';

-- ============================================================================
-- 创建索引
-- ============================================================================

-- 管理员表索引
CREATE INDEX IF NOT EXISTS idx_admins_username ON business.admins(username);
CREATE INDEX IF NOT EXISTS idx_admins_email ON business.admins(email);
CREATE INDEX IF NOT EXISTS idx_admins_phone ON business.admins(phone);
CREATE INDEX IF NOT EXISTS idx_admins_role ON business.admins(role);
CREATE INDEX IF NOT EXISTS idx_admins_status ON business.admins(status);
CREATE INDEX IF NOT EXISTS idx_admins_last_login_time ON business.admins(last_login_time);
CREATE INDEX IF NOT EXISTS idx_admins_created_at ON business.admins(created_at);
CREATE INDEX IF NOT EXISTS idx_admins_created_by ON business.admins(created_by);

-- 管理员操作日志表索引
CREATE INDEX IF NOT EXISTS idx_admin_logs_admin_id ON business.admin_action_logs(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_logs_action_type ON business.admin_action_logs(action_type);
CREATE INDEX IF NOT EXISTS idx_admin_logs_action_module ON business.admin_action_logs(action_module);
CREATE INDEX IF NOT EXISTS idx_admin_logs_target_user_id ON business.admin_action_logs(target_user_id);
CREATE INDEX IF NOT EXISTS idx_admin_logs_target_type ON business.admin_action_logs(target_type);
CREATE INDEX IF NOT EXISTS idx_admin_logs_target_id ON business.admin_action_logs(target_id);
CREATE INDEX IF NOT EXISTS idx_admin_logs_ip_address ON business.admin_action_logs(ip_address);
CREATE INDEX IF NOT EXISTS idx_admin_logs_created_at ON business.admin_action_logs(created_at);
-- 复合索引：管理员操作查询
CREATE INDEX IF NOT EXISTS idx_admin_logs_admin_created_at ON business.admin_action_logs(admin_id, created_at DESC);
-- 复合索引：模块和类型
CREATE INDEX IF NOT EXISTS idx_admin_logs_module_type_created_at ON business.admin_action_logs(action_module, action_type, created_at DESC);
-- 复合索引：目标查询
CREATE INDEX IF NOT EXISTS idx_admin_logs_target_type_id ON business.admin_action_logs(target_type, target_id);

-- ============================================================================
-- 插入默认管理员数据
-- ============================================================================

-- 默认超级管理员
-- 密码: admin123 (bcrypt hash)
INSERT INTO business.admins (
    admin_id,
    username,
    password_hash,
    nickname,
    role,
    permissions,
    status
) VALUES (
    'admin_001',
    'admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5ND7y.Ks0qW0m',
    '超级管理员',
    'super_admin',
    ARRAY[
        'user.manage', 'user.view',
        'member.manage', 'member.view',
        'knowledge.manage', 'knowledge.view',
        'mcp.manage', 'mcp.view',
        'distribution.manage', 'distribution.view',
        'order.view', 'order.manage',
        'system.manage', 'system.view',
        'log.view',
        'admin.manage'
    ],
    'active'
) ON CONFLICT (admin_id) DO NOTHING;

-- ============================================================================
-- 创建视图
-- ============================================================================

-- 管理员操作统计视图
CREATE OR REPLACE VIEW business.v_admin_action_stats AS
SELECT
    admin_id,
    admin_name,
    action_module,
    COUNT(*) as action_count,
    MAX(created_at) as last_action_time
FROM business.admin_action_logs
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY admin_id, admin_name, action_module
ORDER BY admin_id, action_module;

COMMENT ON VIEW business.v_admin_action_stats IS '管理员操作统计视图(最近30天)';
