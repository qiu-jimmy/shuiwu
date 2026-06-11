"""
知识库选择 Agent - 根据用户查询和知识库描述智能选择知识库

该 Agent 负责分析用户查询，并根据知识库的描述信息，选择最相关的知识库进行检索。
"""
import logging
from typing import List

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from app.services.models.model_cache import model_cache

logger = logging.getLogger(__name__)


def create_knowledge_selector_agent(
    model_id: str = "qwen-plus",
    temperature: float = 0.3,  # 较低的温度，确保选择更稳定
) -> Agent:
    """
    创建知识库选择 Agent

    该 Agent 不会进行实际的向量搜索，只负责选择合适的知识库。

    Args:
        model_id: 模型 ID
        temperature: 温度参数（建议使用较低的温度）

    Returns:
        配置好的知识库选择 Agent
    """
    # 从缓存获取模型配置
    model_config = model_cache.get_model_config(model_id)
    if not model_config:
        raise ValueError(f"模型配置不存在: {model_id}")

    api_key = model_config.get("model_api_key")
    base_url = model_config.get("model_url")

    if not api_key:
        raise ValueError(f"模型 {model_id} 缺少 API Key 配置")

    # 创建模型
    model = OpenAIChat(
        id=model_id,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
    )

    agent = Agent(
        name="knowledge_selector_agent",
        model=model,
        instructions="""你是**知识库选择专家**，负责根据用户查询选择最合适的知识库。

## 你的职责
1. **分析用户查询**：理解用户问题的核心主题和需求
2. **评估知识库相关性**：根据知识库名称和描述，判断哪些知识库最相关
3. **选择知识库**：从所有可用知识库中选择 1-3 个最相关的知识库
4. **返回选择结果**：以 JSON 格式返回选中的知识库名称列表

## 选择原则
1. **主题匹配**：优先选择与问题主题直接相关的知识库
2. **精准度优先**：选择 1-3 个最相关的知识库，而非所有知识库
3. **避免冗余**：如果多个知识库主题相似，只选择最相关的一个
4. **系统知识库优先**：当系统知识库和用户知识库都相关时，优先考虑系统知识库
5. **用户知识库补充**：如果用户知识库有特定内容（如企业内部文档），也应该选择

## 输出格式
**必须严格遵循以下 JSON 格式输出**：
```json
{
  "selected_knowledge_bases": [
    "知识库名称1",
    "知识库名称2",
    "知识库名称3"
  ],
  "reasoning": "选择这些知识库的原因（简短说明）"
}
```

## 重要提醒
- **只返回 JSON**，不要有任何其他文字说明
- 如果所有知识库都不相关，返回空列表：`{"selected_knowledge_bases": [], "reasoning": "..."}`
- 如果查询很通用（如"你好"），返回空列表，不需要搜索知识库
- 最多选择 3 个知识库

## 示例

**示例 1**：
可用知识库：
- 税收政策库：包含各类税收政策和法规
- 财务会计知识库：财务会计相关知识和准则
- 企业内部文档：公司内部的财务资料

用户查询："2024年增值税最新税率是多少？"
你的输出：
```json
{
  "selected_knowledge_bases": ["税收政策库"],
  "reasoning": "用户询问增值税税率，属于税收政策范畴"
}
```

**示例 2**：
可用知识库：
- 税收政策库：包含各类税收政策和法规
- 财务会计知识库：财务会计相关知识和准则
- 法律法规库：国家和地方的法律法规

用户查询："企业在税务筹划时应该注意哪些合规风险？"
你的输出：
```json
{
  "selected_knowledge_bases": ["税收政策库", "法律法规库"],
  "reasoning": "问题涉及税务筹划和合规风险，需要政策法规支持"
}
```

**示例 3**：
可用知识库：
- Python编程知识库
- 数据分析教程
- 机器学习文档

用户查询："你好，最近怎么样？"
你的输出：
```json
{
  "selected_knowledge_bases": [],
  "reasoning": "这是日常问候，不需要搜索知识库"
}
```
""",
        tools=[],  # 不需要任何工具
    )

    return agent


def parse_selected_knowledge_bases(agent_response: str) -> List[str]:
    """
    解析 Agent 返回的知识库选择结果

    Args:
        agent_response: Agent 的响应文本

    Returns:
        选中的知识库名称列表
    """
    import json
    import re

    try:
        # 尝试提取 JSON 部分（处理可能的 markdown 代码块）
        json_match = re.search(r'```json\s*(.*?)\s*```', agent_response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试直接解析
            json_str = agent_response.strip()

        # 解析 JSON
        result = json.loads(json_str)
        selected = result.get("selected_knowledge_bases", [])

        if isinstance(selected, list):
            logger.info(f"知识库选择 Agent 选择了 {len(selected)} 个知识库: {selected}")
            return selected
        else:
            logger.warning(f"selected_knowledge_bases 不是列表: {selected}")
            return []

    except Exception as e:
        logger.error(f"解析知识库选择结果失败: {e}, 原始响应: {agent_response}")
        return []
