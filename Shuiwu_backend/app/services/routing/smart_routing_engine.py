"""
智能路由引擎 - 微调+RAG+工具三层协作的核心调度器

核心职责：
1. 分析用户意图，决定使用哪些能力层（微调/RAG/工具）
2. 选择最优的模型（本地微调 vs 云端API）
3. 协调各层的执行顺序和数据流转
4. 监控和记录每次决策，用于持续优化

设计原则：
- 策略模式：路由规则可配置、可热更新
- 责任链：多层处理器按优先级执行
- 可观测性：每个决策都有完整的日志和指标
"""

import re
import time
import json
import hashlib
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod


logger = logging.getLogger(__name__)


class Capability(Enum):
    """能力类型枚举"""
    FINE_TUNED = "fine_tuned"       # 微调模型能力
    RAG_RETRIEVAL = "rag_retrieval" # RAG检索能力
    TOOL_USE = "tool_use"           # 工具调用能力
    CLOUD_LLM = "cloud_llm"         # 云端大模型能力
    MULTIMODAL = "multimodal"       # 多模态能力


class ComplexityLevel(Enum):
    """问题复杂度等级"""
    SIMPLE = "simple"           # 简单（问候、固定问答）
    FACTUAL = "factual"         # 事实查询（需精确答案）
    ANALYTICAL = "analytical"   # 分析型（需推理）
    COMPLEX = "complex"         # 复杂（多步骤、多工具）


@dataclass
class RoutingContext:
    """路由上下文 - 包含所有决策所需的信息"""
    
    user_message: str
    user_id: str
    session_id: str
    session_type: str  # normal / full / contract_review
    
    history_length: int = 0
    has_files: bool = False
    has_images: bool = False
    user_tier: str = "free"
    
    extracted_entities: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def message_length(self) -> int:
        return len(self.user_message.strip())


@dataclass
class RoutingDecision:
    """路由决策结果"""
    
    decision_id: str
    timestamp: float
    
    primary_model: str              # 主要使用的模型ID
    fallback_model: str             # 备用模型ID
    
    required_capabilities: List[Capability]  # 需要的能力列表
    complexity_level: ComplexityLevel
    
    enable_rag: bool                # 是否启用RAG
    enable_search: bool             # 是否启用搜索
    rag_kb_filter: Optional[str]    # RAG知识库过滤（可选）
    
    confidence: float               # 决策置信度 (0-1)
    reasoning: str                  # 决策原因
    processing_time_ms: float        # 决策耗时
    
    metadata: Dict[str, Any] = field(default_factory=dict)


class IntentClassifier(ABC):
    """意图分类器抽象基类"""
    
    @abstractmethod
    def classify(self, context: RoutingContext) -> Tuple[ComplexityLevel, float]:
        """
        分类用户意图
        
        Returns:
            (复杂度等级, 置信度)
        """
        pass


