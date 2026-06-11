-- 用户角色权限系统表结构
-- 将管理员系统改造为通用的角色权限系统
-- 核心设计：role表只存储角色和权限，通过user_id关联users表

-- ============================================================================
-- 用户角色表 (替换 business.admins)
-- ============================================================================
-- 说明：
-- 1. 此表不再存储管理员基本信息（基本信息在users表中）
-- 2. 只存储用户的角色和权限信息
-- 3. 通过user_id外键关联users表
-- 4. 一个用户可以有多条角色记录（如果需要多重角色，也可以使用JSON数组）

CREATE TABLE IF NOT EXISTS business.user_roles (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,  -- 关联users表
    role VARCHAR(50) NOT NULL,      -- 角色: super_admin, admin, operator, vip_user等
    permissions TEXT[],             -- PostgreSQL 数组类型,存储权限代码
    status VARCHAR(20) DEFAULT 'active', -- active, disabled
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50)          -- 创建人user_id
    -- 注意：暂时不添加外键约束，因为可能在迁移时users表还未完全就绪
    -- CONSTRAINT fk_user_roles_user_id FOREIGN KEY (user_id)
    --     REFERENCES business.users(user_id)
    --     ON DELETE CASCADE
);

COMMENT ON TABLE business.user_roles IS '用户角色表 - 存储用户角色和权限信息';
COMMENT ON COLUMN business.user_roles.id IS '主键ID';
COMMENT ON COLUMN business.user_roles.user_id IS '用户ID - 关联business.users表';
COMMENT ON COLUMN business.user_roles.role IS '角色: super_admin-超级管理员, admin-管理员, operator-操作员, vip_user-VIP用户';
COMMENT ON COLUMN business.user_roles.permissions IS '权限列表(数组) - 如: [user.manage, knowledge.view]';
COMMENT ON COLUMN business.user_roles.status IS '状态: active-正常, disabled-禁用';
COMMENT ON COLUMN business.user_roles.created_at IS '创建时间';
COMMENT ON COLUMN business.user_roles.updated_at IS '更新时间';
COMMENT ON COLUMN business.user_roles.created_by IS '创建人用户ID';

-- ============================================================================
-- 创建索引
-- ============================================================================

-- user_id索引（高频查询）
CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON business.user_roles(user_id);
-- 角色索引
CREATE INDEX IF NOT EXISTS idx_user_roles_role ON business.user_roles(role);
-- 状态索引
CREATE INDEX IF NOT EXISTS idx_user_roles_status ON business.user_roles(status);
-- 创建时间索引
CREATE INDEX IF NOT EXISTS idx_user_roles_created_at ON business.user_roles(created_at);
-- 复合索引：查询用户的活跃角色
CREATE INDEX IF NOT EXISTS idx_user_roles_user_status ON business.user_roles(user_id, status);
-- 复合索引：按角色查询
CREATE INDEX IF NOT EXISTS idx_user_roles_role_status ON business.user_roles(role, status);

-- ============================================================================
-- 角色定义表 (可选 - 用于定义标准角色和默认权限)
-- ============================================================================
-- 说明：
-- 此表用于预定义角色模板，方便快速给用户分配标准角色
-- 也可以作为角色权限的参考文档

