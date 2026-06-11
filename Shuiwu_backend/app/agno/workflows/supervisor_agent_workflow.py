"""
Supervisor-Agent Workflow - 领导-专家模式工作流

架构特点：
- Supervisor Agent（领导）先分析用户输入
- 判断是否与税务相关、简单问答
- 输出结构化决策（工具、RAG、搜索等）
- Workflow 根据决策动态调用专业 Agent

与 full_agent 的区别：
- full_agent: Router 直接根据关键词路由
- supervisor: Supervisor Agent 智能分析决策后路由
"""
import json
import logging
import re
import uuid
import time
from typing import Dict, List, Optional, Union

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.workflow import Workflow, Router, Step, StepInput
from agno.tools.calculator import CalculatorTools
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.agno.tools.search.baidu_search_tools import create_baidu_search_tool
from app.agno.tools.search.duckduckgo_search_tools import create_duckduckgo_tools
from app.agno.tools.knowledge.dynamic_knowledge_tool import create_dynamic_knowledge_toolkit
from app.agno.tools.time.time_tools import create_time_tools
from app.infra.db import DATABASE_URL_ASYNC
from app.services.models.model_cache import model_cache

logger = logging.getLogger(__name__)


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


def create_supervisor_agent(
    model_id: str = "qwen-flash",  # ✅ 默认使用 qwen-flash（响应最快）
    temperature: float = 0.3,
    db=None,
    session_id: str = None,
    user_id: str = "default",
) -> Agent:
    """
    创建 Supervisor Agent（领导 Agent）

    职责：
    1. 分析用户输入类型
    2. 判断是否需要专业 Agent 处理
    3. 输出结构化决策（工具配置、Agent 选择）

    Args:
        model_id: 模型 ID（默认 qwen-flash，响应最快）
        temperature: 温度参数
        db: 数据库实例（用于保存推理过程）
        session_id: 会话 ID
        user_id: 用户 ID

    Returns:
        Supervisor Agent 实例
    """
    model_config = model_cache.get_model_config(model_id)
    if not model_config:
        raise ValueError(f"模型配置不存在: {model_id}")

    api_key = model_config.get("model_api_key")
    base_url = model_config.get("model_url")

    if not api_key:
        raise ValueError(f"模型 {model_id} 缺少 API Key 配置")

    # ✅ 自定义 role_map：将 Supervisor Agent 的输出映射为 system
    # 存储时：assistant/model -> system
    # 读取时：system -> system（OpenAI 最经典的角色，所有版本都支持）
    # ✅ Qwen 兼容：developer 角色映射为 system（Qwen 不支持 developer）
    supervisor_role_map = {
        "system": "system",
        "user": "user",
        "assistant": "system",  # Supervisor 推理存储为 system
        "tool": "tool",
        "model": "system",      # 模型回复也存储为 system
        "developer": "system",  # ✅ Qwen 兼容：developer -> system
    }

    model = OpenAIChat(
        id=model_id,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        role_map=supervisor_role_map,  # ✅ 应用自定义角色映射
        assistant_message_role="system",  # ✅ 助手消息角色
    )

    # ✅ 注入当前时间上下文，避免 LLM 错误引用过期年份（如"2024年最新"）
    supervisor_time_context = get_current_time_context()

    agent = Agent(
        name="supervisor_agent",
        model=model,
        instructions=f"""{supervisor_time_context}

你是**税小通**——专业的税务智能助手的工作流程调度器。

## 你的唯一职责
分析用户输入和对话历史，**总是输出 JSON 决策**，派发给合适的专业助手。

## 你不需要直接回答任何问题
无论问题是简单还是复杂，你都需要输出 JSON 格式的决策，派发给对应的专家。

## 对话上下文管理（重要！）
你**能够看到对话历史**，需要负责：
1. **理解上下文**：分析历史对话，理解用户的真实意图
2. **整理上下文**：将必要的上下文信息整合到 `optimized_query` 中
3. **消除歧义**：当代词（它、那个、这个等）需要解释时，在 `optimized_query` 中明确说明

### 示例1（代词消歧）：
- 用户："增值税税率是多少？"
- 用户："它一般是多少？"  ← 你需要将"它"明确为"增值税税率"
- optimized_query: "增值税一般纳税人的税率一般是多少？"

### 示例2（用户信息上下文）：
- 用户："我的名字叫ycc"
- 用户："我叫什么名字？"  ← 你需要将"ycc"告诉专家
- optimized_query: "用户的名字是 ycc，他问'我叫什么名字？'"
- **重要**：即使问题简单，也要在 `optimized_query` 中明确写出用户的名字！

## 图片和文件处理策略
- **任何图片/文件**：都派发给专业助手分析（你不需要直接分析）
- 即使图片清晰、问题简单，也派发给专家处理

## 决策输出格式

**你必须总是输出 JSON 格式的决策**：

```json
{{
  "need_specialist": true,
  "enable_rag": false,
  "enable_search": false,
  "enable_calculator": false,
  "enable_time": false,
  "specialist_agent": "助手名称",
  "reasoning": "派发原因",
  "optimized_query": "优化后的问题（包含必要的上下文）",
  "thought_process": "这里是你的思维链推理过程。详细说明你为什么这样决策，比如：分析用户问题的类型、判断需要什么知识、选择哪个专家助手、为什么启用或禁用某些工具等。这个字段会展示给用户看，让他们了解你的思考过程。"
}}
```

**重要说明**：
- `thought_process` 字段是你的思维链推理过程，会直接展示给用户
- 这个字段应该详细说明你的分析逻辑和决策依据
- 用自然语言描述，类似 DeepSeek 的推理过程，让用户了解你的思考路径

**⚠️ thought_process 字段的格式要求（非常重要）**：

### ✅ 必须遵守的格式：
1. **必须是一段连贯的文字，不要分点列举**
2. **不要使用任何格式标记**（不使用数字序号、不使用符号、不使用 markdown 格式）
3. **就像你在跟朋友说话一样，自然流畅地叙述你的思考过程**

### ✅ 正确示例：
```
用户询问增值税税率，这是一个税收政策问题。我需要派发给税收政策专家，并启用知识库检索功能来查找相关的政策文件。这样可以为用户提供准确且最新的税率信息。
```

### ❌ 错误格式（不要这样写）：
```
1. 用户询问增值税税率
2. 派发给税收政策专家
3. 启用知识库检索
```

### ❌ 错误格式（不要这样写）：
```
- 用户询问增值税税率
- 派发给税收政策专家
- 启用知识库检索
```

## specialist_agent（专业助手）选择规则

| 问题类型 | 派发给 |
|---------|--------|
| 简单问候（你好、谢谢、在吗） | **General Assistant** |
| 时间日期（今天几号、现在几点） | **General Assistant** |
| 自我介绍（介绍一下你） | **General Assistant** |
| 其他简单非税务问题 | **General Assistant |
| 税收政策、法规、文件 | **Tax Policy** |
| 税务计算、税额计算 | **Tax Calculation** |
| 税务筹划、优化建议 | **Tax Planning** |
| 税务风险、合规评估 | **Tax Risk** |
| 图片/文件分析 | **General Tax** |
| 其他税务问题 | **General Tax** |

## 工具配置规则

### enable_rag（知识库检索）
- 询问政策、法规、文件 → true
- 询问"最新"、"现行"政策 → true
- 需要引用具体条款 → true

### enable_search（联网搜索）
- 询问最新新闻、时事 → true
- 询问政策、法规（可能已更新） → true
- 需要实时信息 → true
- **税务相关问题优先启用联网搜索，确保获取最新政策**

### ⚠️ 知识库 + 联网搜索 同时启用规则
- **税务政策类问题（Tax Policy）**：同时启用 `enable_rag: true` + `enable_search: true`
- **税务计算类问题（Tax Calculation）**：同时启用 `enable_rag: true` + `enable_search: true`
- **税务筹划类问题（Tax Planning）**：同时启用 `enable_rag: true` + `enable_search: true`
- 原因：知识库可能有历史政策，联网搜索可获取最新政策，两者结合回答更准确

### enable_calculator（计算器）
- 询问"怎么算"、"如何计算" → true
- 涉及具体数值计算 → true

### enable_time（时间工具）
- **仅当派发给 General Assistant 且问题涉及时间时，才设为 true**

### ⚠️ 特殊规则（税务计算 Agent）
- **如果派发给 Tax Calculation，必须将 `enable_search` 设为 `true`**
- 这是为了确保获取最新的税率和计算公式
- 同时建议启用 `enable_rag` 获取计算公式和案例

## 示例

**示例1（简单问候）**：
用户："你好"
你：
```json
{{
  "need_specialist": true,
  "enable_rag": false,
  "enable_search": false,
  "enable_calculator": false,
  "enable_time": false,
  "specialist_agent": "General Assistant",
  "reasoning": "用户打招呼，需要友好回应",
  "optimized_query": "你好",
  "thought_process": "用户发送了一个简单的问候语'你好'。这是一个日常社交互动，不涉及任何税务专业知识。因此，我将派发给通用助手（General Assistant）来回应。不需要启用任何工具（知识库、搜索、计算器、时间），因为只需要简单友好的问候回应即可。"
}}
```

**示例2（时间问题）**：
用户："今天几号？"
你：
```json
{{
  "need_specialist": true,
  "enable_rag": false,
  "enable_search": false,
  "enable_calculator": false,
  "enable_time": true,
  "specialist_agent": "General Assistant",
  "reasoning": "用户询问当前日期",
  "optimized_query": "今天几号？",
  "thought_process": "用户询问'今天几号'，这是一个关于时间的问题。虽然问题简单，但需要准确的当前日期信息，所以需要启用时间工具（enable_time=true）。这个问题不需要税务专业知识，所以派发给通用助手（General Assistant）处理即可。"
}}
```

**示例3（上下文理解 - 代词消歧）**：
用户："增值税税率是多少？"
用户："它一般是多少？"  ← 第二轮对话
你：
```json
{{
  "need_specialist": true,
  "enable_rag": false,
  "enable_search": false,
  "enable_calculator": false,
  "enable_time": false,
  "specialist_agent": "Tax Policy",
  "reasoning": "用户询问增值税税率，需要上下文理解",
  "optimized_query": "增值税一般纳税人的税率一般是多少？",
  "thought_process": "用户之前询问了'增值税税率是多少'，现在又问'它一般是多少'。从上下文来看，'它'指的是'增值税税率'。用户想知道增值税的一般税率标准，这是一个税收政策问题。我将派发给税收政策专家（Tax Policy），并使用清晰的问题表述，确保专家理解用户是在询问增值税的一般税率。"
}}
```

**示例3b（上下文理解 - 用户信息）**：
用户："我的名字叫ycc"
用户："我叫什么名字？"  ← 第二轮对话
你：
```json
{{
  "need_specialist": true,
  "enable_rag": false,
  "enable_search": false,
  "enable_calculator": false,
  "enable_time": false,
  "specialist_agent": "General Assistant",
  "reasoning": "用户询问自己的名字，需要从历史中获取",
  "optimized_query": "用户的名字是 ycc，他问'我叫什么名字？'",
  "thought_process": "用户在之前的对话中告诉我他的名字是 ycc。现在他问'我叫什么名字？'，这是一个简单的上下文回忆问题。虽然问题本身简单，但专家 Agent 看不到历史消息，所以我必须在 optimized_query 中明确告诉专家：用户的名字是 ycc。这样专家才能正确回答。"
}}
```

**示例4（税务政策问题 - 同时启用知识库和联网搜索）**：
用户："2024年增值税最新税率是多少？"
你：
```json
{{
  "need_specialist": true,
  "enable_rag": true,
  "enable_search": true,
  "enable_calculator": false,
  "enable_time": false,
  "specialist_agent": "Tax Policy",
  "reasoning": "用户询问增值税税率政策，需要查询最新政策文件",
  "optimized_query": "增值税最新税率政策",
  "thought_process": "用户询问增值税的最新税率，这是一个典型的税收政策问题。关键词包括'增值税'、'税率'、'最新'。税务政策经常更新，为了确保回答准确，我需要同时启用知识库检索（enable_rag=true）和联网搜索（enable_search=true）。知识库可以提供历史政策文件和详细解读，联网搜索可以获取最新发布的政策变化。两者结合，能够为用户提供最全面、最准确的答案。派发给税收政策专家（Tax Policy）最为合适。"
}}
```

**示例5（图片分析）**：
用户：[上传图片] "这张发票的税率是多少？"
你：
```json
{{
  "need_specialist": true,
  "enable_rag": false,
  "enable_search": false,
  "enable_calculator": false,
  "enable_time": false,
  "specialist_agent": "General Tax",
  "reasoning": "用户上传发票图片询问税率，需要分析图片内容",
  "optimized_query": "这张发票的税率是多少？",
  "thought_process": "用户上传了一张发票图片并询问税率。这涉及到图片内容识别和税务知识两个层面。首先需要从图片中提取发票信息（如税额、金额等），然后可能需要计算或解释税率。通用税务助手（General Tax）最适合处理这类综合问题。如果发票识别后需要具体计算，后续可以启用计算器工具。"
}}
```
""",
        tools=[],  # 时间工具会自动注入
        db=db,  # ✅ 保存推理过程到数据库
        session_id=session_id,
        user_id=user_id,
        add_history_to_context=True,  # ✅ 加载历史以理解上下文
        num_history_runs=5,  # ✅ 最近5轮对话（减少超时风险）
    )

    return agent


