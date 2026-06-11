"""
本地微调训练脚本 - 基于 QLoRA 在 48GB GPU 上微调 Qwen2.5-7B

使用技术：
- QLoRA (4-bit 量化 + Low-Rank Adaptation)
- bitsandbytes (量化)
- PEFT (Parameter-Efficient Fine-Tuning)
- transformers (模型加载)

硬件要求：
- NVIDIA GPU 显存 >= 24GB (推荐 48GB)
- 训练时间：2万条数据 ≈ 3-4小时 (A100等效) / 6-8小时 (RTX 4090/3090)

使用方式：
    python scripts/train_finetune.py \
        --data_path data/training_data.jsonl \
        --output_dir models/qwen2.5-7b-tax-v1 \
        --num_epochs 3 \
        --batch_size 4
"""

import os
import sys
import json
import torch
import logging
import argparse
from datetime import datetime
from typing import List, Dict, Any


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_gpu():
    """检查GPU环境"""
    if not torch.cuda.is_available():
        raise RuntimeError("❌ CUDA不可用，请检查NVIDIA驱动和CUDA安装")
    
    gpu_name = torch.cuda.get_device_name(0)
    total_memory_gb = torch.cuda.get_device_properties(0).total_mem / (1024**3)
    
    logger.info(f"🎮 GPU: {gpu_name}")
    logger.info(f"💾 显存: {total_memory_gb:.1f} GB")
    
    if total_memory_gb < 20:
        logger.warning(f"⚠️  显存不足20GB，建议使用更小的模型或更激进的量化")
    
    return gpu_name, total_memory_gb


def load_training_data(data_path: str) -> List[Dict]:
    """加载训练数据（JSONL格式）"""
    data = []
    
    with open(data_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                item = json.loads(line)
                conversations = item.get('conversations', [])
                
                if len(conversations) >= 2 and conversations[0].get('role') == 'user':
                    data.append(item)
                    
            except json.JSONDecodeError as e:
                logger.warning(f"第{line_num}行JSON解析失败: {e}")
                continue
    
    logger.info(f"📊 加载了 {len(data)} 条训练样本")
    
    return data


def create_model_and_tokenizer(model_name: str, device_map: str = "auto"):
    """
    创建量化模型和分词器
    
    使用 4-bit NF4 量化，大幅降低显存占用
    """
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import prepare_model_for_kbit_training
    
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )
    
    logger.info(f"🔄 加载模型: {model_name}")
    logger.info("   使用 4-bit NF4 量化...")
    
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map=device_map,
        trust_remote_code=True,
    )
    
    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=True,
        padding_side='right',
    )
    
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    model = prepare_model_for_kbit_training(model)
    
    logger.info("✅ 模型和分词器加载完成")
    
    return model, tokenizer


