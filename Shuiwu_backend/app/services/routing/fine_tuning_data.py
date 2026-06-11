"""
微调数据管理器 - 负责高质量对话数据的收集、清洗、格式化

职责：
1. 从数据库导出历史对话（筛选高质量样本）
2. 数据清洗和脱敏处理
3. 转换为 QLoRA 训练所需的 JSONL 格式
4. 版本管理和增量更新

设计原则：
- 数据安全：自动脱敏敏感信息（身份证、金额等）
- 质量优先：只选择评分高的对话进行微调
- 增量支持：每月/每周可以增量添加新数据
"""

import json
import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)


@dataclass
class FineTuningSample:
    """微调样本"""
    conversation_id: str
    messages: List[Dict[str, str]]
    quality_score: float
    tags: List[str]
    created_at: str
    
    def to_training_format(self) -> Dict:
        """转换为训练格式"""
        return {
            "conversations": self.messages,
            "quality_score": self.quality_score,
        }


class DataCleaner:
    """数据清洗器 - 处理隐私和格式问题"""
    
    SENSITIVE_PATTERNS = {
        'id_card': r'\d{17}[\dXx]|\d{15}',
        'phone': r'1[3-9]\d{9}',
        'amount_large': r'[\d,]+\.?\d*\s*(万|亿)?元',
        'company_name': r'[^\s，。！？]{2,}(有限公司|股份公司|集团|企业)',
        'tax_number': r'\d{9}|[A-Z0-9]{15,20}',
    }
    
    MASK_TEMPLATES = {
        'id_card': '[身份证号已脱敏]',
        'phone': '[手机号已脱敏]',
        'amount_large': '[金额已脱敏]',
        'company_name': '[公司名称已脱敏]',
        'tax_number': '[税号已脱敏]',
    }
    
    @classmethod
    def clean_message(cls, message: str) -> Tuple[str, int]:
        """
        清洗单条消息
        
        Returns:
            (清洗后的文本, 替换数量)
        """
        if not message:
            return message, 0
        
        cleaned = message
        total_replacements = 0
        
        for pattern_name, pattern in cls.SENSITIVE_PATTERNS.items():
            matches = re.findall(pattern, cleaned)
            if matches:
                count = len(matches)
                cleaned = re.sub(pattern, cls.MASK_TEMPLATES[pattern_name], cleaned)
                total_replacements += count
                logger.debug(f"[DataCleaner] 脱敏: {pattern_name} x{count}")
        
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned, total_replacements
    
    @classmethod
    def clean_conversation(cls, messages: List[Dict]) -> Tuple[List[Dict], int]:
        """
        清洗完整对话
        
        Returns:
            (清洗后的消息列表, 总替换数)
        """
        cleaned_messages = []
        total = 0
        
        for msg in messages:
            content = msg.get('content', '')
            cleaned_content, count = cls.clean_message(content)
            
            if cleaned_content:
                cleaned_messages.append({
                    **msg,
                    'content': cleaned_content,
                })
                total += count
        
        return cleaned_messages, total


