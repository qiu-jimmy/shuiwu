-- =====================================================
-- 为 V4黑金会员套餐添加缺失的权益
-- 问题：V4黑金会员套餐创建时（010迁移），008迁移中的三个功能
--      （发票穿透、全景、经营风险）没有被添加，因为 v4_black_gold_year
--      不匹配 008 迁移中的任何 LIKE 模式（%vip%, %premium%, %enterprise%, %free%）
-- 解决：为 v4_black_gold_year 补充这三个功能配置
-- =====================================================

-- V4黑金会员是最高级别套餐，给予无限次使用（-1）
UPDATE business.member_packages
SET
    custom_config = jsonb_set(
        jsonb_set(
            jsonb_set(
                jsonb_set(
                    jsonb_set(
                        jsonb_set(
                            COALESCE(custom_config, '{}'),
                            '{enable_invoice_penetration}',
                            'true'::jsonb
                        ),
                        '{max_invoice_penetration}',
                        '-1'::jsonb
                    ),
                    '{enable_panorama}',
                    'true'::jsonb
                ),
                '{max_panorama}',
                '-1'::jsonb
            ),
            '{enable_business_risk}',
            'true'::jsonb
        ),
        '{max_business_risk}',
        '-1'::jsonb
    ),
    benefits = benefits || '[
        {"title": "发票穿透", "desc": "深度分析发票关联关系，无限次使用"},
        {"title": "全景报告", "desc": "企业全景数据报告，无限次使用"},
        {"title": "经营风险", "desc": "企业经营风险评估，无限次使用"}
    ]'::jsonb
WHERE package_id = 'v4_black_gold_year';

-- =====================================================
-- 完成迁移
-- =====================================================
-- 说明：
-- -1 表示无限使用
-- V4黑金会员是最高级别套餐，应该享有所有功能的无限使用权限
