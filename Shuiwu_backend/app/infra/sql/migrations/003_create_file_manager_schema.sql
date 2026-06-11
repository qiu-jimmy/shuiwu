-- 创建文件管理模块的表（使用business schema）
-- 执行时间: 2026-01-14

-- 创建文件信息表
CREATE TABLE IF NOT EXISTS business.files (
    file_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size BIGINT NOT NULL,
    file_path TEXT NOT NULL,
    file_url TEXT NOT NULL,
    mime_type VARCHAR(100),
    category VARCHAR(50) DEFAULT 'document',
    folder_path VARCHAR(500),
    kb_name VARCHAR(100),
    status VARCHAR(20) DEFAULT 'active',
    is_deleted BOOLEAN DEFAULT FALSE,
    download_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建文件表索引
CREATE INDEX IF NOT EXISTS idx_files_user_id ON business.files(user_id);
CREATE INDEX IF NOT EXISTS idx_files_file_type ON business.files(file_type);
CREATE INDEX IF NOT EXISTS idx_files_category ON business.files(category);
CREATE INDEX IF NOT EXISTS idx_files_folder_path ON business.files(folder_path);
CREATE INDEX IF NOT EXISTS idx_files_kb_name ON business.files(kb_name);
CREATE INDEX IF NOT EXISTS idx_files_status ON business.files(status);
CREATE INDEX IF NOT EXISTS idx_files_created_at ON business.files(created_at);

-- 创建文件分享表
CREATE TABLE IF NOT EXISTS business.file_shares (
    share_id VARCHAR(50) PRIMARY KEY,
    file_id VARCHAR(50) NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    share_code VARCHAR(50) UNIQUE NOT NULL,
    share_type VARCHAR(20) DEFAULT 'private',
    password VARCHAR(100),
    expire_time TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    max_access_count INTEGER,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES business.files(file_id) ON DELETE CASCADE
);

-- 创建文件分享表索引
CREATE INDEX IF NOT EXISTS idx_file_shares_share_code ON business.file_shares(share_code);
CREATE INDEX IF NOT EXISTS idx_file_shares_user_id ON business.file_shares(user_id);
CREATE INDEX IF NOT EXISTS idx_file_shares_status ON business.file_shares(status);

-- 添加表注释
COMMENT ON TABLE business.files IS '文件信息表';
COMMENT ON TABLE business.file_shares IS '文件分享表';

-- 添加列注释
COMMENT ON COLUMN business.files.file_id IS '文件唯一标识';
COMMENT ON COLUMN business.files.user_id IS '用户ID';
COMMENT ON COLUMN business.files.file_name IS '文件名';
COMMENT ON COLUMN business.files.file_type IS '文件类型（扩展名）';
COMMENT ON COLUMN business.files.file_size IS '文件大小（字节）';
COMMENT ON COLUMN business.files.file_path IS '文件存储路径';
COMMENT ON COLUMN business.files.file_url IS '文件访问URL';
COMMENT ON COLUMN business.files.mime_type IS 'MIME类型';
COMMENT ON COLUMN business.files.category IS '文件分类（document/image/video等）';
COMMENT ON COLUMN business.files.folder_path IS '文件夹路径';
COMMENT ON COLUMN business.files.kb_name IS '关联的知识库名称';
COMMENT ON COLUMN business.files.status IS '文件状态（active/inactive/deleted）';
COMMENT ON COLUMN business.files.is_deleted IS '是否已删除（软删除标记）';
COMMENT ON COLUMN business.files.download_count IS '下载次数';
COMMENT ON COLUMN business.files.created_at IS '创建时间';
COMMENT ON COLUMN business.files.updated_at IS '更新时间';

COMMENT ON COLUMN business.file_shares.share_id IS '分享唯一标识';
COMMENT ON COLUMN business.file_shares.file_id IS '文件ID';
COMMENT ON COLUMN business.file_shares.user_id IS '用户ID';
COMMENT ON COLUMN business.file_shares.share_code IS '分享码';
COMMENT ON COLUMN business.file_shares.share_type IS '分享类型（private/public）';
COMMENT ON COLUMN business.file_shares.password IS '访问密码';
COMMENT ON COLUMN business.file_shares.expire_time IS '过期时间';
COMMENT ON COLUMN business.file_shares.access_count IS '访问次数';
COMMENT ON COLUMN business.file_shares.max_access_count IS '最大访问次数';
COMMENT ON COLUMN business.file_shares.status IS '分享状态';