class QualityScorer:
    """质量评分器 - 评估对话质量"""
    
    MIN_LENGTH_USER = 3
    MIN_LENGTH_ASSISTANT = 10
    MAX_LENGTH_ASSISTANT = 2000
    OPTIMAL_LENGTH_RANGE = (50, 500)
    
    HIGH_QUALITY_KEYWORDS = [
        '根据', '按照', '依据', '规定', '条例',
        '税率', '扣除', '抵扣', '申报', '纳税',
        '计算公式', '步骤', '注意', '建议',
    ]
    
    LOW_QUALITY_PATTERNS = [
        r'^[嗯哦啊哈好行]{1,3}$',
        r'^我不知道',
        r'^这个问题',
        r'^抱歉.*无法',
        r'^作为AI',
    ]
    
    @classmethod
    def score(cls, user_msg: str, assistant_msg: str) -> float:
        """
        对一轮对话进行质量评分 (0.0 - 1.0)
        
        评分维度：
        - 长度合理性 (30%)
        - 内容丰富度 (30%)
        - 专业性 (25%)
        - 格式规范 (15%)
        """
        score = 0.0
        
        length_score = cls._score_length(user_msg, assistant_msg)
        richness_score = cls._score_richness(assistant_msg)
        professional_score = cls._score_professional(assistant_msg)
        format_score = cls._score_format(assistant_msg)
        
        score = (
            length_score * 0.30 +
            richness_score * 0.30 +
            professional_score * 0.25 +
            format_score * 0.15
        )
        
        return round(min(score, 1.0), 3)
    
    @classmethod
    def _score_length(cls, user_msg: str, assistant_msg: str) -> float:
        user_len = len(user_msg.strip())
        asst_len = len(assistant_msg.strip())
        
        if user_len < cls.MIN_LENGTH_USER or asst_len < cls.MIN_LENGTH_ASSISTANT:
            return 0.2
        if asst_len > cls.MAX_LENGTH_ASSISTANT:
            return 0.6
        
        optimal_min, optimal_max = cls.OPTIMAL_LENGTH_RANGE
        if optimal_min <= asst_len <= optimal_max:
            return 1.0
        elif asst_len < optimal_min:
            return 0.5 + (asst_len / optimal_min) * 0.5
        else:
            return 1.0 - ((asst_len - optimal_max) / (cls.MAX_LENGTH_ASSISTAN - optimal_max)) * 0.4
    
    @classmethod
    def _score_richness(cls, text: str) -> float:
        sentences = re.split(r'[。！？\n]', text)
        non_empty = [s for s in sentences if s.strip()]
        
        if len(non_empty) >= 3:
            return 1.0
        elif len(non_empty) >= 2:
            return 0.7
        elif len(non_empty) == 1:
            return 0.4
        else:
            return 0.1
    
    @classmethod
    def _score_professional(cls, text: str) -> float:
        keyword_count = sum(1 for kw in cls.HIGH_QUALITY_KEYWORDS if kw in text)
        
        if keyword_count >= 3:
            return 1.0
        elif keyword_count >= 2:
            return 0.7
        elif keyword_count >= 1:
            return 0.5
        else:
            return 0.3
    
    @classmethod
    def _score_format(cls, text: str) -> float:
        has_structure = any([
            '```' in text,
            '**' in text or '##' in text,
            re.search(r'\d+[.、)]', text),
            re.search(r'[：:]\s', text),
        ])
        
        has_emoji = bool(re.search(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF]', text))
        
        base_score = 0.8 if has_structure else 0.5
        if has_emoji:
            base_score -= 0.2
        
        return max(base_score, 0.1)


class ConversationTagger:
    """对话标签器 - 自动标注场景类型"""
    
    TAG_RULES = {
        'greeting': [r'^(你好|您好|嗨|hi)', r'(在吗|有人吗)'],
        'self_intro': [r'(你是谁|介绍.*你|你的功能)', r'(自我介绍|关于你)'],
        'policy_query': [r'(政策|法规|条例|规定|通知)', r'(税率|税收|税务)'],
        'calculation': [r'(算|计算|多少|怎么算)', r'(税额|应纳|所得额)'],
        'process_guide': [r'(怎么|如何|流程|步骤)', r'(办理|申报|操作)'],
        'case_analysis': [r'(案例|例子|实例)', r'(分析|对比|比较)'],
        'document_review': [r'(合同|协议|条款)', r'(审查|审核|风险)'],
        'security_refusal': [r'(逃税|偷税|虚开|骗税)', r'(违法|违规)'],
    }
    
    @classmethod
    def tag(cls, messages: List[Dict]) -> List[str]:
        full_text = ' '.join([m.get('content', '') for m in messages])
        tags = []
        
        for tag_name, patterns in cls.TAG_RULES.items():
            for pattern in patterns:
                if re.search(pattern, full_text, re.IGNORECASE):
                    tags.append(tag_name)
                    break
        
        return tags[:5]


class FineTuningDataManager:
    """
    微调数据管理器
    
    完整的数据流水线：
    导出 → 清洗 → 评分 → 标注 → 格式化 → 输出
    """
    
    MIN_QUALITY_SCORE = 0.45
    TARGET_SAMPLES_PER_CATEGORY = 3000
    MAX_TOTAL_SAMPLES = 20000
    
    def __init__(self):
        self.cleaner = DataCleaner()
        self.scorer = QualityScorer()
        self.tagger = ConversationTagger()
    
    def prepare_training_data(
        self,
        raw_conversations: List[Dict[str, Any]],
        output_path: str,
    ) -> Dict[str, Any]:
        """
        准备训练数据的完整流水线
        
        Args:
            raw_conversations: 原始对话列表（从数据库导出）
            output_path: 输出文件路径 (.jsonl)
        
        Returns:
            统计信息字典
        """
        logger.info(f"[FineTuningDataManager] 开始处理 {len(raw_conversations)} 条原始对话")
        
        stats = {
            'input_count': len(raw_conversations),
            'after_cleaning': 0,
            'after_scoring': 0,
            'final_output': 0,
            'by_tag': {},
            'avg_quality_score': 0,
            'desensitized_items': 0,
        }
        
        all_samples: List[FineTuningSample] = []
        
        for conv in raw_conversations:
            try:
                messages = conv.get('messages', [])
                if not messages or len(messages) < 2:
                    continue
                
                cleaned_messages, desensitization_count = self.cleaner.clean_conversation(messages)
                
                stats['desensitized_items'] += desensitization_count
                
                if not cleaned_messages:
                    continue
                
                stats['after_cleaning'] += 1
                
                sample_scores = []
                formatted_messages = []
                
                for i in range(0, len(cleaned_messages) - 1, 2):
                    if i + 1 < len(cleaned_messages):
                        user_msg = cleaned_messages[i]
                        asst_msg = cleaned_messages[i + 1]
                        
                        if user_msg.get('role') != 'user' or asst_msg.get('role') != 'assistant':
                            continue
                        
                        score = self.scorer.score(
                            user_msg.get('content', ''),
                            asst_msg.get('content', '')
                        )
                        sample_scores.append(score)
                        
                        formatted_messages.append(user_msg)
                        formatted_messages.append(asst_msg)
                
                if not sample_scores:
                    continue
                
                avg_score = sum(sample_scores) / len(sample_scores)
                
                if avg_score < self.MIN_QUALITY_SCORE:
                    continue
                
                stats['after_scoring'] += 1
                
                tags = self.tagger.tag(cleaned_messages)
                
                sample = FineTuningSample(
                    conversation_id=conv.get('id', 'unknown'),
                    messages=formatted_messages,
                    quality_score=avg_score,
                    tags=tags,
                    created_at=conv.get('created_at', datetime.now().isoformat()),
                )
                
                all_samples.append(sample)
                
                for tag in tags:
                    stats['by_tag'][tag] = stats['by_tag'].get(tag, 0) + 1
                
            except Exception as e:
                logger.warning(f"[FineTuningDataManager] 处理对话失败: {e}")
                continue
        
        all_samples.sort(key=lambda x: x.quality_score, reverse=True)
        
        final_samples = self._balance_samples(all_samples)
        stats['final_output'] = len(final_samples)
        
        if final_samples:
            stats['avg_quality_score'] = round(
                sum(s.quality_score for s in final_samples) / len(final_samples), 3
            )
        
        self._save_to_jsonl(final_samples, output_path)
        
        logger.info(f"[FineTuningDataManager] 处理完成: {stats}")
        
        return stats
    
    def _balance_samples(self, samples: List[FineTuningSample]) -> List[FineTuningSample]:
        """
        平衡各分类的样本数量
        
        确保每个标签都有足够的代表性，
        同时避免某个类别过多导致模型偏向
        """
        from collections import defaultdict
        
        tag_buckets = defaultdict(list)
        untagged = []
        
        for sample in samples:
            if sample.tags:
                for tag in sample.tags[:1]:
                    tag_buckets[tag].append(sample)
            else:
                untagged.append(sample)
        
        balanced = []
        
        for tag, bucket in tag_buckets.items():
            target = min(len(bucket), self.TARGET_SAMPLES_PER_CATEGORY)
            balanced.extend(bucket[:target])
        
        remaining_slots = self.MAX_TOTAL_SAMPLES - len(balanced)
        if remaining_slots > 0 and untagged:
            balanced.extend(untagged[:remaining_slots])
        
        balanced.sort(key=lambda x: x.quality_score, reverse=True)
        
        return balanced[:self.MAX_TOTAL_SAMPLES]
    
    def _save_to_jsonl(self, samples: List[FineTuningSample], output_path: str):
        with open(output_path, 'w', encoding='utf-8') as f:
            for sample in samples:
                training_data = sample.to_training_format()
                f.write(json.dumps(training_data, ensure_ascii=False) + '\n')
        
        logger.info(f"[FineTuningDataManager] 已保存 {len(samples)} 条样本到 {output_path}")


fine_tuning_data_manager = FineTuningDataManager()
