#!/usr/bin/env python
"""
合同审查次数配额迁移脚本
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

# 套餐配额配置（max_contract_review_count: -1 表示无限）
package_quotas = {
    'basic_month': {'max_contract_review_count': 5, 'contract_review_count_used': 0},
    'basic_year': {'max_contract_review_count': 10, 'contract_review_count_used': 0},
    'v1_platinum_month': {'max_contract_review_count': 10, 'contract_review_count_used': 0},
    'v1_platinum_year': {'max_contract_review_count': 20, 'contract_review_count_used': 0},
    'v2_gold_month': {'max_contract_review_count': 30, 'contract_review_count_used': 0},
    'v2_gold_year': {'max_contract_review_count': 50, 'contract_review_count_used': 0},
    'v3_diamond_month': {'max_contract_review_count': 100, 'contract_review_count_used': 0},
    'v3_diamond_year': {'max_contract_review_count': 200, 'contract_review_count_used': 0},
    'v4_black_gold_year': {'max_contract_review_count': -1, 'contract_review_count_used': 0},  # 无限
}

# 执行迁移
try:
    with engine.connect() as conn:
        print("开始更新套餐配额配置...")

        for package_id, quota in package_quotas.items():
            # 获取当前 custom_config
            result = conn.execute(
                text("SELECT custom_config FROM business.member_packages WHERE package_id = :package_id"),
                {"package_id": package_id}
            )
            row = result.fetchone()

            if row:
                current_config = row[0] or {}

                # 更新配额配置
                current_config.update(quota)

                # 执行更新
                conn.execute(
                    text("UPDATE business.member_packages SET custom_config = CAST(:config AS jsonb) WHERE package_id = :package_id"),
                    {"config": json.dumps(current_config), "package_id": package_id}
                )

                max_count = quota['max_contract_review_count']
                display = '无限' if max_count == -1 else str(max_count)
                print(f"  [OK] {package_id}: max_contract_review_count={display}")

        conn.commit()
        print("\nDatabase migration completed successfully!")
        print(f"Updated {len(package_quotas)} packages")

except Exception as e:
    print(f"Migration failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
