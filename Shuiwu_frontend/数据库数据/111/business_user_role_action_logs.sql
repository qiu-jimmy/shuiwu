-- 备份时间: 2026-05-01 17:52:18
-- 表名: business.user_role_action_logs
-- 记录数: 0
-- 状态: 空表

-- 表结构:
                                                                          Table "business.user_role_action_logs"
      Column      |            Type             | Collation | Nullable |                          Default                           | Storage  | Compression | Stats target | Description 
------------------+-----------------------------+-----------+----------+------------------------------------------------------------+----------+-------------+--------------+-------------
 id               | integer                     |           | not null | nextval('business.user_role_action_logs_id_seq'::regclass) | plain    |             |              | 
 user_id          | character varying(50)       |           | not null |                                                            | extended |             |              | 
 username         | character varying(100)      |           |          |                                                            | extended |             |              | 
 action_type      | character varying(50)       |           | not null |                                                            | extended |             |              | 
 action_module    | character varying(50)       |           | not null |                                                            | extended |             |              | 
 action_detail    | jsonb                       |           |          |                                                            | extended |             |              | 
 target_user_id   | character varying(50)       |           |          |                                                            | extended |             |              | 
 target_type      | character varying(50)       |           |          |                                                            | extended |             |              | 
 target_id        | character varying(50)       |           |          |                                                            | extended |             |              | 
 ip_address       | character varying(50)       |           |          |                                                            | extended |             |              | 
 user_agent       | text                        |           |          |                                                            | extended |             |              | 
 request_method   | character varying(10)       |           |          |                                                            | extended |             |              | 
 request_path     | text                        |           |          |                                                            | extended |             |              | 
 response_status  | integer                     |           |          |                                                            | plain    |             |              | 
 response_message | text                        |           |          |                                                            | extended |             |              | 
 created_at       | timestamp without time zone |           |          | CURRENT_TIMESTAMP                                          | plain    |             |              | 
Indexes:
    "user_role_action_logs_pkey" PRIMARY KEY, btree (id)
    "idx_user_role_action_logs_created_at" btree (created_at)
    "idx_user_role_action_logs_user_id" btree (user_id)
Access method: heap

