"""
为数据集添加推理块并合并打散
"""
import json
import random
from pathlib import Path

BACKUP_DIR = Path(r"D:\zhulong_code\Shuiwu\Shuiwu_backend\Shuiwu_backend\Shuiwu_backend\docs\数据集\backup")
OUTPUT_DIR = Path(r"D:\zhulong_code\Shuiwu\Shuiwu_backend\Shuiwu_backend\Shuiwu_backend\docs\数据集")

def load_jsonl(filepath):
    """加载JSONL文件"""
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data

def save_jsonl(data, filepath):
    """保存JSONL文件"""
    with open(filepath, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

def generate_reasoning(instruction, output):
    """根据问题和答案生成推理块"""
    instruction_lower = instruction.lower()
    
    # 身份类问题
    if "你是谁" in instruction or "自我介绍" in instruction or "你叫什么" in instruction:
        return "用户询问我的身份信息，需要介绍税小通的基本定位和核心功能。我应该清晰地说明我是税务智能助手，专注于税务咨询服务。"
    
    elif "功能" in instruction or "能力" in instruction or "特长" in instruction:
        return "用户想了解我的功能范围，需要列举核心服务能力。我应该系统性地介绍税收政策咨询、税务筹划、风险预警等主要功能。"
    
    elif "公司" in instruction or "开发者" in instruction:
        return "用户询问我的背景信息，需要介绍税小通平台的基本情况。我应该说明平台的专业性和服务范围。"
    
    elif "优势" in instruction or "特点" in instruction or "定位" in instruction:
        return "用户想了解我的优势特色，需要突出专业性、便捷性、准确性等核心价值。我应该强调税务领域的专业优势。"
    
    # 税种相关问题
    elif "增值税" in instruction:
        return "用户询问增值税相关问题，需要准确解释增值税的基本概念、税率、计税方法等。我应该提供专业、准确的税务知识解答。"
    
    elif "企业所得税" in instruction:
        return "用户询问企业所得税相关问题，需要解释税率、扣除项目、优惠政策等。我应该提供符合税法规定的专业解答。"
    
    elif "个人所得税" in instruction:
        return "用户询问个人所得税相关问题，需要解释税率、扣除标准、汇算清缴等。我应该提供实用的个税知识。"
    
    elif "印花税" in instruction or "房产税" in instruction or "契税" in instruction:
        return "用户询问财产税类相关问题，需要解释税种定义、税率、计税依据等。我应该提供准确的财产税知识。"
    
    # 税务筹划类
    elif "筹划" in instruction:
        return "用户询问税务筹划相关问题，需要在合法合规的前提下提供筹划建议。我应该强调合法性和风险防控。"
    
    # 风险防控类
    elif "风险" in instruction:
        return "用户询问税务风险相关问题，需要识别风险点并提供防控建议。我应该帮助用户建立风险意识。"
    
    # 实务操作类
    elif "如何" in instruction or "怎么" in instruction:
        return "用户询问具体操作流程，需要提供清晰的步骤指导。我应该给出可操作的实务建议。"
    
    # 概念解释类
    elif "什么是" in instruction or "定义" in instruction:
        return "用户询问概念定义，需要准确解释专业术语。我应该用通俗易懂的语言解释税务概念。"
    
    # 税率标准类
    elif "税率" in instruction or "标准" in instruction or "多少" in instruction:
        return "用户询问具体税率或标准，需要提供准确的数值和规定。我应该引用现行税法规定。"
    
    # 其他问题
    else:
        return "用户提出税务相关问题，需要分析问题核心，提供专业、准确的解答。我应该基于税务知识库给出权威回答。"

def add_reasoning_to_data(data):
    """为每条数据添加推理块"""
    enhanced_data = []
    
    for item in data:
        instruction = item['instruction']
        output = item['output']
        
        # 生成推理块
        reasoning = generate_reasoning(instruction, output)
        
        # 构建新的输出格式
        new_output = f"  {reasoning}\n\n\n{output}"
        
        # 创建新的数据项
        enhanced_item = {
            "instruction": instruction,
            "input": item.get('input', ''),
            "output": new_output
        }
        
        enhanced_data.append(enhanced_item)
    
    return enhanced_data

def main():
    """主函数"""
    print("=" * 60)
    print("数据集推理块添加与合并工具")
    print("=" * 60)
    
    # 1. 加载数据
    print("\n[1/5] 加载数据文件...")
    identity_data = load_jsonl(BACKUP_DIR / "identity_data_backup.jsonl")
    general_data = load_jsonl(BACKUP_DIR / "general_data_backup.jsonl")
    
    print(f"身份数据: {len(identity_data)} 条")
    print(f"通用数据: {len(general_data)} 条")
    
    # 2. 添加推理块
    print("\n[2/5] 为数据添加推理块...")
    identity_enhanced = add_reasoning_to_data(identity_data)
    general_enhanced = add_reasoning_to_data(general_data)
    
    print(f"身份数据已添加推理块: {len(identity_enhanced)} 条")
    print(f"通用数据已添加推理块: {len(general_enhanced)} 条")
    
    # 3. 合并数据
    print("\n[3/5] 合并身份数据与通用数据...")
    all_data = identity_enhanced + general_enhanced
    print(f"合并后总数据量: {len(all_data)} 条")
    
    # 4. 随机打散
    print("\n[4/5] 随机打散数据...")
    random.seed(42)  # 设置随机种子以确保可重复性
    random.shuffle(all_data)
    print("数据已随机打散")
    
    # 5. 保存数据
    print("\n[5/5] 保存修改后的数据集...")
    
    # 保存合并打散后的数据
    save_jsonl(all_data, OUTPUT_DIR / "shuixiaotong_finetune_800_with_reasoning.jsonl")
    print(f"合并数据已保存: {OUTPUT_DIR / 'shuixiaotong_finetune_800_with_reasoning.jsonl'}")
    
    # 保存带推理块的身份和通用数据（前400条为身份，后400条为通用）
    identity_new = all_data[:400]
    general_new = all_data[400:]
    
    save_jsonl(identity_new, OUTPUT_DIR / "identity_data_with_reasoning.jsonl")
    save_jsonl(general_new, OUTPUT_DIR / "general_data_with_reasoning.jsonl")
    
    print(f"身份数据已保存: {OUTPUT_DIR / 'identity_data_with_reasoning.jsonl'}")
    print(f"通用数据已保存: {OUTPUT_DIR / 'general_data_with_reasoning.jsonl'}")
    
    print("\n" + "=" * 60)
    print("处理完成！")
    print(f"总数据量: {len(all_data)} 条")
    print(f"身份数据: {len(identity_new)} 条")
    print(f"通用数据: {len(general_new)} 条")
    print("=" * 60)
    
    # 显示示例
    print("\n示例数据:")
    print("-" * 60)
    sample = all_data[0]
    print(f"问题: {sample['instruction']}")
    print(f"\n输出:\n{sample['output'][:200]}...")

if __name__ == "__main__":
    main()
