"""
模型配置验证工具
用于验证模型配置是否可用
"""
import time
from typing import Any, Dict

from agno.agent import Agent
from agno.models.openai import OpenAIChat


class ModelValidator:
    """模型配置验证器"""

    @staticmethod
    def validate_model_config(model: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证模型配置是否可用

        使用 Agno Agent 发送测试请求来验证模型配置（API Key、base URL等）是否正确

        Args:
            model: 模型配置字典，包含 id, name, provider, model_api_key, model_url 等字段

        Returns:
            验证结果，包含是否可用、响应时间、错误信息等
        """
        model_id = model.get("id")

        try:
            # 从模型配置中提取参数（直接使用数据库中的值）
            api_key = model.get("model_api_key")
            base_url = model.get("model_url")

            # 检查必需参数
            if not api_key:
                return {
                    "status": "error",
                    "valid": False,
                    "message": "API Key 未配置",
                    "model_id": model_id
                }

            # 创建模型实例
            openai_model = OpenAIChat(
                id=model_id,
                api_key=api_key,
                base_url=base_url,
                temperature=0.7,
            )

            # 创建 Agno Agent（不使用知识库和工具）
            agent = Agent(
                model=openai_model,
                instructions=[],
                markdown=False,
            )

            # 发送测试请求
            start_time = time.time()
            response = agent.run("Hi")
            response_time = time.time() - start_time

            # 检查响应
            if response and hasattr(response, 'content') and response.content:
                return {
                    "status": "success",
                    "valid": True,
                    "message": "模型配置验证成功",
                    "model_id": model_id,
                    "model_name": model.get("name"),
                    "provider": model.get("provider"),
                    "response_time": round(response_time, 2),
                    "test_response": response.content if len(response.content) < 100 else response.content[:100] + "..."
                }
            else:
                return {
                    "status": "error",
                    "valid": False,
                    "message": "模型响应格式异常",
                    "model_id": model_id
                }

        except Exception as e:
            error_msg = str(e)
            # 常见错误信息处理
            if "401" in error_msg or "Unauthorized" in error_msg:
                error_msg = "API Key 无效或已过期"
            elif "404" in error_msg or "Not Found" in error_msg:
                error_msg = "模型不存在或未部署"
            elif "timeout" in error_msg.lower():
                error_msg = "请求超时，请检查网络连接"
            elif "connection" in error_msg.lower():
                error_msg = "无法连接到模型服务，请检查 base URL"

            return {
                "status": "error",
                "valid": False,
                "message": f"验证失败: {error_msg}",
                "model_id": model_id,
                "error_type": type(e).__name__
            }


# 全局实例
model_validator = ModelValidator()
