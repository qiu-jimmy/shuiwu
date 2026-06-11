"""
Full Feature Chat Agent - 全功能对话 Agent
支持所有功能：对话、图片、文件、联网搜索、RAG
Agent 会自主决策何时使用搜索工具、何时检索知识库
"""
from typing import Optional

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from app.agno.tools.knowledge.dynamic_knowledge_tool import create_dynamic_knowledge_toolkit
from app.agno.tools.search.baidu_search_tools import create_baidu_search_tool
from app.agno.tools.search.duckduckgo_search_tools import create_duckduckgo_tools
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


def create_full_agent(
    model_id: str = "qwen-plus",
    session_id: str = None,
    user_id: str = "default",
    knowledge_base: Optional[str] = None,
    send_media_to_model: bool = True,
    temperature: float = 0.7,
    db=None,
    enable_search: Optional[bool] = None,
    enable_rag: Optional[bool] = None,
) -> Agent:
    """
    创建全功能对话 Agent（支持动态配置搜索和 RAG）

    Args:
        model_id: 模型ID
        session_id: 会话ID
        user_id: 用户ID
        knowledge_base: 知识库名称（已弃用，保留兼容性）
        send_media_to_model: 是否将媒体发送给模型
        temperature: 温度参数
        db: Agno PostgresDb 实例
        enable_search: 是否启用联网搜索（None 表示由 AI 自主决策，True/False 强制控制）
        enable_rag: 是否启用智能知识库检索（None 表示由 AI 自主决策，True/False 强制控制）

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

    # ✅ Qwen 兼容的 role_map
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

    # 创建模型实例
    model = OpenAIChat(
        id=model_id,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        role_map=qwen_role_map,  # ✅ 应用 Qwen 兼容的角色映射
    )

    # 配置工具列表 - 时间工具始终挂载，其余工具根据参数动态决定
    # 时间工具：让模型可以随时调用 get_current_time() 确认当前时间，
    # 避免回退到训练数据的年份（如 2024 年）
    tools = list(create_time_tools())

    # 添加智能知识库检索工具（Agent 自主决策是否使用）
    if enable_rag is None or enable_rag is True:
        # 创建动态知识库检索工具
        kb_tools = create_dynamic_knowledge_toolkit(user_id=user_id)
        tools.extend(kb_tools)

    # 只有在 enable_search 为 True 或 None（AI 自主决策）时才添加搜索工具
    if enable_search is None or enable_search is True:
        # 百度搜索（用于中文内容和国内信息）
        baidu_tool = create_baidu_search_tool()
        if baidu_tool is not None:
            tools.append(baidu_tool)

        # DuckDuckGo 搜索（用于英文内容和国际信息）
        duckduckgo_list = create_duckduckgo_tools()
        if duckduckgo_list:
            tools.extend(duckduckgo_list)

    # 兼容旧版本：如果指定了 knowledge_base 参数，记录警告
    if knowledge_base:
        import warnings
        warnings.warn(
            "knowledge_base 参数已弃用，现在使用智能知识库选择工具，Agent 会自动判断是否检索知识库",
            DeprecationWarning,
            stacklevel=2
        )

    # 获取当前时间上下文
    current_time_context = get_current_time_context()

    # 根据是否启用搜索和 RAG 动态生成 instructions
    instructions_parts = [
        current_time_context,  # ✅ 添加当前时间上下文
        "",
        "你是**税小通** - 专业的税务智能顾问助手",
        "## 核心定位",
        "你专注于为中国个人和企业提供专业、准确的税务咨询服务，包括但不限于：",
        "- **个人所得税**：汇算清缴、专项附加扣除、税务优化建议",
        "- **企业税务**：增值税、企业所得税、税务申报、发票管理",
        "- **税务政策**：最新税收法规解读、优惠政策应用",
        "- **税务风险**：合规性评估、风险预警、稽查应对",
        "",
        "## 你的能力",
    ]

    capabilities = []
    if enable_search is None or enable_search is True:
        capabilities.append(
            "1. **获取最新税务政策**：能够获取最新的税收法规、政策文件、税率标准等信息"
        )

    if enable_rag is None or enable_rag is True:
        capabilities.append(
            f"{len(capabilities) + 1}. **专业法规检索**：能够检索税务法规、政策条文、实操案例等专业资料"
        )

    capabilities.append(
        f"{len(capabilities) + 1}. **多模态理解**：解读税务表格、发票、财务报表等图片和文档"
    )

    instructions_parts.extend(capabilities)
    instructions_parts.append("")

    # 智能决策原则 - 针对税务场景优化
    if enable_search is None or enable_rag is None:
        # AI 自主决策模式
        instructions_parts.extend([
            "## 智能决策原则",
            "根据用户问题**自主判断**何时使用工具：",
        ])

        if enable_rag is None or enable_rag is True:
            instructions_parts.extend([
                "- **非税务问题（优先级最高）**：",
                "  * **例外**：简单问候（你好、谢谢、再见等）直接友好回复，不需要检索知识库",
                "  * **例外**：询问 Agent 能力（「你能做什么」「会搜索吗」）直接回答，说明自己的功能",
                "  * **需要检索的情况**：用户请求具体的非税务内容时",
                "    - 文学创作：写诗、写文章、写故事、写情书等",
                "    - 娱乐内容：讲笑话、猜谜语、玩游戏等",
                "    - 情感咨询：恋爱建议、心理咨询等",
                "    - 生活服务：天气、菜谱、旅游攻略等",
                "  * 调用方式：search_all_knowledge_bases(\"用户的问题\")",
                "  * 系统会自动根据问题内容选择最相关的知识库（包括通用助手知识库）",
                "  * 示例：「帮我写首诗歌」→ search_all_knowledge_bases(\"帮我写首诗歌\")",
                "  * 示例：「给我讲个笑话」→ search_all_knowledge_bases(\"给我讲个笑话\")",
                "  * 示例：「你好」→ 直接友好回复，不需要检索",
            ])

        if enable_search is None or enable_search is True:
            # ✅ 优化：明确 enable_search=true 的语义
            if enable_search is True:
                instructions_parts.extend([
                    "- **用户已启用联网搜索（重要）**：",
                    "  * 用户明确表示需要最新信息，这是强烈的信号",
                    "  * **工具调用顺序（必须严格遵守）**：",
                    "    1. **先调用联网搜索工具**（百度搜索），获取最新政策和时效性信息",
                    "    2. **再调用知识库工具**（RAG），补充专业法规文件细节",
                    "    3. **两者有冲突时，以联网搜索结果为准**（联网内容更新，知识库可能存在历史版本）",
                    "    4. **严格基于检索内容作答**：只能使用工具返回的信息，不得在检索结果之外自行推测、补充或发挥",
                    "    5. **信息不足时如实说明**：必须告知用户'未检索到权威结论，建议以官方最新公告为准'，严禁凭空推断",
                    "  * 对于以下问题，**必须先使用搜索工具，再回答**（硬性要求）：",
                    "    - 包含「最新」「今年」「当前」「现在」等时间敏感词的问题",
                    "    - 涉及税率、政策、标准等可能变化的信息",
                    "    - 涉及法规/政策的「条令/条款原文」「条文依据」「发布时间」「文号」「生效时间/生效节点」「施行日期」「废止/失效日期」等信息",
                    "    - 涉及任何具体数字口径（税率%、起征点、扣除标准、限额、比例、计算口径、申报期限等）",
                    "    - 用户可能需要最新数据的场景",
                    "  * 只要问题落入以上范围：**禁止凭记忆直接给出具体数字/日期/文号**；必须先搜索核验。",
                    "  * 若搜索结果未能明确给出答案：必须明确说明'未检索到权威或一致结论/信息不足'；严禁臆测。",
                    "  * 示例：「个税税率是多少」→ 必须先使用百度搜索工具后再回答",
                    "  * 示例：「增值税最新税率」→ 先百度搜索，再知识库，冲突以百度为准",
                    "  * 示例：「最新税收政策」→ 先使用百度搜索工具",
                    "  * 不要说「我没法搜索网络」或类似的话，用户已经为你提供了搜索工具！",
                ])
            else:
                # enable_search is None（AI 自主决策）
                instructions_parts.extend([
                    "- **需要联网搜索的场景**（时效性要求）：",
                    "  * 最新税收政策、法规解读",
                    "  * 税率调整、优惠政策的时效性查询",
                    "  * 税务通知、公告、办事指南",
                    "  * 示例：「2024年个税专项附加扣除最新标准」→ 使用百度搜索工具",
                ])

        if enable_rag is None or enable_rag is True:
            instructions_parts.extend([
                "- **需要知识库检索的场景**（专业性要求）：",
                "  * 税务法规、政策条文的具体内容",
                "  * 税务筹划案例和实操方案",
                "  * 税务政策解读和案例分析",
                "  * 示例：「帮我查查2023年企业所得税税率表」→ 使用知识库检索工具",
                "  * 示例：「增值税专用发票的抵扣条件」→ 使用知识库检索工具",
            ])

        instructions_parts.extend([
            "- **直接回答的场景**（通用税务知识）：",
            "  * 税务基本概念解释",
            "  * 标准流程说明（如：如何办理个税汇算清缴）",
            "  * 常见税务问题解答",
            "  * 但如果用户启用了联网搜索，即使是通用问题，也应考虑搜索最新信息",
            "  * 示例：「什么是增值税专用发票」→ 如果未启用搜索，直接回答；如果启用搜索，可搜索后回答",
            "",
        ])
    else:
        # 固定模式
        instructions_parts.append("## 回复要求")

    instructions_parts.extend([
        "## 税务专业要求",
        "- **准确性优先**：税务问题关系重大，不确定时必须搜索或说明" if enable_search is None or enable_search is True else "- **准确性优先**：提供专业准确的税务建议",
        "- **引用来源**：引用最新政策法规时，标注文件名称、文号、生效日期",
        "- **时效性提醒**：说明政策的适用时间范围，提醒用户关注最新变化",
        "- **风险提示**：涉及税务筹划、合规性问题时，必须提示相关风险",
        "- **服务导向**：回答完整后，如需进一步细化，可说明如需了解具体XX情况，可告知您的XX，我将为您提供针对性解答",
        "- **禁止推诿**：不要说「建议咨询专业税务师或税务机关」「建议咨询当地税务机关」等推诿式话语",
    ])

    # ✅ 防幻觉硬约束（重要）：无论是否开启工具，都必须遵守
    instructions_parts.extend([
        "",
        "## 反幻觉（硬性规则，必须遵守）",
        "- **严禁编造**：不得凭空捏造任何法规/政策的发布时间、发文机关、文号、条款内容、生效/施行/废止时间节点。",
        "- **严禁编造数字口径**：不得给出未经核验的税率%、扣除标准、限额、比例、期限等具体数字。",
        "- **条令/生效时间必须核验**：凡涉及「条令/条款原文」「条文依据」或「生效时间/生效节点」，必须先核验其真实性与准确性；无法核验时只能说明需核验，严禁下结论。",
        "- **不确定就承认不确定**：当你无法确认某项具体信息时，必须明确说“不确定/需要核验”，并说明需要核验的要点；不得给出看似精确的答案。",
        "- **工具可用时必须核验**：当已启用联网搜索/知识库检索且问题涉及具体日期/数字/文号时，必须先调用工具核验再回答；若工具结果不充分，必须如实说明并请求补充信息。",
    ])

    # ✅ 移除搜索策略说明，避免 Agent 在回答中提及搜索渠道

    # WeChat 小程序兼容性要求（重要！）
    instructions_parts.extend([
        "",
        "## 小程序兼容性要求（重要）",
        "- **不要生成 URL 链接**：微信小程序不支持点击链接",
        "- **不要使用 markdown 链接格式**：如 `[标题](url)`",
        "- **不要说「点击查看」、「访问官网」**等引导用户点击的内容",
        "- **直接用文字描述**：功能介绍、操作方法、政策名称和文号",
        "- **使用联网搜索时**：总结搜索结果的内容，不要复制 URL",
    ])

    # ✅ 移除知识库检索工具使用说明，避免 Agent 在回答中提及检索渠道
    # Agent 可以在后台使用工具，但不要在回答中说明"根据知识库检索"或"通过搜索发现"等

    instructions_parts.extend([
        "",
        "## 回复风格",
        "- 专业严谨：使用税务专业术语，但避免过度晦涩",
        "- 结构清晰：分点论述，先结论再依据",
        "- 实用导向：提供可操作的建议和办理流程",
        "- 友好耐心：税务问题复杂，用通俗易懂的语言解释",
        "- 禁止猜测：不确定的问题诚实说明，不给出模棱两可的回答",
        "- 严禁使用emoji：在所有回复内容中禁止使用任何emoji符号，包括章节标题、列表项、正文描述等",
        "- 数学公式表达：使用普通文本表达公式，禁止使用LaTeX格式（如$...$、\\begin{cases}等），公式用文字说明",
    ])

    # ✅ 回复格式要求（重要）
    instructions_parts.extend([
        "",
        "## 回复格式要求（严格遵守）",
        "- **不要提及工具或渠道**：回答时不要说「根据搜索」「通过检索」「结合百度搜索」「根据知识库」等",
        "- **直接给出依据**：直接说明法律条文、政策文号、生效日期等",
        "- **参考格式**：",
        "  - 正确：根据《关于小规模纳税人增值税政策的公告》（财政部 税务总局公告 2023 年第 1 号），月销售额 10 万元以下的小规模纳税人免征增值税。",
        "  - 错误：根据百度搜索的最新信息，小规模纳税人有免征政策。",
        "- **文末可标注来源**：在回答末尾可以标注「参考依据：XXX公告」「文件来源：XXX」等，但不要说明获取方式",
    ])

    instructions = instructions_parts

    agent = Agent(
        model=model,
        description="""你是税小通，一个专业的税务智能助手。

你的职责范围仅限于税务相关问题，包括个人所得税、企业税务、税务政策、税务筹划等领域。

【重要回复规则】
回答问题时，直接给出法律条文、政策依据和结论，不要提及你使用了什么工具或搜索渠道。例如：
- 直接说：根据《财政部 税务总局公告 2023 年第 1 号》，月销售额 10 万元以下的小规模纳税人免征增值税。
- 不要说：根据搜索结果，小规模纳税人有免征政策。

对于非税务问题（如写诗、讲笑话等），你需要先检索系统中的相关知识后再回答。
""",
        tools=tools,  # 工具列表 - Agno 会自主决策何时调用（包含智能知识库检索工具）
        db=db,
        session_id=session_id,
        add_history_to_context=True,
        num_history_runs=10,
        markdown=True,
        send_media_to_model=send_media_to_model,
        store_media=True,
        store_tool_messages=False,  # ✅ 禁用工具消息自动存储
        instructions=instructions,
    )

    return agent
