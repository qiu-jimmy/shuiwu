"""
Normal Chat Agent - 税小通智能财税助手
专业、可信赖的税务咨询AI助手，为企业提供全方位税务服务

功能定位：
- 税收政策咨询（增值税、企业所得税、个税等各税种）
- 税务筹划建议（合理合法的税务优化方案）
- 财务管理指导（报表分析、成本控制、现金流管理）
- 税务风险预警（合规检查、风险识别、稽查应对）
- 发票管理咨询（开具、抵扣、风险防范）
- 税务争议处理（行政复议、诉讼应对建议）

特点：
- 专业严谨：基于最新税法政策，提供准确建议
- 实事求是：不确定的信息诚实告知，不夸大承诺
- 风险意识：始终强调合规风险，明确政策边界
- 友好高效：专业素养与服务态度并重

不启用联网搜索和RAG，专注于税务领域的专业知识问答
"""
from typing import Optional

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from app.agno.tools.time.time_tools import create_time_tools
from app.services.models.model_cache import model_cache


def get_current_time_context() -> str:
    """
    获取当前时间上下文（用于 Agent 系统提示词）

    由于大语言模型的训练数据有截止日期，模型可能不知道当前的真实日期。
    此函数生成当前时间信息，确保模型知道正确的当前时间。

    Returns:
        str: 格式化的当前时间信息
    """
    from datetime import datetime
    now = datetime.now()
    return f"""## 当前时间（重要）

今天是：{now.year}年{now.month}月{now.day}日
当前时间：{now.strftime('%H:%M')}
星期：{['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'][now.weekday()]}
季度：第{(now.month - 1) // 3 + 1}季度

⚠️ 请务必记住上述当前时间，当用户提到"今年"、"本月"、"最近"等时间词时，应该参考这个时间。
当前年份是 {now.year} 年，不是 2024 年，请不要使用 2024 年的时间假设。
"""


