-- 备份时间: 2026-05-01 17:52:18
-- 表名: business.promotion_activities
-- 记录数: 0
-- 状态: 空表

-- 表结构:
                                                                                  Table "business.promotion_activities"
       Column        |            Type             | Collation | Nullable |           Default           | Storage  | Compression | Stats target |                      Description                       
---------------------+-----------------------------+-----------+----------+-----------------------------+----------+-------------+--------------+--------------------------------------------------------
 activity_id         | character varying(50)       |           | not null |                             | extended |             |              | 活动ID
 name                | character varying(200)      |           | not null |                             | extended |             |              | 活动名称
 description         | text                        |           |          |                             | extended |             |              | 活动描述
 activity_type       | character varying(20)       |           |          |                             | extended |             |              | 活动类型: register-注册, order-订单, custom-自定义
 reward_type         | character varying(20)       |           |          |                             | extended |             |              | 奖励类型: cash-现金, points-积分, member_days-会员天数
 reward_amount       | numeric(10,2)               |           |          |                             | main     |             |              | 奖励金额
 reward_points       | integer                     |           |          |                             | plain    |             |              | 奖励积分
 reward_member_days  | integer                     |           |          |                             | plain    |             |              | 奖励会员天数
 min_order_amount    | numeric(10,2)               |           |          |                             | main     |             |              | 最低订单金额
 max_reward_per_user | numeric(10,2)               |           |          |                             | main     |             |              | 单用户最大奖励
 start_time          | timestamp without time zone |           |          |                             | plain    |             |              | 开始时间
 end_time            | timestamp without time zone |           |          |                             | plain    |             |              | 结束时间
 status              | character varying(20)       |           |          | 'active'::character varying | extended |             |              | 状态: active-有效, paused-暂停, ended-已结束
 created_at          | timestamp without time zone |           |          | CURRENT_TIMESTAMP           | plain    |             |              | 创建时间
 updated_at          | timestamp without time zone |           |          | CURRENT_TIMESTAMP           | plain    |             |              | 更新时间
Indexes:
    "promotion_activities_pkey" PRIMARY KEY, btree (activity_id)
    "idx_promotion_activities_activity_type" btree (activity_type)
    "idx_promotion_activities_created_at" btree (created_at)
    "idx_promotion_activities_end_time" btree (end_time)
    "idx_promotion_activities_reward_type" btree (reward_type)
    "idx_promotion_activities_start_end" btree (start_time, end_time)
    "idx_promotion_activities_start_time" btree (start_time)
    "idx_promotion_activities_status" btree (status)
    "idx_promotion_activities_status_start" btree (status, start_time)
Referenced by:
    TABLE "business.distribution_records" CONSTRAINT "distribution_records_activity_id_fkey" FOREIGN KEY (activity_id) REFERENCES business.promotion_activities(activity_id)
Access method: heap

