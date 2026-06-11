-- 备份时间: 2026-05-01 17:52:16
-- 表名: ai.agno_eval_runs
-- 记录数: 0
-- 状态: 空表

-- 表结构:
                                                      Table "ai.agno_eval_runs"
          Column          |       Type        | Collation | Nullable | Default | Storage  | Compression | Stats target | Description 
--------------------------+-------------------+-----------+----------+---------+----------+-------------+--------------+-------------
 run_id                   | character varying |           | not null |         | extended |             |              | 
 eval_type                | character varying |           | not null |         | extended |             |              | 
 eval_data                | jsonb             |           | not null |         | extended |             |              | 
 eval_input               | jsonb             |           | not null |         | extended |             |              | 
 name                     | character varying |           |          |         | extended |             |              | 
 agent_id                 | character varying |           |          |         | extended |             |              | 
 team_id                  | character varying |           |          |         | extended |             |              | 
 workflow_id              | character varying |           |          |         | extended |             |              | 
 model_id                 | character varying |           |          |         | extended |             |              | 
 model_provider           | character varying |           |          |         | extended |             |              | 
 evaluated_component_name | character varying |           |          |         | extended |             |              | 
 created_at               | bigint            |           | not null |         | plain    |             |              | 
 updated_at               | bigint            |           |          |         | plain    |             |              | 
Indexes:
    "agno_eval_runs_pkey" PRIMARY KEY, btree (run_id)
    "idx_agno_eval_runs_created_at" btree (created_at)
Access method: heap