class TaxDomainIntentClassifier(IntentClassifier):
    """
    税务领域专用意图分类器
    
    基于规则 + 关键词的多维度分类，
    后续可以替换为轻量级本地模型的语义分类
    """
    
    GREETING_PATTERNS = [
        r'^(你好|您好|嗨|hi|hello)[\s！!？?。.,]*$',
        r'^(在吗|在不在|有人吗|在的)[\s！!？?。.,]*$',
        r'^(谢谢|感谢|多谢|好的|收到|ok|OK|嗯|哦)[\s！!？?。.,]*$',
        r'^(再见|拜拜|bye|晚安)[\s！!？?。.,]*$',
        r'^[\s！!？?。.,]+$',
    ]
    
    SELF_INTRO_PATTERNS = [
        r'(你是谁|你是什么|介绍一下.*你|你的功能|你能做什么)',
        r'(自我介绍|关于你|你是干什么的)',
        r'(有什么功能|怎么使用|如何使用.*你)',
    ]
    
    TIME_QUERY_PATTERNS = [
        r'(今天|明天|昨天|现在|当前).*(几号|号|星期|周|几点|时间|日期|年|月)',
        r'(几号|星期|周|几点|时间|日期).*(是|了|了没)',
        r'^(现在|当前).*(什么时间|几点|几号)',
    ]
    
    POLICY_FACT_PATTERNS = [
        r'(税率|标准|比例|限额|起征点|扣除标准).*是?(多少|多少|怎么算|怎么算)',
        r'(什么是|什么叫|如何理解).*税',
        r'(最新|今年|当前|现在).*(政策|法规|规定|条例|通知)',
        r'(财税|国税发|国家税务总局|公告|函).*\d{4}.*号?',
        r'第.*条.*(款|项|规定|内容|怎么说)',
    ]
    
    ANALYSIS_KEYWORDS = {
        'high_weight': ['分析', '对比', '比较', '筹划', '优化', '评估', '测算', '建议'],
        'medium_weight': ['方案', '策略', '流程', '申报', '填报', '案例', '实操'],
        'low_weight': ['怎么', '如何', '能否', '是否', '可以'],
    }
    
    FORCE_CLOUD_KEYWORDS = [
        '合同', '协议', '条款', '法律效力', '合规审计',
        '尽职调查', '跨境', '国际税收', '转让定价',
        'IPO', '上市', '并购重组', '风险评估',
    ]
    
    SECURITY_VIOLATION_KEYWORDS = [
        '逃税', '偷税', '漏税', '虚开', '骗税',
        '洗钱', '做假账', '隐瞒收入', '虚假申报',
    ]
    
    def classify(self, context: RoutingContext) -> Tuple[ComplexityLevel, float]:
        msg = context.user_message.strip()
        msg_lower = msg.lower()
        
        if not msg:
            return ComplexityLevel.SIMPLE, 0.99
        
        score_simple = 0.0
        score_factual = 0.0
        score_analytical = 0.0
        score_complex = 0.0
        
        if self._match_any(msg, self.GREETING_PATTERNS):
            score_simple += 0.95
            logger.debug(f"[IntentClassifier] 匹配问候语")
        
        if self._match_any(msg, self.SELF_INTRO_PATTERNS):
            score_simple += 0.90
            logger.debug(f"[IntentClassifier] 匹配自我介绍")
        
        if self._match_any(msg, self.TIME_QUERY_PATTERNS):
            score_factual += 0.70
            score_simple += 0.20
            logger.debug(f"[IntentClassifier] 匹配时间查询")
        
        if self._match_any(msg, self.POLICY_FACT_PATTERNS):
            score_factual += 0.85
            logger.debug(f"[IntentClassifier] 匹配政策事实查询")
        
        for kw in self.ANALYSIS_KEYWORDS['high_weight']:
            if kw in msg_lower:
                score_analytical += 0.15
        
        for kw in self.ANALYSIS_KEYWORDS['medium_weight']:
            if kw in msg_lower:
                score_analytical += 0.08
        
        analysis_count = sum(1 for kw in self.ANALYSIS_KEYWORDS['high_weight'] if kw in msg_lower)
        if analysis_count >= 2:
            score_complex += 0.30
            score_analytical += 0.20
        
        for kw in self.FORCE_CLOUD_KEYWORDS:
            if kw in msg_lower:
                score_complex += 0.40
                logger.debug(f"[IntentClassifier] 检测到强制云端关键词: {kw}")
        
        if context.has_files or context.has_images:
            score_complex += 0.35
            logger.debug(f"[IntentClassifier] 检测到文件/图片附件")
        
        if context.history_length > 15:
            score_analytical += 0.20
            logger.debug(f"[IntentClassifier] 长历史对话 ({context.history_length}轮)")
        
        for kw in self.SECURITY_VIOLATION_KEYWORDS:
            if kw in msg_lower:
                score_simple += 0.10
                logger.debug(f"[IntentClassifier] 检测到安全相关关键词: {kw}")
        
        scores = {
            ComplexityLevel.SIMPLE: score_simple,
            ComplexityLevel.FACTUAL: score_factual,
            ComplexityLevel.ANALYTICAL: score_analytical,
            ComplexityLevel.COMPLEX: score_complex,
        }
        
        best_level = max(scores, key=scores.get)
        best_score = scores[best_level]
        
        logger.info(
            f"[IntentClassifier] 分类结果: {best_level.value} "
            f"(分数: S={score_simple:.2f}, F={score_factual:.2f}, "
            f"A={score_analytical:.2f}, C={score_complex:.2f})"
        )
        
        return best_level, min(best_score, 1.0)
    
    def _match_any(self, text: str, patterns: list) -> bool:
        for pattern in patterns:
            try:
                if re.search(pattern, text, re.IGNORECASE):
                    return True
            except re.error:
                continue
        return False


