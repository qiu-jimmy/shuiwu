"""
全本地化配置模块 - Qwen2.5-14B 完全本地部署配置

当决定不使用云端API时，使用此配置替换原有的云端模型配置。
所有请求都将路由到本地 vLLM 服务。

配置项：
- 本地模型端点
- 模型参数调优
- RAG增强策略
- 降级策略（当本地模型无法处理时）
"""

import os
from typing import Dict, Any, Optional, List


class LocalDeploymentConfig:
    """
    全本地化部署配置
    
    目标: 在 48GB NVIDIA GPU 上运行 Qwen2.5-14B，
         覆盖 90%+ 的税务咨询场景
    """
    
    VLLM_CONFIG = {
        "host": "0.0.0.0",
        "port": 8001,
        
        "model_path": "Qwen/Qwen2.5-14B-Instruct",
        
        "tensor_parallel_size": 1,
        
        "dtype": "half",
        
        "max_model_len": 8192,
        
        "gpu_memory_utilization": 0.85,
        
        "max_num_seqs": 64,
        
        "enable_prefix_caching": True,
        
        "quantization": "awq",
        
        "enforce_eager": False,
        
        "swap_space": 4,
    }
    
    MODEL_ALIASES = {
        "qwen2.5-14b-local": {
            "id": "qwen2.5-14b-local",
            "name": "Qwen2.5-14B 本地部署版",
            "provider": "local",
            "model_url": f"http://localhost:{VLLM_CONFIG['port']}/v1",
            "model_api_key": "not-needed-for-local",
            "description": "本地部署的 Qwen2.5-14B-Instruct (AWQ-4bit量化)",
            "status": "active",
            "context_window": 8192,
            "is_local": True,
            "deployment_type": "vllm",
            "max_tokens": 4096,
        },
    }
    
    ROUTING_OVERRIDES = {
        "force_local": True,
        
        "fallback_to_cloud": False,
        
        "cloud_fallback_threshold": 0.3,
        
        "default_model_id": "qwen2.5-14b-local",
        
        "supervisor_model_id": "qwen2.5-14b-local",
        
        "expert_model_id": "qwen2.5-14b-local",
        
        "contract_review_model_id": "qwen2.5-14b-local",
    }
    
    CAPABILITY_LIMITS = {
        "max_context_length": 8192,
        
        "max_input_chars": 12000,
        
        "max_file_text_length": 8000,
        
        "supports_multimodal": False,
        
        "supports_vision": False,
        
        "max_reasoning_steps": 8,
        
        "recommended_max_conversation_turns": 15,
    }
    
    RAG_ENHANCEMENT = {
        "force_enable_rag_for": [
            "税率", "政策", "法规", "条例", "规定",
            "标准", "限额", "起征点", "扣除",
            "文号", "条款", "条文", "发布日期",
            "最新", "今年", "当前", "现在",
        ],
        
        "always_use_rag_patterns": [
            r'\d{4}年.*政策',
            r'第.*条',
            r'(财税|国税发|国家税务总局).*\d*号?',
            r'.*(税率|标准|比例).*是?(多少|怎么算)',
        ],
        
        "rag_top_k": 5,
        
        "rag_max_chunk_chars": 4000,
        
        "use_full_document_retrieval": True,
        
        "kb_selection_strategy": "semantic",
    }
    
    QUALITY_GUARDS = {
        "min_answer_length": 10,
        
        "max_answer_length": 4096,
        
        "require_citation_for_factual_queries": True,
        
        "uncertainty_phrases": [
            "我不确定", "可能", "也许", "建议咨询",
            "以官方信息为准", "具体请咨询税务机关",
        ],
        
        "auto_append_sources": True,
        
        "detect_hallucination_keywords": [
            "根据我的训练数据",
            "作为一个AI语言模型",
            "我没有实时信息",
        ],
    }
    
    PERFORMANCE_TUNING = {
        "temperature_map": {
            "greeting": 0.8,
            "factual_query": 0.3,
            "analysis": 0.6,
            "creative": 0.9,
            "default": 0.7,
        },
        
        "top_p": 0.9,
        
        "top_k": 50,
        
        "repetition_penalty": 1.05,
        
        "max_new_tokens_map": {
            "simple_qa": 512,
            "detailed_explanation": 2048,
            "analysis_report": 4096,
            "default": 1024,
        },
    }
    
    FALLBACK_STRATEGIES = {
        "model_overload": {
            "action": "queue_request",
            "max_queue_size": 100,
            "queue_timeout_ms": 30000,
            "user_message": "当前服务繁忙，请稍后再试",
        },
        
        "answer_quality_low": {
            "action": "retry_with_different_params",
            "max_retries": 2,
            "param_changes": {"temperature": 0.3, "top_p": 0.95},
        },
        
        "context_too_long": {
            "action": "truncate_and_warn",
            "truncation_strategy": "keep_recent",
            "warning_message": "您的问题较长，已进行智能截断。如需完整分析，建议分段提问。",
        },
        
        "unsupported_capability": {
            "action": "graceful_degrade",
            "multimodal_fallback": "请将图片内容复制为文字后重新提问",
            "long_context_fallback": "文档过长，建议分章节上传分析",
        },
    }


def get_local_config() -> Dict[str, Any]:
    """获取完整本地化配置"""
    return {
        "vllm": LocalDeploymentConfig.VLLM_CONFIG,
        "models": LocalDeploymentConfig.MODEL_ALIASES,
        "routing": LocalDeploymentConfig.ROUTING_OVERRIDES,
        "capabilities": LocalDeploymentConfig.CAPABILITY_LIMITS,
        "rag": LocalDeploymentConfig.RAG_ENHANCEMENT,
        "quality": LocalDeploymentConfig.QUALITY_GUARDS,
        "performance": LocalDeploymentConfig.PERFORMANCE_TUNING,
        "fallback": LocalDeploymentConfig.FALLBACK_STRATEGIES,
    }


def is_local_deployment_enabled() -> bool:
    """检查是否启用全本地化模式"""
    return os.getenv("ENABLE_LOCAL_DEPLOYMENT", "false").lower() == "true"


def get_effective_model_id(requested_model_id: str) -> str:
    """
    获取实际使用的模型ID
    
    在全本地化模式下，所有模型ID都映射到本地模型
    """
    if not is_local_deployment_enabled():
        return requested_model_id
    
    return LocalDeploymentConfig.ROUTING_OVERRIDES.get(
        "default_model_id",
        "qwen2.5-14b-local"
    )


def should_force_rag(user_message: str) -> bool:
    """判断是否应该强制启用RAG"""
    force_keywords = LocalDeploymentConfig.RAG_ENHANCEMENT["force_enable_rag_for"]
    
    for keyword in force_keywords:
        if keyword in user_message:
            return True
    
    import re
    patterns = LocalDeploymentConfig.RAG_ENHANCEMENT.get("always_use_rag_patterns", [])
    for pattern in patterns:
        if re.search(pattern, user_message):
            return True
    
    return False


def get_temperature_for_scenario(scenario: str) -> float:
    """根据场景获取推荐的温度参数"""
    return LocalDeploymentConfig.PERFORMANCE_TUNING["temperature_map"].get(
        scenario,
        LocalDeploymentConfig.PERFORMANCE_TUNING["temperature_map"]["default"]
    )
