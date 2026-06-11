"""
执行SQL迁移：添加测试套餐 0.1 - 全权限配置
使用同步数据库连接（psycopg2）
"""
import os
import sys
from pathlib import Path

# 加载 .env 文件
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text


def run_migration():
    """执行迁移脚本"""

    # 从环境变量获取数据库配置
    db_host = os.getenv("PG_HOST", "localhost")
    db_port = os.getenv("PG_PORT", "5432")
    db_user = os.getenv("PG_USER", "postgres")
    db_password = os.getenv("PG_PASSWORD", "")
    db_name = os.getenv("PG_DATABASE", "postgres")

    print(f"连接数据库: {db_user}@{db_host}:{db_port}/{db_name}")

    # 创建同步引擎
    database_url = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    engine = create_engine(database_url, echo=False)

    with engine.begin() as conn:
        # 删除已存在的测试套餐（如果存在）
        delete_sql = text("""
            DELETE FROM business.member_packages WHERE package_id = 'test_01';
        """)

        # 插入测试套餐
        insert_sql = text("""
            INSERT INTO business.member_packages (
                package_id,
                name,
                description,
                package_type,
                price,
                original_price,
                duration_days,
                enable_rag,
                enable_web_search,
                enable_mcp_tools,
                max_daily_chats,
                max_kb_count,
                max_kb_documents,
                max_file_storage_mb,
                max_file_count,
                custom_config,
                benefits,
                status,
                sort_order
            ) VALUES (
                'test_01',
                '测试套餐 0.1',
                '全权限测试套餐 - 包含所有功能权限和无限配额',
                'lifetime',
                0.1,
                0.1,
                36500,
                true,
                true,
                true,
                -1,
                -1,
                -1,
                -1,
                -1,
                '{
                    "priority": 999,
                    "level": "test_full",
                    "enable_advanced_analytics": true,
                    "enable_team_collaboration": true,
                    "enable_api_access": true,
                    "enable_export_data": true,
                    "enable_ai_writing": true,
                    "enable_voice_input": true,
                    "enable_invoice_penetration": true,
                    "enable_panorama": true,
                    "enable_business_risk": true,
                    "enable_contract_screening": true,
                    "enable_contract_review": true,
                    "max_invoice_penetration": -1,
                    "max_panorama": -1,
                    "max_business_risk": -1,
                    "max_contract_review_count": -1,
                    "contract_screening_pages": -1,
                    "multi_page_contract_pages": -1,
                    "expert_followup_available": true,
                    "expert_followup_monthly": -1,
                    "quarterly_consultation_minutes": -1,
                    "ocr_invoice_monthly": -1,
                    "batch_api_available": true,
                    "batch_api_monthly_quota": -1,
                    "risk_indicators_count": -1,
                    "risk_warnings_count": -1,
                    "scenario_metrics_count": -1,
                    "mock_audit_available": true,
                    "risk_assessment_available": true,
                    "real_time_monitoring": true,
                    "strategic_planning_available": true,
                    "dedicated_team_available": true,
                    "dedicated_team_members": 10,
                    "historical_data_retention_months": -1,
                    "enable_basic_calculator": true,
                    "enable_tax_filing_generator": true,
                    "enable_multi_platform_tax": true,
                    "enable_agi_planning": true
                }'::jsonb,
                '[
                    {"title": "无限对话", "desc": "每日无限制AI对话次数"},
                    {"title": "无限知识库", "desc": "支持创建无限数量知识库"},
                    {"title": "无限文档", "desc": "每个知识库支持无限文档数"},
                    {"title": "无限存储", "desc": "云端文件存储空间无限制"},
                    {"title": "RAG增强检索", "desc": "知识库检索增强生成"},
                    {"title": "网络搜索", "desc": "支持实时网络搜索功能"},
                    {"title": "MCP工具", "desc": "支持MCP扩展工具调用"},
                    {"title": "发票穿透", "desc": "无限次发票穿透分析"},
                    {"title": "全景报告", "desc": "无限次全景报告生成"},
                    {"title": "经营风险查询", "desc": "无限次经营风险查询"},
                    {"title": "合同筛查", "desc": "无限页合同筛查"},
                    {"title": "合同审查", "desc": "无限页多页合同审查"},
                    {"title": "专家追问", "desc": "无限次专家追问"},
                    {"title": "季度咨询", "desc": "无限时长季度咨询服务"},
                    {"title": "批量API", "desc": "无限次批量API调用"},
                    {"title": "专属团队", "desc": "10人专属服务团队"},
                    {"title": "数据保留", "desc": "永久历史数据保留"},
                    {"title": "高级分析", "desc": "高级数据分析功能"},
                    {"title": "团队协作", "desc": "团队协作功能"},
                    {"title": "API访问", "desc": "完整API访问权限"},
                    {"title": "数据导出", "desc": "数据导出功能"},
                    {"title": "AI写作", "desc": "AI辅助写作功能"},
                    {"title": "语音输入", "desc": "语音输入功能"},
                    {"title": "稽查模拟", "desc": "税务稽查模拟功能"},
                    {"title": "风险评估", "desc": "税务风险评估功能"},
                    {"title": "实时监控", "desc": "实时税务监控"},
                    {"title": "战略筹划", "desc": "税务战略筹划"},
                    {"title": "基础计算器", "desc": "税费计算器"},
                    {"title": "申报生成器", "desc": "税务申报生成器"},
                    {"title": "多平台税", "desc": "多平台税务管理"},
                    {"title": "AGI筹划", "desc": "AGI智能筹划"}
                ]'::jsonb,
                'active',
                999
            );
        """)

        # 验证查询
        verify_sql = text("""
            SELECT
                package_id,
                name,
                price,
                enable_rag,
                enable_web_search,
                enable_mcp_tools,
                max_daily_chats,
                custom_config->'priority' as priority,
                custom_config->'enable_invoice_penetration' as enable_invoice_penetration,
                custom_config->'max_invoice_penetration' as max_invoice_penetration,
                jsonb_array_length(benefits) as benefits_count
            FROM business.member_packages
            WHERE package_id = 'test_01';
        """)

        # 执行删除
        print("删除已存在的测试套餐（如果有）...")
        conn.execute(delete_sql)

        # 执行插入
        print("插入测试套餐 0.1...")
        conn.execute(insert_sql)

        # 验证结果
        print("\n验证插入结果:")
        result = conn.execute(verify_sql)
        rows = result.fetchall()

        if rows:
            print("\n测试套餐创建成功!")
            for row in rows:
                print(f"  - package_id: {row[0]}")
                print(f"  - name: {row[1]}")
                print(f"  - price: {row[2]}")
                print(f"  - enable_rag: {row[3]}")
                print(f"  - enable_web_search: {row[4]}")
                print(f"  - enable_mcp_tools: {row[5]}")
                print(f"  - max_daily_chats: {row[6]}")
                print(f"  - priority: {row[7]}")
                print(f"  - enable_invoice_penetration: {row[8]}")
                print(f"  - max_invoice_penetration: {row[9]}")
                print(f"  - benefits_count: {row[10]}")
        else:
            print("未找到插入的套餐，请检查错误")

    print("\n迁移完成!")


if __name__ == "__main__":
    run_migration()