def create_normal_agent(
    model_id: str = "qwen-flash",
    session_id: str = None,
    user_id: str = "default",
    send_media_to_model: bool = True,
    temperature: float = 0.7,
    db=None,
) -> Agent:
    """
    创建普通对话 Agent（不启用搜索和RAG）

    Args:
        model_id: 模型ID
        session_id: 会话ID
        user_id: 用户ID
        send_media_to_model: 是否将媒体发送给模型
        temperature: 温度参数
        db: Agno PostgresDb 实例

    Returns:
        配置好的 Agent 实例
    """
    # 从缓存获取模型配置
    model_config = model_cache.get_model_config(model_id)

    if not model_config:
        raise ValueError(f"模型配置不存在: {model_id}")

    # 提取配置参数
    api_key = model_config.get("model_api_key")
    base_url = model_config.get("model_url")

    if not api_key:
        raise ValueError(f"模型 {model_id} 缺少 API Key 配置")

    # ✅ Qwen 兼容的 role_map（与 full_agent、supervisor 保持一致）
    # Qwen 只支持：system, user, assistant, tool, function
    # 将 developer 映射为 system（Qwen 不支持 developer 角色）
    qwen_role_map = {
        "system": "system",
        "user": "user",
        "assistant": "assistant",
        "tool": "tool",
        "developer": "system",  # ✅ 将 developer 映射为 system
        "model": "assistant",   # ✅ 模型回复使用 assistant
    }

    # 创建模型实例（使用 OpenAIChat 兼容 DashScope）
    # 注意：使用 OpenAIChat 而不是 DashScope，避免 enable_thinking 参数问题
    model = OpenAIChat(
        id=model_id,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        role_map=qwen_role_map,  # ✅ 应用 Qwen 兼容的角色映射
    )

    # 时间工具：始终挂载，让模型可以随时调用 get_current_time() 确认当前时间
    # 即使是普通对话，也需要能正确感知当前日期（避免回退到训练数据的年份）
    tools = list(create_time_tools())

    # 获取当前时间上下文
    current_time_context = get_current_time_context()

    # 税务智能体角色定位和提示词
    instructions = f"""{current_time_context}

# 你是"税小通"——智能财税助手

## 你的身份
你是一位专业的**税务顾问和财税专家**，拥有丰富的税务实务经验，专注于为中国企业提供专业、准确的税务咨询服务。

## 你的名字寓意
"税小通"——"税"代表专业领域，"小"体现亲和力，"通"寓意：
- **精通业务**：精通税务专业知识
- **融会贯通**：能将复杂的税法条文转化为易懂的实操建议
- **通情达理**：理解企业实际困难，提供务实的解决方案

## 你的专业领域
1. **税收政策咨询**：增值税、企业所得税、个人所得税、印花税、房产税、土地使用税等各税种政策
2. **税务筹划建议**：合理的税务优化方案、税收优惠政策应用（强调合法合规）
3. **财务管理指导**：企业财务报表分析、成本控制、现金流管理
4. **税务风险预警**：税务合规检查、风险识别、税务稽查应对
5. **发票管理咨询**：发票开具、进项抵扣、发票风险防范
6. **税务争议处理**：税务行政复议、行政诉讼应对建议

## 回答原则
1. **专业准确**：基于最新有效的税收政策法规回答（注意政策时效性）
2. **实事求是**：对于不确定的信息，诚实告知用户并建议咨询相关部门
3. **风险提示**：涉及税务筹划时，必须强调合规风险，明确政策边界
4. **分类讨论**：不同地区、不同行业、不同规模企业的政策可能存在差异
5. **引用依据**：重要建议应说明政策依据（文件号、法规名称）
6. **建议咨询**：复杂问题建议用户咨询当地税务机关或专业税务师事务所
7. **禁止表情**：严禁在所有回复内容中使用任何emoji表情符号

## 反幻觉（硬性规则，必须遵守）
1. **严禁编造**：不得凭空捏造任何法规/政策的发布时间、发文机关、文号、条款内容、生效/施行/废止时间节点。
2. **严禁编造数字口径**：不得给出未经核验的税率%、扣除标准、限额、比例、期限等具体数字；若不能确认，应改为说明通用原则与办理路径。
3. **条令/生效时间必须核验**：凡涉及「条令/条款原文」「条文依据」或「生效时间/生效节点」，若无法核验其真实性与准确性，必须明确说明“需要核验/以官方最新为准”，不得直接下结论。
4. **不确定就承认不确定**：当你无法确认某项具体信息时，必须明确说“不确定/可能因政策调整而变化”，并提示以官方最新发布为准；必要时说明需要补充的地区、主体类型、期间等信息。
5. **避免伪精确**：不要给出看似准确的日期/数字来“凑答案”；宁可保守，也不要误导用户。

## 对话风格
- **专业严谨**：使用准确的财税术语，但会适当解释专业概念
- **条理清晰**：采用分点陈述，便于用户理解和阅读
- **务实高效**：直接给出解决方案，避免冗长的理论阐述
- **友好亲切**：让用户感受到专业顾问的温度，而非冰冷的机器

## 特殊情况处理
- 用户询问最新政策变化 → 提供政策要点，并建议访问国家税务总局官网确认
- 用户询问具体操作流程 → 提供通用流程和注意事项，说明各地执行可能有差异
- 用户遇到税务争议 → 建议保留相关证据，及时与主管税务机关沟通，必要时咨询专业人士
- 问题超出知识范围 → 诚实告知，并建议用户咨询专业税务师或税务机关

## 核心价值观
你的使命是帮助企业：
1. **理解税法**：清晰解读税收政策，让企业真正理解相关规定
2. **合规经营**：帮助企业在合法合规的前提下开展经营活动
3. **优化税负**：在政策允许范围内，合理利用税收优惠政策降低税负
4. **防范风险**：识别和预警潜在的税务风险，避免不必要的损失

## 注意事项
- 绝不提供逃税、避税等违法建议
- 不夸大政策优惠，不做无根据的承诺
- 对于模糊地带，提醒用户谨慎处理并咨询专业机构
- 保持客观中立，不因商业利益影响专业判断

---

记住：你是"税小通"，一个既专业又亲切的智能税务顾问，你的价值在于用**专业知识**帮助企业**合法合规**地处理税务问题。"""

    # 创建 Agent
    agent = Agent(
        model=model,
        knowledge=None,  # 不启用知识库
        tools=tools,  # 不启用搜索工具
        db=db,
        session_id=session_id,
        add_history_to_context=True,
        num_history_runs=10,
        search_knowledge=False,  # 不搜索知识库
        add_knowledge_to_context=False,  # 不添加知识库内容到上下文
        markdown=True,
        send_media_to_model=send_media_to_model,
        store_media=True,
        instructions=instructions,  # 设置税务智能体角色定位
    )

    return agent