CREATE TABLE IF NOT EXISTS business.role_definitions (
    role VARCHAR(50) PRIMARY KEY,
    role_name VARCHAR(100) NOT NULL,
    description TEXT,
    default_permissions TEXT[],  -- 该角色的默认权限列表
    is_system BOOLEAN DEFAULT true, -- 是否为系统角色（系统角色不可删除）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE business.role_definitions IS '角色定义表 - 预定义的角色模板';
COMMENT ON COLUMN business.role_definitions.role IS '角色代码（如: super_admin, admin）';
COMMENT ON COLUMN business.role_definitions.role_name IS '角色名称（如: 超级管理员）';
COMMENT ON COLUMN business.role_definitions.description IS '角色描述';
COMMENT ON COLUMN business.role_definitions.default_permissions IS '默认权限列表';
COMMENT ON COLUMN business.role_definitions.is_system IS '是否为系统角色（系统角色不可删除）';

-- ============================================================================
-- 插入默认角色定义
-- ============================================================================

INSERT INTO business.role_definitions (role, role_name, description, default_permissions, is_system) VALUES
(
    'super_admin',
    '超级管理员',
    '拥有系统所有权限的超级管理员',
    ARRAY[
        'user.manage', 'user.view',
        'member.manage', 'member.view',
        'knowledge.manage', 'knowledge.view',
        'knowledge.system.create', 'knowledge.system.delete',
        'mcp.manage', 'mcp.view',
        'distribution.manage', 'distribution.view',
        'order.view', 'order.manage',
        'system.manage', 'system.view',
        'log.view',
        'role.manage', 'role.view',
        '*/*'  -- 超级管理员拥有所有权限
    ],
    true
),
(
    'admin',
    '管理员',
    '拥有大部分管理权限的管理员',
    ARRAY[
        'user.view',
        'member.manage', 'member.view',
        'knowledge.manage', 'knowledge.view',
        'mcp.view',
        'distribution.view',
        'order.view', 'order.manage',
        'log.view'
    ],
    true
),
(
    'operator',
    '操作员',
    '负责日常运营操作的人员',
    ARRAY[
        'user.view',
        'member.view',
        'knowledge.view',
        'order.view',
        'log.view'
    ],
    true
),
(
    'vip_user',
    'VIP用户',
    '拥有特殊权限的VIP用户',
    ARRAY[
        'knowledge.system.view',
        'knowledge.advanced.search'
    ],
    true
) ON CONFLICT (role) DO NOTHING;

-- ============================================================================
-- 用户角色操作日志表 (基于business.admin_action_logs改造)
-- ============================================================================

-- 创建用户角色操作日志表
CREATE TABLE IF NOT EXISTS business.user_role_action_logs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,  -- 操作人user_id
    username VARCHAR(100),          -- 冗余存储用户名
    action_type VARCHAR(50) NOT NULL, -- login, logout, create_user, update_user, delete_user, etc.
    action_module VARCHAR(50) NOT NULL, -- user, member, knowledge, mcp, distribution, order, system
    action_detail JSONB,            -- 操作详情(JSON格式)
    target_user_id VARCHAR(50),     -- 目标用户ID(如果有)
    target_type VARCHAR(50),        -- 目标类型: user, order, knowledge_base, etc.
    target_id VARCHAR(50),          -- 目标ID
    -- 请求信息
    ip_address VARCHAR(50),
    user_agent TEXT,
    request_method VARCHAR(10),
    request_path TEXT,
    -- 响应信息
    response_status INTEGER,        -- HTTP状态码
    response_message TEXT,
    -- 时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    -- 注意：暂时不添加外键约束
    -- CONSTRAINT fk_user_role_action_logs_user_id FOREIGN KEY (user_id)
    --     REFERENCES business.users(user_id)
    --     ON DELETE SET NULL
);

COMMENT ON TABLE business.user_role_action_logs IS '用户角色操作日志表';
COMMENT ON COLUMN business.user_role_action_logs.user_id IS '操作人用户ID';
COMMENT ON COLUMN business.user_role_action_logs.username IS '操作人用户名（冗余存储）';
COMMENT ON COLUMN business.user_role_action_logs.action_type IS '操作类型';
COMMENT ON COLUMN business.user_role_action_logs.action_module IS '操作模块';
COMMENT ON COLUMN business.user_role_action_logs.action_detail IS '操作详情(JSON)';
COMMENT ON COLUMN business.user_role_action_logs.target_user_id IS '目标用户ID';
COMMENT ON COLUMN business.user_role_action_logs.target_type IS '目标类型';
COMMENT ON COLUMN business.user_role_action_logs.target_id IS '目标ID';
COMMENT ON COLUMN business.user_role_action_logs.ip_address IS 'IP地址';
COMMENT ON COLUMN business.user_role_action_logs.user_agent IS '用户代理';
COMMENT ON COLUMN business.user_role_action_logs.request_method IS '请求方法';
COMMENT ON COLUMN business.user_role_action_logs.request_path IS '请求路径';
COMMENT ON COLUMN business.user_role_action_logs.response_status IS '响应状态码';
COMMENT ON COLUMN business.user_role_action_logs.response_message IS '响应消息';
COMMENT ON COLUMN business.user_role_action_logs.created_at IS '创建时间';

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_user_role_action_logs_user_id ON business.user_role_action_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_user_role_action_logs_action_type ON business.user_role_action_logs(action_type);
CREATE INDEX IF NOT EXISTS idx_user_role_action_logs_action_module ON business.user_role_action_logs(action_module);
CREATE INDEX IF NOT EXISTS idx_user_role_action_logs_target_user_id ON business.user_role_action_logs(target_user_id);
CREATE INDEX IF NOT EXISTS idx_user_role_action_logs_created_at ON business.user_role_action_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_user_role_action_logs_user_created_at ON business.user_role_action_logs(user_id, created_at DESC);

-- ============================================================================
-- 视图：用户角色概览
-- ============================================================================

CREATE OR REPLACE VIEW business.v_user_roles AS
SELECT
    ur.user_id,
    u.username,
    u.nickname,
    u.email,
    ur.role,
    ur.permissions,
    ur.status,
    ur.created_at AS role_assigned_at,
    rd.role_name,
    rd.description AS role_description
FROM business.user_roles ur
JOIN business.users u ON ur.user_id = u.user_id
LEFT JOIN business.role_definitions rd ON ur.role = rd.role
WHERE ur.status = 'active';

COMMENT ON VIEW business.v_user_roles IS '用户角色概览视图 - 关联用户信息和角色定义';

-- ============================================================================
-- 迁移说明
-- ============================================================================
-- 1. 执行此脚本创建新表
-- 2. 运行迁移脚本将business.admins数据迁移到business.user_roles
-- 3. 更新应用代码使用新的role系统
-- 4. 验证无误后可以删除business.admins表（可选，建议先保留备份）
