-- 备份时间: 2026-05-01 17:52:16
-- 表名: ai.agno_component_links
-- 记录数: 0
-- 状态: 空表

-- 表结构:
                                                Table "ai.agno_component_links"
       Column        |       Type        | Collation | Nullable | Default | Storage  | Compression | Stats target | Description 
---------------------+-------------------+-----------+----------+---------+----------+-------------+--------------+-------------
 parent_component_id | character varying |           | not null |         | extended |             |              | 
 parent_version      | integer           |           | not null |         | plain    |             |              | 
 link_kind           | character varying |           | not null |         | extended |             |              | 
 link_key            | character varying |           | not null |         | extended |             |              | 
 child_component_id  | character varying |           | not null |         | extended |             |              | 
 child_version       | integer           |           |          |         | plain    |             |              | 
 position            | integer           |           | not null |         | plain    |             |              | 
 meta                | jsonb             |           |          |         | extended |             |              | 
 created_at          | bigint            |           |          |         | plain    |             |              | 
 updated_at          | bigint            |           |          |         | plain    |             |              | 
Indexes:
    "agno_component_links_pkey" PRIMARY KEY, btree (parent_component_id, parent_version, link_kind, link_key)
    "idx_agno_component_links_created_at" btree (created_at)
    "idx_agno_component_links_link_kind" btree (link_kind)
Foreign-key constraints:
    "agno_component_links_child_component_id_fkey" FOREIGN KEY (child_component_id) REFERENCES ai.agno_components(component_id)
    "agno_component_links_parent_component_id_parent_version_fkey" FOREIGN KEY (parent_component_id, parent_version) REFERENCES ai.agno_component_configs(component_id, version)
Access method: heap