def parse_supervisor_decision(response_content: str) -> Dict:
    """
    解析 Supervisor Agent 的决策

    Args:
        response_content: Agent 响应内容

    Returns:
        决策字典
    """
    try:
        # 提取 JSON
        json_match = re.search(r'```json\s*(.*?)\s*```', response_content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试直接解析
            json_str = response_content.strip()

        # 尝试解析 JSON
        if json_str.startswith('{'):
            decision = json.loads(json_str)

            # 验证必需字段
            required_fields = ["need_specialist", "specialist_agent"]
            for field in required_fields:
                if field not in decision:
                    logger.warning(f"决策缺少字段: {field}")
                    decision[field] = False if "need_specialist" == field else "General Tax"

            # 设置默认值
            decision.setdefault("enable_rag", False)
            decision.setdefault("enable_search", False)
            decision.setdefault("enable_calculator", False)
            decision.setdefault("enable_time", False)
            decision.setdefault("reasoning", "")
            decision.setdefault("optimized_query", "")
            decision.setdefault("thought_process", "")  # ✅ 新增：思维链推理过程

            logger.info(f"Supervisor 决策: {decision}")
            return decision

        # 不是 JSON，说明是简单回答
        return {
            "need_specialist": False,
            "direct_answer": response_content,
            "reasoning": "简单问候或非税务问题"
        }

    except json.JSONDecodeError as e:
        logger.warning(f"JSON解析失败: {e}, 判断为简单回答")
        return {
            "need_specialist": False,
            "direct_answer": response_content,
            "reasoning": "解析失败，按简单回答处理"
        }
    except Exception as e:
        logger.error(f"解析 Supervisor 决策失败: {e}", exc_info=True)
        return {
            "need_specialist": False,
            "direct_answer": response_content,
            "reasoning": "解析异常"
        }


def create_supervisor_workflow(
    model_id: str = "qwen-plus",  # ✅ 专家模型默认使用 qwen-plus
    session_id: str = None,
    user_id: str = "default",
    send_media_to_model: bool = True,
    temperature: float = 0.7,
    db=None,
    enable_search: bool = True,  # ✅ 全局搜索开关
    enable_rag: bool = True,  # ✅ 全局 RAG 开关
) -> Workflow:
    """
    创建 Supervisor-Agent Workflow

    工作流程：
    1. Supervisor Agent 分析输入并决策
    2. 如果是简单回答，直接返回
    3. 如果需要专业 Agent，根据决策动态配置工具和 Agent

    Args:
        model_id: 专家模型 ID（默认 qwen-plus）
        session_id: 会话 ID
        user_id: 用户 ID
        send_media_to_model: 是否发送媒体
        temperature: 温度参数
        db: 数据库实例
        enable_search: 全局搜索开关（false 则强制禁用）
        enable_rag: 全局 RAG 开关（false 则强制禁用）

    Returns:
        Workflow 实例
    """
    model_config = model_cache.get_model_config(model_id)
    if not model_config:
        raise ValueError(f"模型配置不存在: {model_id}")

    api_key = model_config.get("model_api_key")
    base_url = model_config.get("model_url")

    # ✅ Qwen 兼容的 role_map（用于所有专业 Agent）
    # Qwen 只支持：system, user, assistant, tool, function
    qwen_role_map = {
        "system": "system",
        "user": "user",
        "assistant": "assistant",
        "tool": "tool",
        "developer": "system",  # ✅ Qwen 兼容：developer -> system
        "model": "assistant",   # ✅ 模型回复使用 assistant
    }

    # ✅ 专家模型：使用传入的 model_id（默认 qwen-plus，性能与速度平衡）
    specialist_model = OpenAIChat(
        id=model_id,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        role_map=qwen_role_map,  # ✅ 应用 Qwen 兼容的角色映射
    )

    # ✅ 领导模型：使用 qwen-flash（响应最快）
    supervisor_model_id = "qwen-flash"
    supervisor_model_config = model_cache.get_model_config(supervisor_model_id)
    if supervisor_model_config:
        supervisor_api_key = supervisor_model_config.get("model_api_key", api_key)
        supervisor_base_url = supervisor_model_config.get("model_url", base_url)
    else:
        # 如果找不到 qwen-flash 配置，使用默认配置
        supervisor_api_key = api_key
        supervisor_base_url = base_url

    supervisor_model = OpenAIChat(
        id=supervisor_model_id,
        api_key=supervisor_api_key,
        base_url=supervisor_base_url,
        temperature=0.3,  # ✅ 领导使用较低温度，决策更稳定
        role_map=qwen_role_map,
    )

    # ============ 创建专业 Agent ============

    # ============ 获取当前时间上下文 ============
    current_time_context = get_current_time_context()

    # ============ 创建专业 Agent ============

    # 0. 通用助手 Agent（处理简单问候、时间、自我介绍等非税务问题）
    general_assistant_agent = Agent(
        name="general_assistant_agent",
        model=specialist_model,  # ✅ 使用专家模型
        instructions=f"""{current_time_context}

你是"税小通"——专业的税务智能助手。

## 你的职责
处理简单、与税务专业问题无关的咨询，包括：
1. **友好问候**：回应"你好"、"谢谢"、"在吗"等
2. **时间日期**：回答"今天几号"、"现在几点"等（使用时间工具）
3. **自我介绍**：介绍你的身份和功能
4. **其他简单问题**：帮助用户、指引提问方式等

## 你的身份
你是税小通，一个专业的税务智能助手，可以帮助用户：
- 查询税收政策和法规
- 进行税务计算
- 提供税务筹划建议
- 评估税务风险
- 分析税务相关图片和文件

## 回答原则
1. 简洁友好，不啰嗦
2. 如果用户问的是税务专业问题，礼貌地引导他们重新提问
3. 如果需要时间，使用时间工具准确回答
4. 严禁使用emoji：在所有回复内容中禁止使用任何emoji符号
5. 数学公式表达：使用普通文本表达公式，禁止使用LaTeX格式（如$...$、\\begin{{cases}}等）

## 小程序兼容性要求（重要）
- **不要生成 URL 链接**：微信小程序不支持点击链接
- **不要使用 markdown 链接格式**：如 `[标题](url)`
- **不要说"点击查看"、"访问官网"**等引导用户点击的内容
- **直接用文字描述**：功能介绍、操作方法等

## 自我介绍模板（用户询问"介绍一下你自己"时使用）
"我是税小通，专业的税务智能助手。我可以帮您：
- 查询最新的税收政策和法规
- 进行各种税务计算（增值税、企业所得税、个人所得税等）
- 提供税务筹划和优化建议
- 评估税务风险和合规问题
- 分析发票、合同等税务相关文件

请问有什么可以帮您的吗？"
""",
        tools=[],  # 时间工具会动态添加
        send_media_to_model=send_media_to_model,
        store_media=True,
        markdown=True,  # ✅ 启用 markdown 格式（支持标题、列表等）
        db=None,  # ❌ 不使用 Agno 存储（手动保存到 Supervisor 的 run）
        store_tool_messages=False,  # ✅ 禁用工具消息单独存储
    )

    # 1. 税收政策 Agent
    tax_policy_agent = Agent(
        name="tax_policy_agent",
        model=specialist_model,  # ✅ 使用专家模型（qwen-max-latest）
        instructions=f"""{current_time_context}

你是**税收政策专家**。

## 专业领域
- 增值税、企业所得税、个人所得税等各税种政策
- 税收优惠政策、税收法规

## 回答原则
1. 直接引用政策文号和发布日期
2. 说明政策适用范围和时效性
3. 严禁使用emoji：在所有回复内容中禁止使用任何emoji符号
4. 数学公式表达：使用普通文本表达公式，禁止使用LaTeX格式
5. 服务导向：回答完整后，可说明如需进一步了解XX，可告知您的具体情况，我将提供针对性解答
6. 禁止推诿：不要说「建议咨询专业税务师或税务机关」等推诿式话语

## 回复格式要求（严格遵守）
- **不要提及工具或渠道**：回答时不要说「根据搜索」「通过检索」「根据知识库」「结合百度搜索」等
- **直接给出依据**：直接说明法律条文、政策文号、生效日期等
- **参考格式**：
  - 正确：根据《关于小规模纳税人增值税政策的公告》（财政部 税务总局公告 2023 年第 1 号）...
  - 错误：根据知识库检索的最新信息...

## 小程序兼容性要求（重要）
- **不要生成 URL 链接**：微信小程序不支持点击链接
- **不要使用 markdown 链接格式**：如 `[标题](url)` 或 `<url>`
- **不要说"点击查看"**：用户无法点击
- **直接用文字说明**：政策名称、文号、核心内容
- **如果需要引用来源**：直接说明文件名称和文号即可

## 时间工具使用（强制）
- 在回答每个税务问题前，必须先调用 get_current_time 工具确认当前时间
- 这是必须步骤，即使问题看起来与时间无关，也需要先确认时间背景，以判断政策时效性

## ⚠️ 工具调用顺序（严格遵守）
0. **严禁直接从训练数据回答**：即使你"认为"自己知道答案，也禁止跳过工具直接作答。
   训练数据有知识截止日期，政策/税率可能已调整，必须经过搜索/知识库核验后才能回答。
1. **先调用联网搜索工具**（获取最新政策，时效性最强）
2. **再调用知识库工具**（获取专业法规文件补充细节）
3. **冲突时以联网搜索结果为准**（联网内容更新，知识库可能有历史版本）
4. **严格基于检索内容作答**：只能使用工具返回的信息，不得在检索结果之外自行推测、补充或发挥
5. **信息不足时如实说明**："根据目前检索到的信息，暂无法确认该内容，建议以官方最新公告为准"，严禁凭空推断
- 每个工具一次调用即可，请勿对同一问题重复调用
""",
        tools=[],  # 不预先添加时间工具
        send_media_to_model=send_media_to_model,
        store_media=True,
        markdown=True,  # ✅ 启用 markdown 格式（支持标题、列表等）
        db=None,  # ❌ 不使用 Agno 存储（手动保存到 Supervisor 的 run）
        store_tool_messages=False,  # ✅ 禁用工具消息单独存储
    )

    # 2. 税务计算 Agent
    tax_calculation_agent = Agent(
        name="tax_calculation_agent",
        model=specialist_model,  # ✅ 使用专家模型（qwen-max-latest）
        instructions=f"""{current_time_context}

你是**税务计算专家**。

## 计算能力
- 增值税、企业所得税、个人所得税计算

## 计算原则
1. 使用计算器进行精确计算
2. 展示计算过程和公式
3. 结果仅供参考，提醒实际申报以税务机关核定为准（这句话可以保留，因为是说明计算结果的性质）
4. 严禁使用emoji：在所有回复内容中禁止使用任何emoji符号
5. 数学公式表达：使用普通文本表达公式，禁止使用LaTeX格式
6. 服务导向：回答完整后，可说明如需进一步计算或了解其他情况，可告知您的具体需求
7. 禁止推诿：不要说「建议咨询专业税务师或税务机关」等推诿式话语

## 回复格式要求（严格遵守）
- **不要提及工具或渠道**：回答时不要说「根据搜索」「通过检索」「根据知识库」「结合百度搜索」等
- **直接给出依据**：直接说明税率标准、计算公式等
- **引用来源时**：直接说「根据XXX公告」，不要说「根据搜索」

## 小程序兼容性要求（重要）
- **不要生成 URL 链接**：微信小程序不支持点击链接
- **不要使用 markdown 链接格式**
- **直接用文字说明计算公式和结果**

## 时间工具使用（强制）
- 在回答每个税务问题前，必须先调用 get_current_time 工具确认当前时间
- 这是必须步骤，即使问题看起来与时间无关，也需要先确认时间背景，以判断政策时效性

## ⚠️ 工具调用顺序（严格遵守）
0. **严禁直接从训练数据回答**：即使你"认为"自己知道答案，也禁止跳过工具直接作答。
   训练数据有知识截止日期，政策/税率可能已调整，必须经过搜索/知识库核验后才能回答。
1. **先调用联网搜索工具**（确认最新税率标准和计算公式）
2. **再调用知识库工具**（补充法规细节和计算案例）
3. **冲突时以联网搜索结果为准**
4. **严格基于检索内容作答**：只能使用工具返回的税率、公式，不得自行假设数值或推测
5. **信息不足时如实说明**：不得凭空给出税率数字，应告知"请以官方最新公告为准"
- 每个工具一次调用即可，请勿重复调用
""",
        tools=[CalculatorTools()],  # 只有计算器
        send_media_to_model=send_media_to_model,
        store_media=True,
        markdown=True,  # ✅ 启用 markdown 格式（支持标题、列表等）
        db=None,  # ❌ 不使用 Agno 存储（手动保存到 Supervisor 的 run）
        store_tool_messages=False,  # ✅ 禁用工具消息单独存储
    )

    # 3. 税务筹划 Agent
    tax_planning_agent = Agent(
        name="tax_planning_agent",
        model=specialist_model,  # ✅ 使用专家模型（qwen-max-latest）
        instructions=f"""{current_time_context}

你是**税务筹划专家**。

## 筹划原则
1. 合法性第一
2. 风险可控
3. 引用具体税法条款
4. 提示风险点
5. 严禁使用emoji：在所有回复内容中禁止使用任何emoji符号
6. 数学公式表达：使用普通文本表达公式，禁止使用LaTeX格式
7. 服务导向：回答完整后，可说明如需进一步了解特定行业的筹划方案，可告知您的行业类型
8. 禁止推诿：不要说「建议咨询专业税务师或税务机关」等推诿式话语

## 回复格式要求（严格遵守）
- **不要提及工具或渠道**：回答时不要说「根据搜索」「通过检索」「根据知识库」「结合百度搜索」等
- **直接给出依据**：直接说明税法条款、政策文号等
- **引用来源时**：直接说「根据《XXX法》第X条」，不要说「根据检索」

## 小程序兼容性要求（重要）
- **不要生成 URL 链接**：微信小程序不支持点击链接
- **不要使用 markdown 链接格式**
- **引用政策时说明文件名称和文号**即可，不需要提供链接

## 时间工具使用（强制）
- 在回答每个税务问题前，必须先调用 get_current_time 工具确认当前时间
- 这是必须步骤，即使问题看起来与时间无关，也需要先确认时间背景，以判断政策时效性

## ⚠️ 工具调用顺序（严格遵守）
0. **严禁直接从训练数据回答**：即使你"认为"自己知道答案，也禁止跳过工具直接作答。
   训练数据有知识截止日期，政策/税率可能已调整，必须经过搜索/知识库核验后才能回答。
1. **先调用联网搜索工具**（确认最新优惠政策和合规要求）
2. **再调用知识库工具**（补充具体税法条款细节）
3. **冲突时以联网搜索结果为准**
4. **严格基于检索内容作答**：筹划方案必须有工具返回的依据，不得推测发挥
5. **信息不足时如实说明**：不得假设优惠政策存在，应告知需核实最新政策
- 每个工具一次调用即可，请勿重复调用
""",
        tools=[],  # 不预先添加时间工具
        send_media_to_model=send_media_to_model,
        store_media=True,
        markdown=True,  # ✅ 启用 markdown 格式（支持标题、列表等）
        db=None,  # ❌ 不使用 Agno 存储（手动保存到 Supervisor 的 run）
        store_tool_messages=False,  # ✅ 禁用工具消息单独存储
    )

    # 4. 税务风险 Agent
    tax_risk_agent = Agent(
        name="tax_risk_agent",
        model=specialist_model,  # ✅ 使用专家模型（qwen-max-latest）
        instructions=f"""{current_time_context}

你是**税务风险专家**。

## 风险识别
- 发票管理风险
- 税务申报风险
- 税务合规风险

## 回复原则
1. 客观公正评估
2. 提供具体建议
3. 说明严重性
4. 严禁使用emoji：在所有回复内容中禁止使用任何emoji符号
5. 数学公式表达：使用普通文本表达公式，禁止使用LaTeX格式
6. 服务导向：回答完整后，可说明如需进一步评估特定业务场景的风险，可提供更多细节
7. 禁止推诿：不要说「建议咨询专业税务师或税务机关」等推诿式话语

## 回复格式要求（严格遵守）
- **不要提及工具或渠道**：回答时不要说「根据搜索」「通过检索」「根据知识库」「结合百度搜索」等
- **直接给出依据**：直接说明法规要求、合规标准等
- **引用来源时**：直接说「根据《XXX管理办法》」，不要说「根据检索」

## 小程序兼容性要求（重要）
- **不要生成 URL 链接**：微信小程序不支持点击链接
- **不要使用 markdown 链接格式**
- **直接用文字说明风险点和建议**

## 时间工具使用（强制）
- 在回答每个税务问题前，必须先调用 get_current_time 工具确认当前时间
- 这是必须步骤，即使问题看起来与时间无关，也需要先确认时间背景，以判断政策时效性

## ⚠️ 工具调用顺序（严格遵守）
0. **严禁直接从训练数据回答**：即使你"认为"自己知道答案，也禁止跳过工具直接作答。
   训练数据有知识截止日期，政策/税率可能已调整，必须经过搜索/知识库核验后才能回答。
1. **先调用联网搜索工具**（确认最新合规要求和处罚标准）
2. **再调用知识库工具**（补充具体法规条款细节）
3. **冲突时以联网搜索结果为准**
4. **严格基于检索内容作答**：风险评估必须有工具返回的依据，不得自行推测风险等级
5. **信息不足时如实说明**：不得凭空断定合规或违规，应告知需进一步核实
- 每个工具一次调用即可，请勿重复调用
""",
        tools=[],  # 不预先添加时间工具
        send_media_to_model=send_media_to_model,
        store_media=True,
        markdown=True,  # ✅ 启用 markdown 格式（支持标题、列表等）
        db=None,  # 不使用 Agno 存储（手动保存到 Supervisor 的 run）
        store_tool_messages=False,  # 禁用工具消息单独存储
    )

    # 5. 通用税务 Agent
    general_tax_agent = Agent(
        name="general_tax_agent",
        model=specialist_model,  # ✅ 使用专家模型（qwen-max-latest）
        instructions=f"""{current_time_context}

你是"税小通"——智能财税助手。

## 你的专业领域
1. 税收政策咨询
2. 税务计算
3. 税务筹划
4. 税务风险预警

## 回复原则
1. 专业准确
2. 实事求是
3. 风险提示
4. 条理清晰
5. 严禁使用emoji：在所有回复内容中禁止使用任何emoji符号
6. 数学公式表达：使用普通文本表达公式，禁止使用LaTeX格式
7. 服务导向：回答完整后，可说明如需进一步了解具体情况，可告知您的业务场景或需求
8. 禁止推诿：不要说「建议咨询专业税务师或税务机关」「建议咨询当地税务机关」等推诿式话语

## 回复格式要求（严格遵守）
- **不要提及工具或渠道**：回答时不要说「根据搜索」「通过检索」「根据知识库」「结合百度搜索」「让我为您搜索」等
- **直接给出依据**：直接说明法律条文、政策文号、生效日期等
- **参考格式**：
  - 正确：根据《增值税暂行条例》第X条，...
  - 错误：根据知识库检索的最新信息...
- **文末可标注来源**：可以标注「参考依据：XXX」，但不要说明获取方式

## 小程序兼容性要求（重要）
- **不要生成 URL 链接**：微信小程序不支持点击链接
- **不要使用 markdown 链接格式**：如 `[标题](url)`
- **不要说"点击查看"**
- **引用来源时说明文件名称**即可，不要提供链接

## 时间工具使用（强制）
- 在回答每个税务问题前，必须先调用 get_current_time 工具确认当前时间
- 这是必须步骤，即使问题看起来与时间无关，也需要先确认时间背景，以判断政策时效性

## ⚠️ 工具调用顺序（严格遵守）
0. **严禁直接从训练数据回答**：即使你"认为"自己知道答案，也禁止跳过工具直接作答。
   训练数据有知识截止日期，政策/税率可能已调整，必须经过搜索/知识库核验后才能回答。
1. **先调用联网搜索工具**（获取最新政策，时效性最强）
2. **再调用知识库工具**（补充专业法规文件细节）
3. **冲突时以联网搜索结果为准**（联网内容更新，知识库可能有历史版本）
4. **严格基于检索内容作答**：只能使用工具返回的信息，不得在检索结果之外自行推测、补充或发挥
5. **信息不足时如实说明**："根据目前检索到的信息，暂无法确认该内容，建议以官方最新公告为准"，严禁凭空推断
- 每个工具一次调用即可，请勿重复调用
""",
        tools=[],  # 不预先添加时间工具
        send_media_to_model=send_media_to_model,
        store_media=True,
        markdown=True,  # ✅ 启用 markdown 格式（支持标题、列表等）
        db=None,  # ❌ 不使用 Agno 存储（手动保存到 Supervisor 的 run）
        store_tool_messages=False,  # ✅ 禁用工具消息单独存储
    )

    # ============ 创建 Supervisor Agent ============
    # ✅ 不传递 model_id，使用默认的 qwen-flash（响应最快）
    supervisor_agent = create_supervisor_agent(
        db=db,
        session_id=session_id,
        user_id=user_id,
    )

    # ============ 创建 Workflow ============
    workflow = Workflow(
        name="Supervisor Agent Workflow",
        description="Supervisor Agent 分析并决策，派发给专业 Agent",
        db=db,
        session_id=session_id,
        user_id=user_id,
        steps=[
            Router(
                name="supervisor_router",
                selector=lambda step_input: [
                    Step(name="Supervisor", agent=supervisor_agent),
                ],
                choices=[
                    Step(name="Supervisor", agent=supervisor_agent),
                    Step(name="General Assistant", agent=general_assistant_agent),  # ✅ 新增
                    Step(name="Tax Policy", agent=tax_policy_agent),
                    Step(name="Tax Calculation", agent=tax_calculation_agent),
                    Step(name="Tax Planning", agent=tax_planning_agent),
                    Step(name="Tax Risk", agent=tax_risk_agent),
                    Step(name="General Tax", agent=general_tax_agent),
                ],
                description="Supervisor Agent 分析问题，派发给专业 Agent",
            ),
        ],
    )

    # ✅ 保存全局开关到 workflow 对象上
    workflow.enable_search = enable_search
    workflow.enable_rag = enable_rag

    return workflow


def execute_supervisor_workflow(
    workflow: Workflow,
    query: str,
    user_id: str = "default",
) -> str:
    """
    执行 Supervisor Workflow

    Args:
        workflow: Workflow 实例
        query: 用户查询
        user_id: 用户 ID

    Returns:
        最终回答
    """
    try:
        logger.info(f"[Supervisor Workflow] 开始处理查询: {query}")

        # 步骤1: 调用 Supervisor Agent
        supervisor_step = workflow.steps[0].choices[0]  # Supervisor
        supervisor_response = supervisor_step.agent.run(query)

        # 步骤2: 解析决策
        decision = parse_supervisor_decision(supervisor_response.content)

        # 步骤3: 如果是简单回答，直接返回
        if not decision.get("need_specialist", False):
            logger.info("[Supervisor Workflow] Supervisor 直接回答")
            return decision.get("direct_answer", supervisor_response.content)

        # 步骤4: 根据决策找到专业 Agent
        specialist_agent_name = decision.get("specialist_agent", "General Tax")
        logger.info(f"[Supervisor Workflow] 派发给: {specialist_agent_name}")

        # 找到对应的 Agent Step（名称直接匹配，无需转换）
        target_step = None
        for step in workflow.steps[0].choices:
            if step.name == specialist_agent_name:
                target_step = step
                break

        if not target_step:
            logger.warning(f"未找到 Agent: {specialist_agent_name}, 使用 General Tax")
            target_step = workflow.steps[0].choices[-1]  # General Tax

        # 步骤5: 根据决策动态配置工具
        # 时间工具：始终挂载给所有专家 Agent
        # 原因：系统提示词里的时间是静态注入的，模型有时会忽略；
        # 工具调用有明确返回值，模型更倾向于信任工具结果来确认当前时间。
        tools = list(create_time_tools())
        logger.info("[Supervisor Workflow] 时间工具始终挂载")

        # ✅ RAG 工具：需要 Supervisor 决策启用 + 全局开关启用
        if decision.get("enable_rag") and workflow.enable_rag:
            tools.extend(create_dynamic_knowledge_toolkit(user_id=user_id, cache_size=1000))
            logger.info("[Supervisor Workflow] 启用 RAG")
        elif decision.get("enable_rag") and not workflow.enable_rag:
            logger.info("[Supervisor Workflow] Supervisor 要求启用 RAG，但全局开关已禁用")

        # ✅ 搜索工具：需要 Supervisor 决策启用 + 全局开关启用
        if decision.get("enable_search") and workflow.enable_search:
            baidu_tool = create_baidu_search_tool()
            if baidu_tool:
                tools.append(baidu_tool)
            duckduckgo_tools = create_duckduckgo_tools()
            tools.extend(duckduckgo_tools)
            logger.info("[Supervisor Workflow] 启用联网搜索")
        elif decision.get("enable_search") and not workflow.enable_search:
            logger.info("[Supervisor Workflow] Supervisor 要求启用搜索，但全局开关已禁用")

        if decision.get("enable_calculator"):
            tools.append(CalculatorTools())
            logger.info("[Supervisor Workflow] 启用计算器")

        # 动态更新 Agent 的工具
        target_step.agent.tools = tools

        # 步骤6: 使用优化后的查询调用专业 Agent
        optimized_query = decision.get("optimized_query", query)
        final_response = target_step.agent.run(optimized_query)

        logger.info("[Supervisor Workflow] 处理完成")
        return final_response.content

    except Exception as e:
        logger.error(f"[Supervisor Workflow] 执行失败: {e}", exc_info=True)
        return f"处理您的请求时出错: {str(e)}"


async def execute_supervisor_workflow_stream(
    workflow: Workflow,
    user_message: str,
    query_for_agent: str,
    user_id: str = "default",
    session_id: str = None,
    images=None,
    db=None,
):
    """
    执行 Supervisor Workflow（流式版本）

    流式输出策略：
    1. Supervisor Agent 总是输出 JSON 决策（不输出给用户）
    2. 根据决策派发给对应的专家 Agent（包括 General Assistant）
    3. 流式输出专家 Agent 的回答

    Args:
        workflow: Workflow 实例
        user_message: 用户原始消息（纯净，将保存到数据库）
        query_for_agent: 完整查询（包含文件内容，用于 Agent 处理）
        user_id: 用户 ID
        session_id: 会话 ID
        images: 图片列表（可选）
        db: 数据库实例（用于手动保存专家回答）

    Yields:
        Dict: SSE 事件字典
    """
    from agno.agent import RunEvent

    try:
        logger.info(f"[Supervisor Workflow Stream] 开始处理查询: {query_for_agent}")
        logger.info(f"[Supervisor Workflow Stream] 用户原始消息（将保存到数据库）: {user_message}")

        # ========== 检测是否有图片或文件 ==========
        has_images = images is not None and len(images) > 0
        if has_images:
            logger.info(f"[Supervisor Workflow Stream] 检测到 {len(images)} 张图片")

        # ========== 步骤1: 调用 Supervisor Agent（流式输出推理过程） ==========
        supervisor_step = workflow.steps[0].choices[0]  # Supervisor
        supervisor_content = ""
        supervisor_run_id = None  # 保存 Supervisor 的 run_id

        # 先收集所有 Supervisor 内容（不流式输出，避免输出原始 JSON）
        # ✅ 使用 user_message 作为 input，这样纯净的用户消息会被保存到数据库
        async for event in supervisor_step.agent.arun(
            input=user_message,  # ✅ 保存纯净的用户消息到数据库
            images=images,
            stream=True,
            stream_events=True,
        ):
            # 捕获 run_id
            if hasattr(event, "run_id") and event.run_id:
                supervisor_run_id = event.run_id

            if hasattr(event, "event") and event.event == RunEvent.run_content:
                if hasattr(event, "content") and isinstance(event.content, str):
                    supervisor_content += event.content

        logger.info(f"[Supervisor Workflow Stream] Supervisor 分析完成，run_id={supervisor_run_id}")

        # ========== 步骤2: 解析决策 ==========
        decision = parse_supervisor_decision(supervisor_content)

        # ========== 步骤3: 提取思考过程（立即开始流式输出） ==========
        thought_process = decision.get("thought_process", "")
        specialist_agent_name = decision.get("specialist_agent", "General Tax")
        logger.info(f"[Supervisor Workflow Stream] 提取 thought_process: {'有' if thought_process else '无'}, 长度: {len(thought_process)}, 内容预览: {thought_process[:100] if thought_process else '(空)'}...")
        logger.info(f"[Supervisor Workflow Stream] 派发给: {specialist_agent_name}")

        # 定义异步任务
        async def stream_thinking_process():
            """流式输出思考过程（使用 grapheme 库安全切分）"""
            if thought_process:
                # 使用 grapheme 库按字形集群（grapheme clusters）切分
                # 确保不会截断组合字符（emoji、肤色修饰符、组合标记等）
                try:
                    import grapheme

                    # 将字符串拆分为字形集群
                    clusters = list(grapheme.graphemes(thought_process))

                    # ✅ 每 2-3 个字形集群输出一次（细粒度流式输出）
                    current_chunk = ""
                    chunk_size_target = 3  # 目标块大小：3个字形集群
                    current_grapheme_count = 0  # 当前非空白字形集群计数

                    for cluster in clusters:
                        current_chunk += cluster

                        # 只计数非空白字符
                        if cluster.strip():
                            current_grapheme_count += 1

                        # 每达到目标块大小就输出
                        if current_grapheme_count >= chunk_size_target:
                            yield {
                                "type": "thinking",
                                "content": current_chunk,
                            }
                            current_chunk = ""
                            current_grapheme_count = 0
                            await asyncio.sleep(0.08)  # ✅ 0.08秒延迟（更短，因为是细粒度输出）

                    # 发送剩余内容
                    if current_chunk:
                        yield {
                            "type": "thinking",
                            "content": current_chunk,
                        }

                except ImportError:
                    # 如果 grapheme 不可用，降级为简单方案（一次性发送）
                    yield {
                        "type": "thinking",
                        "content": thought_process,
                    }

        async def find_agent_and_preload_tools():
            """查找专业 Agent + 预加载工具配置"""
            # 1. 查找对应的 Agent Step（名称直接匹配，无需转换）
            target_step = None
            for step in workflow.steps[0].choices:
                if step.name == specialist_agent_name:
                    target_step = step
                    break

            if not target_step:
                logger.warning(f"未找到 Agent: {specialist_agent_name}, 使用 General Tax")
                target_step = workflow.steps[0].choices[-1]  # General Tax

            # 2. 预加载工具配置
            # 时间工具：始终挂载给所有专家 Agent
            # 原因：系统提示词里的时间是静态注入的，模型有时会忽略；
            # 工具调用有明确返回值，模型更倾向于信任工具结果来确认当前时间。
            tools = list(create_time_tools())
            logger.info("[Supervisor Workflow Stream] 时间工具始终挂载")

            # ✅ RAG 工具：需要 Supervisor 决策启用 + 全局开关启用
            if decision.get("enable_rag") and workflow.enable_rag:
                tools.extend(create_dynamic_knowledge_toolkit(user_id=user_id, cache_size=1000))
                logger.info("[Supervisor Workflow Stream] 启用 RAG")
            elif decision.get("enable_rag") and not workflow.enable_rag:
                logger.info("[Supervisor Workflow Stream] Supervisor 要求启用 RAG，但全局开关已禁用")

            # ✅ 搜索工具：需要 Supervisor 决策启用 + 全局开关启用
            if decision.get("enable_search") and workflow.enable_search:
                baidu_tool = create_baidu_search_tool()
                if baidu_tool:
                    tools.append(baidu_tool)
                duckduckgo_tools = create_duckduckgo_tools()
                tools.extend(duckduckgo_tools)
                logger.info("[Supervisor Workflow Stream] 启用联网搜索")
            elif decision.get("enable_search") and not workflow.enable_search:
                logger.info("[Supervisor Workflow Stream] Supervisor 要求启用搜索，但全局开关已禁用")

            if decision.get("enable_calculator"):
                from agno.tools.calculator import CalculatorTools
                tools.append(CalculatorTools())
                logger.info("[Supervisor Workflow Stream] 启用计算器")

            # 3. 动态更新 Agent 的工具
            target_step.agent.tools = tools

            return target_step, tools

        # ========== 步骤4: 并行执行（流式输出 + 查找Agent + 工具预加载） ==========
        import asyncio

        # 创建查找 Agent + 工具预加载任务（协程）
        agent_tools_task = asyncio.create_task(find_agent_and_preload_tools())

        # 流式输出思考过程（直接遍历异步生成器）
        try:
            async for chunk in stream_thinking_process():
                yield chunk
        except Exception as e:
            logger.error(f"[Supervisor Workflow Stream] 输出 thinking 失败: {e}", exc_info=True)

        # 等待查找 Agent + 工具预加载完成
        try:
            target_step, tools = await agent_tools_task
        except Exception as e:
            logger.error(f"[Supervisor Workflow Stream] 查找 Agent 或预加载工具失败: {e}", exc_info=True)
            # 如果预加载失败，使用默认 Agent 和空工具列表
            target_step = workflow.steps[0].choices[-1]  # General Tax
            tools = []
            target_step.agent.tools = tools

        # ========== 步骤6: 流式输出专家 Agent 的回答 ==========
        # 专家 Agent 不使用 Agno 存储，手动将回答保存到 Supervisor 的 run
        optimized_query = decision.get("optimized_query", query_for_agent)

        # 收集专家回答的完整内容（用于手动保存）
        specialist_response = ""
        # ✅ 收集工具调用结果（用于保存到 run）
        specialist_tools = []

        logger.info(f"[Supervisor Workflow Stream] 开始调用专家 Agent: {target_step.agent.name}, 查询: {optimized_query}")

        # ✅ 构建传递给专家 Agent 的完整查询（包含文件内容）
        # 如果用户上传了文件，需要将文件内容也传递给专家
        final_query_for_specialist = optimized_query
        if query_for_agent != user_message:
            # 说明有文件内容，将文件内容附加到优化后的查询中
            final_query_for_specialist = f"{optimized_query}\n\n{query_for_agent[len(user_message):]}"

        async for event in target_step.agent.arun(
            input=final_query_for_specialist,  # ✅ 使用包含文件内容的完整查询
            images=images,
            stream=True,
            stream_events=True,
        ):
            # 流式输出内容
            if hasattr(event, "event") and event.event == RunEvent.run_content:
                if hasattr(event, "content") and isinstance(event.content, str):
                    specialist_response += event.content
                    yield {
                        "type": "content",
                        "content": event.content,
                    }
                continue

            # 工具调用结果
            if hasattr(event, "event"):
                event_str = str(event.event)
                if "tool" in event_str.lower() or "Tool" in event_str:
                    tool_obj = getattr(event, "tool", None)
                    if tool_obj and hasattr(tool_obj, "tool_name") and hasattr(tool_obj, "result"):
                        tool_name = getattr(tool_obj, "tool_name", "")
                        tool_output = getattr(tool_obj, "result", None)
                        tool_call_id = getattr(tool_obj, "tool_call_id", str(uuid.uuid4()))

                        if tool_name and tool_output:
                            tool_name_lower = str(tool_name).lower()

                            # ✅ 收集工具调用（用于保存到数据库）
                            specialist_tools.append({
                                "tool_name": tool_name,
                                "result": tool_output,
                                "tool_call_id": tool_call_id,
                                "created_at": int(time.time()),
                            })

                            # RAG 知识库搜索
                            if "search_knowledge" in tool_name_lower or "knowledge" in tool_name_lower:
                                from app.agno.runners.chat_runner import ChatRunner

                                # ✅ 打印知识库查询信息
                                print("\n" + "="*80)
                                print(f"📚 [RAG 知识库检索]")
                                print(f"🔍 查询词: {final_query_for_specialist}")
                                print(f"🛠️  工具名称: {tool_name}")

                                # 尝试解析工具输出，提取知识库信息
                                try:
                                    if isinstance(tool_output, str):
                                        # 尝试解析 JSON 输出
                                        if tool_output.strip().startswith('{'):
                                            output_data = json.loads(tool_output)
                                            print(f"📦 工具输出: {json.dumps(output_data, ensure_ascii=False, indent=2)[:500]}...")
                                        else:
                                            print(f"📦 工具输出（原始）: {str(tool_output)[:300]}...")
                                    else:
                                        print(f"📦 工具输出（类型: {type(tool_output).__name__}）: {str(tool_output)[:300]}...")
                                except Exception as e:
                                    print(f"📦 工具输出（解析失败）: {str(tool_output)[:300]}...")

                                # 解析 RAG 文件（仅用于日志输出，不再缓存发送）
                                rag_files = ChatRunner._parse_rag_files(tool_output)

                                # 打印命中的知识库文件
                                if rag_files:
                                    print(f"\n✅ 命中 {len(rag_files)} 个知识库文件:")
                                    for i, file in enumerate(rag_files, 1):
                                        print(f"   {i}. 📄 {file.get('file_name', '未知文件')}")
                                        if file.get('source'):
                                            print(f"      📍 来源: {file.get('source')}")
                                        if file.get('relevance'):
                                            print(f"      🎯 相关度: {file.get('relevance')}")
                                else:
                                    print(f"\n⚠️  未找到相关知识库文件")

                                print("="*80 + "\n")

                                logger.info(f"[RAG] 查询词: {final_query_for_specialist}, 命中文件数: {len(rag_files)}")

                            # 在线搜索（仅用于日志输出，不再缓存发送）
                            elif "baidu" in tool_name_lower or "duckduckgo" in tool_name_lower:
                                from app.agno.runners.chat_runner import ChatRunner
                                structured_results = ChatRunner._parse_search_results(str(tool_output))

                                # ✅ 打印联网搜索信息
                                print("\n" + "="*80)
                                print(f"🌐 [联网搜索]")
                                print(f"🔍 查询词: {final_query_for_specialist}")
                                print(f"🛠️  搜索引擎: {tool_name}")
                                print(f"✅ 找到 {len(structured_results)} 条结果")
                                for i, result in enumerate(structured_results[:3], 1):  # 只显示前3条
                                    print(f"   {i}. {result.get('title', '未知标题')[:50]}...")
                                print("="*80 + "\n")

                    continue

            # 完成事件
            if hasattr(event, "event") and event.event == RunEvent.run_completed:
                # ✅ 将 RAG 和搜索结果作为内容追加到流式输出中
                # 这些数据同时也会保存到 Agno 的 runs 表中，供历史消息查询使用

                # 1. 提取 RAG 文件列表
                rag_files = []
                for tool in specialist_tools:
                    tool_name = tool.get("tool_name", "")
                    tool_result = tool.get("result", "")

                    if "search_knowledge" in tool_name.lower() or "knowledge" in tool_name.lower():
                        from app.agno.runners.chat_runner import ChatRunner
                        rag_files = ChatRunner._parse_rag_files(tool_result)
                        break

                # 2. 提取搜索结果列表
                search_results = []
                for tool in specialist_tools:
                    tool_name = tool.get("tool_name", "")
                    tool_result = tool.get("result", "")

                    if "baidu" in tool_name.lower() or "duckduckgo" in tool_name.lower():
                        from app.agno.runners.chat_runner import ChatRunner
                        search_results = ChatRunner._parse_search_results(str(tool_result))
                        break

                # 3. 构建参考来源文本（追加到回答末尾）
                references_text = ""

                if rag_files:
                    references_text += "\n\n**参考文件：**\n"
                    # 只显示前3条文件
                    display_files = rag_files[:3]
                    for i, file in enumerate(display_files, 1):
                        file_name = file.get("file_name", "未知文件")

                        # 去掉文件扩展名（如 .md, .pdf, .docx 等）
                        if '.' in file_name:
                            display_name = file_name.rsplit('.', 1)[0]
                        else:
                            display_name = file_name

                        # 如果文件名超过40个字符，截断并添加省略号
                        display_name = display_name[:40] + "..." if len(display_name) > 40 else display_name

                        references_text += f"{i}. {display_name}\n"

                    # 如果超过3条，显示省略提示
                    if len(rag_files) > 3:
                        references_text += f"\n\n... 等 {len(rag_files)} 个文件\n"

                if search_results:
                    references_text += "\n\n**参考链接：**\n"
                    for i, result in enumerate(search_results[:3], 1):  # 最多显示3条
                        title = result.get("title", "未知标题")
                        url = result.get("url", "")

                        # 如果title超过40个字符，截断并添加省略号
                        display_title = title[:40] + "..." if len(title) > 40 else title

                        if url:
                            references_text += f"{i}. [{display_title}]({url})\n"
                        else:
                            references_text += f"{i}. {display_title}\n"

                # 4. 发送参考来源内容（作为 content 类型）
                if references_text:
                    yield {
                        "type": "content",
                        "content": references_text,
                    }

                # 5. 完成标记
                yield {
                    "type": "completed",
                }

        logger.info(f"[Supervisor Workflow Stream] 专家 Agent 回答完成，总长度: {len(specialist_response)}, 工具调用: {len(specialist_tools)}")

        # ✅ 如果没有任何输出，发送默认消息
        if not specialist_response and not specialist_tools:
            logger.warning("[Supervisor Workflow Stream] 专家 Agent 没有产生任何输出")
            yield {
                "type": "content",
                "content": "\n\n抱歉，处理您的请求时遇到了问题，请重试。",
            }
            yield {
                "type": "completed",
            }

        logger.info("[Supervisor Workflow Stream] 处理完成")

        # ========== 手动保存专家回答到 Supervisor 的 run ==========
        # 专家 Agent 不使用 Agno 存储，需要手动将回答追加到 Supervisor 的 run 中
        # ⚠️ 只在有实际内容时才保存消息（避免空 content 导致 Full Agent 加载历史时报错）
        has_valid_content = bool(specialist_response and specialist_response.strip())
        if (has_valid_content or specialist_tools) and supervisor_run_id and db:
            engine = None
            try:
                # 创建异步引擎（使用 asyncpg 驱动）
                engine = create_async_engine(DATABASE_URL_ASYNC, echo=False)

                # 生成消息 ID 和时间戳
                message_id = str(uuid.uuid4())
                created_at = int(time.time())

                # 构建消息 JSON 结构（基于 Agno 的数据格式）
                # ⚠️ 确保 content 不为空，使用占位符（Full Agent 加载历史时会检查 content 字段）
                safe_content = specialist_response if (specialist_response and specialist_response.strip()) else "（工具调用完成）"
                message_json = {
                    "id": message_id,
                    "role": "assistant",  # ✅ 专家回答使用 "assistant" 角色
                    "content": safe_content,  # ✅ 使用安全的内容（非空）
                    "reasoning_content": thought_process,  # ✅ 使用 Agno 标准字段存储推理过程
                    "created_at": created_at,
                    "from_history": False,
                    "stop_after_tool_call": False,
                }

                # 使用 JSONB 追加消息和工具到 ai.agent_sessions 表的 runs 字段
                # 同时更新 messages 和 tools 字段
                update_sql = text("""
                    UPDATE ai.agent_sessions
                    SET runs = (
                        SELECT jsonb_agg(
                            CASE
                                WHEN (elem->>'run_id') = :run_id
                                THEN
                                    -- 先更新 messages
                                    jsonb_set(
                                        -- 再更新 tools
                                        jsonb_set(
                                            elem,
                                            ARRAY['messages'],
                                            (elem->'messages') || CAST(:message_json AS jsonb)
                                        ),
                                        ARRAY['tools'],
                                        COALESCE((elem->'tools') || CAST(:tools_json AS jsonb), CAST(:tools_json AS jsonb))
                                    )
                                ELSE elem
                            END
                        )
                        FROM jsonb_array_elements(runs) AS elem
                    )
                    WHERE session_id = :session_id
                      AND user_id = :user_id
                """)

                # 异步执行更新
                async with engine.begin() as conn:
                    await conn.execute(update_sql, {
                        "session_id": workflow.session_id,
                        "user_id": workflow.user_id,
                        "run_id": supervisor_run_id,
                        "message_json": json.dumps(message_json),
                        "tools_json": json.dumps(specialist_tools) if specialist_tools else "[]",
                    })

                logger.info(f"[Supervisor Workflow Stream] 手动保存专家回答到 run: {supervisor_run_id}, message_id: {message_id}, tools: {len(specialist_tools)}, thinking: {thought_process[:100] if thought_process else '(空)'}...")
            except Exception as e:
                logger.warning(f"[Supervisor Workflow Stream] 手动保存专家回答失败: {e}", exc_info=True)
            finally:
                # ✅ 确保关闭引擎，避免连接泄漏
                if engine:
                    await engine.dispose()
                    logger.debug("[Supervisor Workflow Stream] 数据库引擎已关闭")


    except Exception as e:
        logger.error(f"[Supervisor Workflow Stream] 执行失败: {e}", exc_info=True)
        yield {
            "type": "error",
            "content": str(e)
        }

