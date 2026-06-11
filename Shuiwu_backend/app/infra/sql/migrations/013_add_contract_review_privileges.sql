-- ==================================================
-- 合同审查权限配置迁移
-- ==================================================
-- 为套餐添加合同审查相关权限字段
-- contract_screening: 合同筛查（基础版，3页内）
-- contract_review: 合同审查（完整版，多页合同）
-- ==================================================

-- 更新基础会员套餐（启用合同筛查）
UPDATE business.member_packages
SET
    custom_config = jsonb_set(
        jsonb_set(
            custom_config,
            '{enable_contract_screening}',
            'true'::jsonb
        ),
        '{enable_contract_review}',
        'false'::jsonb
    ),
    benefits = jsonb_set(
        benefits,
        (jsonb_array_length(benefits))::text,
        '{"title": "合同筛查", "desc": "3页内合同基础筛查"}'::jsonb
    )
WHERE package_id IN ('basic_month', 'basic_year');

-- 更新 V1铂金会员套餐（启用合同筛查）
UPDATE business.member_packages
SET
    custom_config = jsonb_set(
        jsonb_set(
            custom_config,
            '{enable_contract_screening}',
            'true'::jsonb
        ),
        '{enable_contract_review}',
        'false'::jsonb
    ),
    benefits = jsonb_set(
        benefits,
        (jsonb_array_length(benefits))::text,
        '{"title": "合同筛查", "desc": "3页内合同基础筛查"}'::jsonb
    )
WHERE package_id IN ('v1_platinum_month', 'v1_platinum_year');

-- 更新 V2黄金会员套餐（启用完整合同审查）
UPDATE business.member_packages
SET
    custom_config = jsonb_set(
        jsonb_set(
            custom_config,
            '{enable_contract_screening}',
            'true'::jsonb
        ),
        '{enable_contract_review}',
        'true'::jsonb
    ),
    benefits = jsonb_set(
        benefits,
        (jsonb_array_length(benefits))::text,
        '{"title": "合同审查", "desc": "多页合同审查50页/次"}'::jsonb
    )
WHERE package_id IN ('v2_gold_month', 'v2_gold_year');

-- 更新 V3钻石会员套餐（启用完整合同审查，合同筛查无限）
UPDATE business.member_packages
SET
    custom_config = jsonb_set(
        jsonb_set(
            custom_config,
            '{enable_contract_screening}',
            'true'::jsonb
        ),
        '{enable_contract_review}',
        'true'::jsonb
    ),
    benefits = jsonb_set(
        benefits,
        (jsonb_array_length(benefits))::text,
        '{"title": "合同审查", "desc": "多页合同审查50页/次"}'::jsonb
    )
WHERE package_id IN ('v3_diamond_month', 'v3_diamond_year');

-- 更新 V4黑金会员套餐（启用完整合同审查，无限）
UPDATE business.member_packages
SET
    custom_config = jsonb_set(
        jsonb_set(
            custom_config,
            '{enable_contract_screening}',
            'true'::jsonb
        ),
        '{enable_contract_review}',
        'true'::jsonb
    ),
    benefits = jsonb_set(
        benefits,
        (jsonb_array_length(benefits))::text,
        '{"title": "合同审查", "desc": "无限合同审查"}'::jsonb
    )
WHERE package_id = 'v4_black_gold_year';