class CapabilityPlanner(ABC):
    """能力规划器抽象基类"""
    
    @abstractmethod
    def plan(
        self,
        complexity: ComplexityLevel,
        context: RoutingContext
    ) -> List[Capability]:
        pass


class TaxDomainCapabilityPlanner(CapabilityPlanner):
    """
    税务领域能力规划器
    
    根据问题复杂度和上下文，规划需要启用的能力组合
    """
    
    CAPABILITY_MAP = {
        ComplexityLevel.SIMPLE: [
            Capability.FINE_TUNED,
        ],
        ComplexityLevel.FACTUAL: [
            Capability.RAG_RETRIEVAL,
            Capability.FINE_TUNED,
        ],
        ComplexityLevel.ANALYTICAL: [
            Capability.RAG_RETRIEVAL,
            Capability.TOOL_USE,
            Capability.CLOUD_LLM,
        ],
        ComplexityLevel.COMPLEX: [
            Capability.RAG_RETRIEVAL,
            Capability.TOOL_USE,
            Capability.CLOUD_LLM,
            Capability.MULTIMODAL,
        ],
    }
    
    def plan(
        self,
        complexity: ComplexityLevel,
        context: RoutingContext
    ) -> List[Capability]:
        base_capabilities = self.CAPABILITY_MAP.get(complexity, []).copy()
        
        if context.has_images and Capability.MULTIMODAL not in base_capabilities:
            base_capabilities.append(Capability.MULTIMODAL)
        
        time_patterns = [
            r'(几号|星期|周|几点|时间|日期|年|月)',
            r'(现在|当前).*(时间|几点)',
        ]
        msg = context.user_message.lower()
        if any(re.search(p, msg) for p in time_patterns):
            if Capability.TOOL_USE not in base_capabilities:
                base_capabilities.append(Capability.TOOL_USE)
        
        logger.info(
            f"[CapabilityPlanner] 能力规划: {[c.value for c in base_capabilities]} "
            f"(复杂度: {complexity.value})"
        )
        
        return base_capabilities


class ModelSelector(ABC):
    """模型选择器抽象基类"""
    
    @abstractmethod
    def select(
        self,
        capabilities: List[Capability],
        complexity: ComplexityLevel,
        context: RoutingContext
    ) -> Tuple[str, str]:
        """
        选择主模型和备用模型
        
        Returns:
            (primary_model_id, fallback_model_id)
        """
        pass


class HybridModelSelector(ModelSelector):
    """
    混合模型选择器
    
    策略：
    - 简单问题 → 本地微调模型（免费+快速）
    - 事实查询 → 本地微调 + RAG（精准+低成本）
    - 分析型 → 云端标准模型 + RAG（能力强）
    - 复杂任务 → 云端旗舰模型 + 全部能力（最强能力）
    """
    
    MODEL_POOL = {
        'local_7b_ft': 'qwen2.5-7b-finetuned',
        'local_14b': 'qwen2.5-14b-local',
        'cloud_economy': 'qwen-flash',
        'cloud_standard': 'qwen-plus',
        'cloud_premium': 'qwen-max',
        'cloud_vl': 'qwen-vl-max',
    }
    
    SELECTION_RULES = {
        ComplexityLevel.SIMPLE: {
            'primary': 'local_7b_ft',
            'fallback': 'cloud_economy',
            'reason': '简单问答使用本地微调模型，快速且免费',
        },
        ComplexityLevel.FACTUAL: {
            'primary': 'local_7b_ft',
            'fallback': 'cloud_standard',
            'reason': '事实查询使用本地模型+RAG，确保准确性',
        },
        ComplexityLevel.ANALYTICAL: {
            'primary': 'cloud_standard',
            'fallback': 'cloud_premium',
            'reason': '分析型问题需要强推理能力，使用云端标准模型',
        },
        ComplexityLevel.COMPLEX: {
            'primary': 'cloud_premium',
            'fallback': 'cloud_standard',
            'reason': '复杂任务使用云端旗舰模型，确保质量',
        },
    }
    
    def select(
        self,
        capabilities: List[Capability],
        complexity: ComplexityLevel,
        context: RoutingContext
    ) -> Tuple[str, str]:
        rule = self.SELECTION_RULES.get(complexity, self.SELECTION_RULES[ComplexityLevel.ANALYTICAL])
        
        primary_key = rule['primary']
        fallback_key = rule['fallback']
        
        if Capability.MULTIMODAL in capabilities:
            primary_key = 'cloud_vl'
            fallback_key = 'cloud_premium'
        
        if context.user_tier == 'enterprise':
            if complexity in [ComplexityLevel.ANALYTICAL, ComplexityLevel.COMPLEX]:
                primary_key = 'cloud_premium'
        
        primary_model = self.MODEL_POOL.get(primary_key, 'qwen-plus')
        fallback_model = self.MODEL_POOL.get(fallback_key, 'qwen-plus')
        
        logger.info(
            f"[ModelSelector] 模型选择: 主={primary_model}, 备={fallback_model} "
            f"(复杂度: {complexity.value})"
        )
        
        return primary_model, fallback_model


