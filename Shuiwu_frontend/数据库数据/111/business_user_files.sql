-- 备份时间: 2026-05-01 17:52:18
-- 表名: business.user_files
-- 记录数: 0
-- 状态: 空表

-- 表结构:
                                                                                   Table "business.user_files"
     Column     |            Type             | Collation | Nullable |           Default           | Storage  | Compression | Stats target |                     Description                      
----------------+-----------------------------+-----------+----------+-----------------------------+----------+-------------+--------------+------------------------------------------------------
 file_id        | character varying(50)       |           | not null |                             | extended |             |              | 文件ID
 user_id        | character varying(50)       |           |          |                             | extended |             |              | 用户ID
 file_name      | character varying(500)      |           | not null |                             | extended |             |              | 文件名
 file_type      | character varying(50)       |           |          |                             | extended |             |              | 文件类型: pdf, docx, pptx, image, txt, csv, xlsx
 file_size      | bigint                      |           |          |                             | plain    |             |              | 文件大小（字节）
 file_path      | text                        |           |          |                             | extended |             |              | 存储路径
 file_url       | text                        |           |          |                             | extended |             |              | 访问URL
 mime_type      | character varying(100)      |           |          |                             | extended |             |              | MIME类型
 category       | character varying(50)       |           |          |                             | extended |             |              | 分类: document-文档, image-图片, other-其他
 folder_path    | character varying(500)      |           |          |                             | extended |             |              | 文件夹路径
 kb_name        | character varying(50)       |           |          |                             | extended |             |              | 关联知识库名称
 status         | character varying(20)       |           |          | 'active'::character varying | extended |             |              | 状态: active-有效, deleted-已删除, processing-处理中
 is_deleted     | boolean                     |           |          | false                       | plain    |             |              | 是否已删除（软删除）
 deleted_at     | timestamp without time zone |           |          |                             | plain    |             |              | 删除时间
 download_count | integer                     |           |          | 0                           | plain    |             |              | 下载次数
 created_at     | timestamp without time zone |           |          | CURRENT_TIMESTAMP           | plain    |             |              | 创建时间
 updated_at     | timestamp without time zone |           |          | CURRENT_TIMESTAMP           | plain    |             |              | 更新时间
Indexes:
    "user_files_pkey" PRIMARY KEY, btree (file_id)
    "idx_files_category" btree (category)
    "idx_files_created_at" btree (created_at)
    "idx_files_deleted_at" btree (deleted_at)
    "idx_files_file_type" btree (file_type)
    "idx_files_folder_path" btree (folder_path)
    "idx_files_folder_status" btree (folder_path, status)
    "idx_files_is_deleted" btree (is_deleted)
    "idx_files_kb_name" btree (kb_name)
    "idx_files_kb_status" btree (kb_name, status)
    "idx_files_status" btree (status)
    "idx_files_updated_at" btree (updated_at)
    "idx_files_user_created_at" btree (user_id, created_at DESC)
    "idx_files_user_id" btree (user_id)
    "idx_files_user_status" btree (user_id, status)
Foreign-key constraints:
    "user_files_user_id_fkey" FOREIGN KEY (user_id) REFERENCES business.users(user_id)
Referenced by:
    TABLE "business.file_shares" CONSTRAINT "file_shares_file_id_fkey" FOREIGN KEY (file_id) REFERENCES business.user_files(file_id)
Access method: heap