def setup_lora_config(r: int = 16, lora_alpha: int = 32, lora_dropout: float = 0.05):
    """配置LoRA参数"""
    from peft import LoraConfig, TaskType, get_peft_model
    
    lora_config = LoraConfig(
        r=r,
        lora_alpha=lora_alpha,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=lora_dropout,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    
    logger.info(f"⚙️  LoRA配置: r={r}, alpha={lora_alpha}, dropout={lora_dropout}")
    
    return lora_config


def format_conversation(messages: List[Dict], tokenizer) -> str:
    """
    格式化对话为Qwen2.5的训练格式
    
    Qwen2.5 使用 ChatML 格式:
    <|im_start|>system\n{system}<|im_end|>
    <|im_start|>user\n{user}<|im_end|>
    <|im_start|>assistant\n{assistant}<|im_end|>
    """
    SYSTEM_PROMPT = """你是"税小通"，一个专业的税务智能助手。

你的职责：
- 回答税务相关问题（政策、法规、计算等）
- 提供专业的税务咨询和筹划建议
- 解释复杂的税务概念和流程

回答原则：
1. 使用专业但易懂的语言
2. 引用政策时注明文号和条款
3. 计算问题要展示步骤
4. 不确定的信息要说明来源
5. 严禁使用emoji符号
6. 数学公式用普通文本表达，禁止LaTeX格式"""

    formatted = f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n"
    
    for msg in messages:
        role = msg['role']
        content = msg['content']
        
        if role in ['user', 'assistant', 'tool']:
            formatted += f"<|im_start|>{role}\n{content}<|im_end|>\n"
    
    formatted += "<|im_start|>assistant\n"
    
    return formatted


def train(
    data_path: str,
    output_dir: str,
    base_model: str = "Qwen/Qwen2.5-7B-Instruct",
    num_epochs: int = 3,
    batch_size: int = 4,
    gradient_accumulation_steps: int = 4,
    learning_rate: float = 2e-4,
    max_seq_length: int = 2048,
    lora_r: int = 16,
    warmup_ratio: float = 0.05,
):
    """
    执行完整的微调训练流程
    """
    start_time = datetime.now()
    
    logger.info("=" * 60)
    logger.info("  税小通 - 本地微调训练")
    logger.info("=" * 60)
    logger.info(f"  开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"  基础模型: {base_model}")
    logger.info(f"  训练数据: {data_path}")
    logger.info(f"  输出目录: {output_dir}")
    logger.info(f"  训练轮数: {num_epochs}")
    logger.info(f"  批次大小: {batch_size}")
    logger.info("=" * 60)
    
    check_gpu()
    
    training_data = load_training_data(data_path)
    
    if not training_data:
        raise ValueError("❌ 没有有效的训练数据")
    
    model, tokenizer = create_model_and_tokenizer(base_model)
    
    lora_config = setup_lora_config(r=lora_r)
    
    from peft import get_peft_model
    model = get_peft_model(model, lora_config)
    
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    all_params = sum(p.numel() for p in model.parameters())
    
    logger.info(f"📈 可训练参数: {trainable_params:,} / {all_params:,} ({100*trainable_params/all_params:.2f}%)")
    
    class TaxDataset(torch.utils.data.Dataset):
        def __init__(self, data, tokenizer, max_length):
            self.data = data
            self.tokenizer = tokenizer
            self.max_length = max_length
        
        def __len__(self):
            return len(self.data)
        
        def __getitem__(self, idx):
            item = self.data[idx]
            messages = item.get('conversations', [])
            
            text = format_conversation(messages, self.tokenizer)
            
            result = self.tokenizer(
                text,
                truncation=True,
                max_length=self.max_length,
                padding='max_length',
                return_tensors=None,
            )
            
            result["labels"] = result["input_ids"].copy()
            
            return result
    
    dataset = TaxDataset(training_data, tokenizer, max_seq_length)
    
    train_size = int(0.95 * len(dataset))
    val_size = len(dataset) - train_size
    
    train_dataset, val_dataset = torch.utils.data.random_split(
        dataset, [train_size, val_size]
    )
    
    logger.info(f"📦 数据集划分: 训练={train_size}, 验证={val_size}")
    
    from transformers import TrainingArguments, Trainer, DataCollatorForSeq2Seq
    
    output_path = os.path.join(output_dir, f"finetuned_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
    training_args = TrainingArguments(
        output_dir=output_path,
        num_train_epochs=num_epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size * 2,
        gradient_accumulation_steps=gradient_accumulation_steps,
        learning_rate=learning_rate,
        warmup_ratio=warmup_ratio,
        logging_steps=10,
        save_strategy="epoch",
        eval_strategy="epoch",
        bf16=True,
        fp16=False,
        gradient_checkpointing=True,
        optim="paged_adamw_32bit",
        lr_scheduler_type="cosine",
        report_to="none",
        save_total_limit=3,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
    )
    
    data_collator = DataCollatorForSeq2Seq(
        tokenizer=tokenizer,
        model=model,
        padding=True,
        return_tensors="pt",
    )
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        data_collator=data_collator,
    )
    
    logger.info("\n🚀 开始训练...\n")
    
    trainer.train()
    
    logger.info("\n✅ 训练完成！保存模型...\n")
    
    final_output_path = os.path.join(output_dir, "final_model")
    model.save_pretrained(final_output_path)
    tokenizer.save_pretrained(final_output_path)
    
    end_time = datetime.now()
    duration = end_time - start_time
    
    logger.info("=" * 60)
    logger.info("  🎉 微调训练完成!")
    logger.info("=" * 60)
    logger.info(f"  结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"  总耗时: {duration}")
    logger.info(f"  模型保存位置: {final_output_path}")
    logger.info("=" * 60)
    
    return final_output_path


def main():
    parser = argparse.ArgumentParser(description="税小通本地微调训练")
    
    parser.add_argument("--data_path", type=str, required=True,
                        help="训练数据路径 (JSONL格式)")
    parser.add_argument("--output_dir", type=str, default="./models/finetuned",
                        help="输出目录")
    parser.add_argument("--base_model", type=str, default="Qwen/Qwen2.5-7B-Instruct",
                        help="基础模型名称或路径")
    parser.add_argument("--num_epochs", type=int, default=3,
                        help="训练轮数")
    parser.add_argument("--batch_size", type=int, default=4,
                        help="批次大小 (根据显存调整)")
    parser.add_argument("--learning_rate", type=float, default=2e-4,
                        help="学习率")
    parser.add_argument("--max_seq_length", type=int, default=2048,
                        help="最大序列长度")
    parser.add_argument("--lora_r", type=int, default=16,
                        help="LoRA秩 (越大表达能力越强)")
    
    args = parser.parse_args()
    
    try:
        output_path = train(
            data_path=args.data_path,
            output_dir=args.output_dir,
            base_model=args.base_model,
            num_epochs=args.num_epochs,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            max_seq_length=args.max_seq_length,
            lora_r=args.lora_r,
        )
        
        print(f"\n✅ 成功！模型已保存到: {output_path}")
        
        print(f"\n下一步操作:")
        print(f"1. 测试模型效果:")
        print(f"   python scripts/test_finetuned.py --model_path {output_path}")
        print(f"\n2. 部署到vLLM:")
        print(f"   vllm serve {output_path} --port 8001")
        print(f"\n3. 更新数据库中的模型配置:")
        print(f"   UPDATE models.models SET model_url='http://localhost:8001/v1' WHERE id='qwen2.5-7b-finetuned';")
        
    except Exception as e:
        logger.error(f"❌ 训练失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