class KnowledgeBaseRouter:
    """
    知识库路由器
    
    根据查询内容，智能选择最相关的知识库进行检索
    （增强版：支持多知识库联合检索）
    """
    
    KB_SEMANTIC_MAP = {
        'policy': ['政策税务法规', '税收优惠政策', '最新政策通知'],
        'operation': ['操作指引', '系统使用指南', '常见问题解答'],
        'case': ['典型案例', '违法案例', '稽查案例'],
        'calculation': ['税务计算公式', '税率速查表'],
    }
    
    KEYWORD_TO_KB = {
        '税率': '税务计算公式',
        '抵扣': '政策税务法规',
        '发票': '政策税务法规',
        '申报': '操作指引',
        '优惠': '税收优惠政策',
        '处罚': '违法案例',
        '稽查': '稽查案例',
        '计算': '税务计算公式',
        '筹划': '典型案例',
        '风险': '经营风险案例',
        '合同': None,
        '条款': None,
    }
    
    def route(self, query: str, context: RoutingContext) -> Optional[str]:
        query_lower = query.lower()
        
        for keyword, kb_name in self.KEYWORD_TO_KB.items():
            if keyword in query_lower:
                if kb_name:
                    logger.info(f"[KBRouter] 关键词匹配: '{keyword}' → '{kb_name}'")
                    return kb_name
                else:
                    logger.info(f"[KBRouter] 关键词 '{keyword}' 标记为不使用知识库")
                    return None
        
        if len(query) > 200:
            return '政策税务法规'
        
        return '政策税务法规'


