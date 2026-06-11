#!/usr/bin/env python
"""
合同审查权限迁移脚本
"""
import os
import sys
import json
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 从环境变量获取数据库连接信息
host = os.getenv('PG_HOST', 'localhost')
port = os.getenv('PG_PORT', '5432')
user = os.getenv('PG_USER', 'postgres')
password = os.getenv('PG_PASSWORD', 'root')
database = os.getenv('PG_DATABASE', 'Agno')

# 创建同步引擎
engine = create_engine(f'postgresql+psycopg://{user}:{password}@{host}:{port}/{database}')

# 套餐权限配置
package_configs = {
    'basic_month': {'enable_contract_screening': True, 'enable_contract_review': False},
    'basic_year': {'enable_contract_screening': True, 'enable_contract_review': False},
    'v1_platinum_month': {'enable_contract_screening': True, 'enable_contract_review': False},
    'v1_platinum_year': {'enable_contract_screening': True, 'enable_contract_review': False},
    'v2_gold_month': {'enable_contract_screening': True, 'enable_contract_review': True},
    'v2_gold_year': {'enable_contract_screening': True, 'enable_contract_review': True},
    'v3_diamond_month': {'enable_contract_screening': True, 'enable_contract_review': True},
    'v3_diamond_year': {'enable_contract_screening': True, 'enable_contract_review': True},
    'v4_black_gold_year': {'enable_contract_screening': True, 'enable_contract_review': True},
}

# 执行迁移
try:
    with engine.connect() as conn:
        print("开始更新套餐配置...")

        for package_id, config in package_configs.items():
            # 获取当前 custom_config
            result = conn.execute(
                text("SELECT custom_config FROM business.member_packages WHERE package_id = :package_id"),
                {"package_id": package_id}
            )
            row = result.fetchone()

            if row:
                current_config = row[0] or {}

                # 更新配置
                current_config.update(config)

                # 执行更新
                conn.execute(
                    text("UPDATE business.member_packages SET custom_config = CAST(:config AS jsonb) WHERE package_id = :package_id"),
                    {"config": json.dumps(current_config), "package_id": package_id}
                )

                print(f"  [OK] {package_id}: enable_contract_screening={config['enable_contract_screening']}, enable_contract_review={config['enable_contract_review']}")

        conn.commit()
        print("\nDatabase migration completed successfully!")
        print(f"Updated {len(package_configs)} packages")

except Exception as e:
    print(f"Migration failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
