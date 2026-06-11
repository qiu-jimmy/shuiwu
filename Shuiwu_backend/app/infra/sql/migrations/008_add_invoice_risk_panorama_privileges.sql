-- =====================================================
-- 新增会员权益：发票穿透、全景、经营风险
-- 权益类型：按次计费（每次使用消耗1次）
-- =====================================================

-- 1. 为不同套餐配置这三个权益
-- 免费套餐：不启用（或给少量试用次数）
UPDATE business.member_packages
SET custom_config = jsonb_set(
    jsonb_set(
        jsonb_set(
            jsonb_set(
                jsonb_set(
                    jsonb_set(
                        COALESCE(custom_config, '{}'),
                        '{enable_invoice_penetration}',
                        'false'::jsonb
                    ),
                    '{max_invoice_penetration}',
                    '0'::jsonb
                ),
                '{enable_panorama}',
                'false'::jsonb
            ),
            '{max_panorama}',
            '0'::jsonb
        ),
        '{enable_business_risk}',
        'false'::jsonb
    ),
    '{max_business_risk}',
    '0'::jsonb
)
WHERE package_id LIKE '%free%' OR package_id = 'free';

-- VIP月卡套餐：启用并设置配额
UPDATE business.member_packages
SET custom_config = jsonb_set(
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
                    '10'::jsonb
                ),
                '{enable_panorama}',
                'true'::jsonb
            ),
            '{max_panorama}',
            '5'::jsonb
        ),
        '{enable_business_risk}',
        'true'::jsonb
    ),
    '{max_business_risk}',
    '5'::jsonb
)
WHERE package_id LIKE '%vip%' AND package_id LIKE '%month%';

-- VIP季卡/年卡套餐：更多配额
UPDATE business.member_packages
SET custom_config = jsonb_set(
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
                    '30'::jsonb
                ),
                '{enable_panorama}',
                'true'::jsonb
            ),
            '{max_panorama}',
            '20'::jsonb
        ),
        '{enable_business_risk}',
        'true'::jsonb
    ),
    '{max_business_risk}',
    '20'::jsonb
)
WHERE package_id LIKE '%vip%' AND (package_id LIKE '%quarter%' OR package_id LIKE '%year%');

-- 高级套餐：更高配额
UPDATE business.member_packages
SET custom_config = jsonb_set(
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
                    '50'::jsonb
                ),
                '{enable_panorama}',
                'true'::jsonb
            ),
            '{max_panorama}',
            '30'::jsonb
        ),
        '{enable_business_risk}',
        'true'::jsonb
    ),
    '{max_business_risk}',
    '30'::jsonb
)
WHERE package_id LIKE '%premium%';

-- 企业套餐：无限使用或超大配额
UPDATE business.member_packages
SET custom_config = jsonb_set(
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
)
WHERE package_id LIKE '%enterprise%';

-- =====================================================
-- 更新权益描述（benefits）- 添加到现有权益列表
-- =====================================================

-- VIP套餐添加权益描述
UPDATE business.member_packages
SET benefits = benefits || '[
    {"title": "发票穿透", "desc": "深度分析发票关联关系，支持10次/月"},
    {"title": "全景报告", "desc": "企业全景数据报告，支持5次/月"},
    {"title": "经营风险", "desc": "企业经营风险评估，支持5次/月"}
]'::jsonb
WHERE package_id LIKE '%vip%' AND package_id LIKE '%month%';

-- 高级套餐添加权益描述
UPDATE business.member_packages
SET benefits = benefits || '[
    {"title": "发票穿透", "desc": "深度分析发票关联关系，支持50次/月"},
    {"title": "全景报告", "desc": "企业全景数据报告，支持30次/月"},
    {"title": "经营风险", "desc": "企业经营风险评估，支持30次/月"}
]'::jsonb
WHERE package_id LIKE '%premium%';

-- 企业套餐添加权益描述
UPDATE business.member_packages
SET benefits = benefits || '[
    {"title": "发票穿透", "desc": "深度分析发票关联关系，无限次使用"},
    {"title": "全景报告", "desc": "企业全景数据报告，无限次使用"},
    {"title": "经营风险", "desc": "企业经营风险评估，无限次使用"}
]'::jsonb
WHERE package_id LIKE '%enterprise%';

-- =====================================================
-- 完成迁移
-- =====================================================
-- 说明：
-- -1 表示无限使用
-- 0 表示不启用该功能
-- 正数表示每月可用次数
