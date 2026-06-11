-- =====================================================
-- 为所有套餐添加发票穿透、全景报告、经营风险功能
-- 根据套餐等级和价格合理分配配额（最多5次/月）
-- =====================================================

-- V3钻石会员（高价位）- 5次/月
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
                        '5'::jsonb
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
    ),
    benefits = benefits || '[
        {"title": "发票穿透", "desc": "深度分析发票关联关系，支持5次/月"},
        {"title": "全景报告", "desc": "企业全景数据报告，支持5次/月"},
        {"title": "经营风险", "desc": "企业经营风险评估，支持5次/月"}
    ]'::jsonb
WHERE package_id IN ('v3_diamond_month', 'v3_diamond_year');

-- V2黄金会员（中价位）- 3次/月
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
                        '3'::jsonb
                    ),
                    '{enable_panorama}',
                    'true'::jsonb
                ),
                '{max_panorama}',
                '3'::jsonb
            ),
            '{enable_business_risk}',
            'true'::jsonb
        ),
        '{max_business_risk}',
        '3'::jsonb
    ),
    benefits = benefits || '[
        {"title": "发票穿透", "desc": "深度分析发票关联关系，支持3次/月"},
        {"title": "全景报告", "desc": "企业全景数据报告，支持3次/月"},
        {"title": "经营风险", "desc": "企业经营风险评估，支持3次/月"}
    ]'::jsonb
WHERE package_id IN ('v2_gold_month', 'v2_gold_year');

-- V1铂金会员（中低价位）- 2次/月
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
                        '2'::jsonb
                    ),
                    '{enable_panorama}',
                    'true'::jsonb
                ),
                '{max_panorama}',
                '2'::jsonb
            ),
            '{enable_business_risk}',
            'true'::jsonb
        ),
        '{max_business_risk}',
        '2'::jsonb
    ),
    benefits = benefits || '[
        {"title": "发票穿透", "desc": "深度分析发票关联关系，支持2次/月"},
        {"title": "全景报告", "desc": "企业全景数据报告，支持2次/月"},
        {"title": "经营风险", "desc": "企业经营风险评估，支持2次/月"}
    ]'::jsonb
WHERE package_id IN ('v1_platinum_month', 'v1_platinum_year');

-- 基础会员（低价位）- 1次/月
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
                        '1'::jsonb
                    ),
                    '{enable_panorama}',
                    'true'::jsonb
                ),
                '{max_panorama}',
                '1'::jsonb
            ),
            '{enable_business_risk}',
            'true'::jsonb
        ),
        '{max_business_risk}',
        '1'::jsonb
    ),
    benefits = benefits || '[
        {"title": "发票穿透", "desc": "深度分析发票关联关系，支持1次/月"},
        {"title": "全景报告", "desc": "企业全景数据报告，支持1次/月"},
        {"title": "经营风险", "desc": "企业经营风险评估，支持1次/月"}
    ]'::jsonb
WHERE package_id IN ('basic_month', 'basic_year');

-- 免费会员 - 不启用这些高级功能（0次）
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
WHERE package_id = 'free';

-- =====================================================
-- 完成迁移
-- =====================================================
-- 配额分配说明：
-- V4黑金: 无限次 (-1)
-- V3钻石: 5次/月
-- V2黄金: 3次/月
-- V1铂金: 2次/月
-- 基础:   1次/月
-- 免费:   不启用 (0)
