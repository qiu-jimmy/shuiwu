# -*- coding: utf-8 -*-
"""
企业体检报告生成器 - 启动文件
所有配置参数写死在代码中
"""
import asyncio
from pathlib import Path
from datetime import datetime

from quote_generator import QuoteGenerator
from quote_number_generator import QuoteNumberGenerator
from document_generators import PandocDocumentGenerator


# ==================== 配置参数 ====================
# API密钥
API_KEY = "sk-4d31a20cdabe43b5b21372c27ebdfa2c"

# 企业资料内容（写死，不再读取/解析上传文件）
REQUIREMENT_TEXT = r"""1.1.1.11）企业信息

企业名称：杭州某某科技有限公司统一社会信用代码：9133XXXXXXXXXXXXXX注册地址：浙江省杭州市XX区XX路XX号成立时间：2021-06-18法定代表人：张三企业类型：有限责任公司员工人数：45人主营业务：为连锁门店提供SaaS管理系统、会员营销系统及数据分析服务收入模式：软件订阅费（年费/季费）、实施服务费、少量硬件代采服务费主要客户类型：本地生活服务行业连锁门店（餐饮/美容/足浴）主要供应商类型：云服务商、短信/支付等第三方服务商、外包开发团队（偶发）开票情况：对客户开具增值税发票；对供应商取得增值税发票纳税人资质：一般纳税人主要税种：增值税、企业所得税、个税代扣代缴情形（工资薪金/劳务）

1.1.1.22）客户身份识别（KYC）

客户类型：企业客户为主，少量个体工商户客户准入流程：销售提交客户信息→财务复核开票信息→签署合同→交付与验收客户识别信息来源：营业执照、法人/经办人身份证复印件、对公账户信息、合同盖章件受益所有人识别：通常仅核验法定代表人及股东信息，未形成标准化“受益所有人”记录高风险特征排查：未建立统一黑名单/制裁名单筛查；对异常交易（大额一次性付款、频繁退款）缺少书面留痕

1.1.1.33）合作与交易风险排查

合作对象：云服务商、支付/短信服务商、外包团队（按项目结算）合作合同管理：合同由业务部门发起，法务审核不固定；部分历史合同缺少验收条款费用结算方式：对公转账为主；外包团队偶发使用个人账户收款（需进一步核实）发票与业务匹配：存在“先付款后补票”情况；部分费用类目与合同约定不完全一致收入确认与验收：SaaS订阅按期确认；实施服务费部分项目验收资料不完整关联关系：公司股东名下另有一家咨询公司，曾为本公司客户提供培训服务（需确认是否存在关联交易及定价合理性）

1.1.1.44）已知问题/关注点（可选）

1.进销项发票管理与台账不够完整，缺少可追溯链路（合同-订单-交付-开票-回款）。

1.外包服务存在个人收款可能性，需核实涉税合规与个税代扣义务。

1.关联方交易识别与留存资料不足，需评估转让定价/定价公允性风险。

1.个税代扣代缴：奖金、补贴、劳务报酬等口径不统一，需自查申报准确性。

1.1.1.55）补充说明（可选）

本次材料为初步整理，后续可补充：近12个月纳税申报表、开票汇总、主要合同样本、银行流水摘要、工资表/个税申报记录、关联方清单与交易明细等。
"""

# 企业/项目名称
PROJECT_NAME = "005"

# 输出目录
OUTPUT_DIR = r"C:/Users/29784/Desktop/zhulong/shuiwuAgent/backend_agentsystem_template/test/PythonProject/output"

# 其他参数（固定值）
QUOTE_AMOUNT = 0.0  # 报价金额（不再参与计算，仅用于生成编号）
VALIDITY_DAYS = 30  # 有效期天数
LOGO_PATH = None    # Logo图片路径（None表示不使用）
# ==================== 配置参数结束 ====================


async def generate_report():
    """生成企业体检报告"""
    print("=" * 60)
    print("企业体检报告生成器")
    print("=" * 60)
    
    # 验证输出目录
    output_dir_path = Path(OUTPUT_DIR)
    if not output_dir_path.exists():
        print(f"错误: 输出目录不存在: {OUTPUT_DIR}")
        return
    
    print(f"API密钥: {API_KEY[:10]}...")
    print("企业资料来源: 写死在 src/run.py 的 REQUIREMENT_TEXT")
    print(f"企业/项目名称: {PROJECT_NAME}")
    print(f"输出目录: {OUTPUT_DIR}")
    print("-" * 60)
    
    # 初始化生成器
    print("正在初始化AI生成器...")
    quote_generator = QuoteGenerator(API_KEY)
    number_generator = QuoteNumberGenerator()
    
    # 使用写死的资料内容
    requirement = (REQUIREMENT_TEXT or "").strip()
    if not requirement:
        print("✗ 企业资料内容为空：请在 src/run.py 中配置 REQUIREMENT_TEXT")
        return
    print(f"✓ 已加载企业资料内容，长度: {len(requirement)} 字符")
    
    # 生成报告编号
    print("正在生成报告编号...")
    quote_number = number_generator.generate(QUOTE_AMOUNT)
    print(f"✓ 已生成报告编号: {quote_number}")
    
    # 准备数据
    data = {
        'quote_number': quote_number,
        'date': datetime.now().strftime("%Y年%m月%d日"),
        'validity_days': VALIDITY_DAYS,
        'project_name': PROJECT_NAME,
    }
    
    # 生成实施周期
    print("正在生成改进计划与持续管理...")
    timeline = await quote_generator.generate_implementation_timeline(requirement)
    print("✓ 改进计划与持续管理生成完成")
    
    # 生成完整Markdown文档
    print("正在并行生成所有内容...")
    markdown_content = await quote_generator.generate_all_content_with_titles(
        requirement, PROJECT_NAME, timeline, QUOTE_AMOUNT
    )
    print("✓ 完整 Markdown 文档生成完成")
    
    # 生成文件名
    safe_project_name = "".join(c for c in PROJECT_NAME if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_project_name = safe_project_name.replace(' ', '_')
    filename = f"{safe_project_name}_{quote_number}.docx"
    output_file_path = output_dir_path / filename
    
    # 使用Pandoc转换为Word
    print("正在生成Word文档...")
    try:
        PandocDocumentGenerator.generate_document_from_markdown(
            markdown_content,
            str(output_file_path),
            project_name=PROJECT_NAME,
            quote_number=quote_number,
            date=data.get('date', ''),
            logo_path=LOGO_PATH
        )
        print("✓ Pandoc 转换完成")
    except Exception as e:
        print(f"✗ Word文档生成失败: {e}")
        return
    
    # 完成
    print("=" * 60)
    print("企业体检报告生成完成！")
    print(f"文件已保存至: {output_file_path}")
    print("=" * 60)


def main():
    """主函数"""
    try:
        asyncio.run(generate_report())
    except KeyboardInterrupt:
        print("\n用户中断操作")
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