class SmartRoutingEngine:
    """
    智能路由引擎 - 微调+RAG+工具三层协作的核心调度器
    
    使用方式：
        engine = SmartRoutingEngine()
        decision = engine.route(context)
        # decision.primary_model, decision.enable_rag, ...
    """
    
    ENABLED = True
    
    def __init__(
        self,
        intent_classifier: IntentClassifier = None,
        capability_planner: CapabilityPlanner = None,
        model_selector: ModelSelector = None,
    ):
        self.intent_classifier = intent_classifier or TaxDomainIntentClassifier()
        self.capability_planner = capability_planner or TaxDomainCapabilityPlanner()
        self.model_selector = model_selector or HybridModelSelector()
        self.kb_router = KnowledgeBaseRouter()
        
        self._stats = {
            'total_routes': 0,
            'by_complexity': {},
            'by_model': {},
            'rag_enabled_count': 0,
            'search_enabled_count': 0,
            'avg_decision_time_ms': 0,
        }
    
    def route(self, context: RoutingContext) -> RoutingDecision:
        """
        执行完整的路由决策流程
        
        流程：
        1. 意图分类 → 问题复杂度
        2. 能力规划 → 需要哪些能力
        3. 模型选择 → 主模型+备用模型
        4. 知识库路由 → 检索哪个知识库
        5. 构建最终决策
        """
        start_time = time.time()
        decision_id = self._generate_decision_id(context)
        
        if not self.ENABLED:
            return self._fallback_decision(decision_id, start_time, context)
        
        try:
            complexity, conf_complexity = self.intent_classifier.classify(context)
            
            capabilities = self.capability_planner.plan(complexity, context)
            
            primary_model, fallback_model = self.model_selector.select(
                capabilities, complexity, context
            )
            
            enable_rag = Capability.RAG_RETRIEVAL in capabilities
            enable_search = Capability.TOOL_USE in capabilities
            
            rag_kb_filter = None
            if enable_rag:
                rag_kb_filter = self.kb_router.route(context.user_message, context)
            
            overall_confidence = (
                conf_complexity * 0.6 +
                (0.9 if enable_rag else 0.5) * 0.2 +
                (0.8 if primary_model.startswith('qwen2') else 0.6) * 0.2
            )
            
            reasoning_parts = [
                f"复杂度={complexity.value}",
                f"能力={[c.value for c in capabilities]}",
                f"主模型={primary_model}",
            ]
            if rag_kb_filter:
                reasoning_parts.append(f"知识库={rag_kb_filter}")
            
            processing_time = (time.time() - start_time) * 1000
            
            decision = RoutingDecision(
                decision_id=decision_id,
                timestamp=time.time(),
                primary_model=primary_model,
                fallback_model=fallback_model,
                required_capabilities=capabilities,
                complexity_level=complexity,
                enable_rag=enable_rag,
                enable_search=enable_search,
                rag_kb_filter=rag_kb_filter,
                confidence=min(overall_confidence, 1.0),
                reasoning=' | '.join(reasoning_parts),
                processing_time_ms=processing_time,
                metadata={
                    'raw_confidence': conf_complexity,
                    'message_length': context.message_length,
                    'has_files': context.has_files,
                    'has_images': context.has_images,
                    'user_tier': context.user_tier,
                }
            )
            
            self._update_stats(decision)
            
            logger.info(
                f"[SmartRoutingEngine] 决策完成: {decision.primary_model} "
                f"(RAG={enable_rag}, Search={enable_search}, "
                f"置信度={decision.confidence:.2f}, "
                f"耗时={processing_time:.1f}ms)"
            )
            
            return decision
            
        except Exception as e:
            logger.error(f"[SmartRoutingEngine] 路由决策失败: {e}", exc_info=True)
            return self._fallback_decision(decision_id, start_time, context)
    
    def _generate_decision_id(self, context: RoutingContext) -> str:
        raw = f"{context.user_id}:{context.session_id}:{time.time()}:{context.user_message[:50]}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]
    
    def _fallback_decision(
        self,
        decision_id: str,
        start_time: float,
        context: RoutingContext
    ) -> RoutingDecision:
        processing_time = (time.time() - start_time) * 1000
        
        return RoutingDecision(
            decision_id=decision_id,
            timestamp=time.time(),
            primary_model='qwen-plus',
            fallback_model='qwen-flash',
            required_capabilities=[Capability.CLOUD_LLM],
            complexity_level=ComplexityLevel.ANALYTICAL,
            enable_rag=True,
            enable_search=True,
            rag_kb_filter=None,
            confidence=0.5,
            reason='兜底决策：路由引擎异常',
            processing_time_ms=processing_time,
        )
    
    def _update_stats(self, decision: RoutingDecision):
        self._stats['total_routes'] += 1
        
        complexity = decision.complexity_level.value
        self._stats['by_complexity'][complexity] = \
            self._stats['by_complexity'].get(complexity, 0) + 1
        
        model = decision.primary_model
        self._stats['by_model'][model] = \
            self._stats['by_model'].get(model, 0) + 1
        
        if decision.enable_rag:
            self._stats['rag_enabled_count'] += 1
        if decision.enable_search:
            self._stats['search_enabled_count'] += 1
        
        total = self._stats['total_routes']
        current_avg = self._stats['avg_decision_time_ms']
        self._stats['avg_decision_time_ms'] = \
            (current_avg * (total - 1) + decision.processing_time_ms) / total
    
    def get_stats(self) -> Dict[str, Any]:
        total = self._stats['total_routes']
        if total == 0:
            return {'message': '暂无路由统计数据'}
        
        return {
            **self._stats,
            'rag_percentage': round(self._stats['rag_enabled_count'] / total * 100, 1),
            'search_percentage': round(self._stats['search_enabled_count'] / total * 100, 1),
            'local_model_percentage': round(
                sum(v for k, v in self._stats['by_model'].items() if 'local' in k or 'finetuned' in k)
                / total * 100, 1
            ),
        }


routing_engine = SmartRoutingEngine()
