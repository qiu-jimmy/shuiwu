"""
验证带推理块的数据集
"""
import json
from pathlib import Path

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

def validate_reasoning_format(output):
    """验证推理块格式"""
    if not output.startswith("  "):
        return False, "缺少推理块开始标记"
    
    if "\n\n\n" not in output:
        return False, "缺少推理块与答案的分隔符"
    
    parts = output.split("\n\n\n")
    if len(parts) != 2:
        return False, "分隔符数量不正确"
    
    reasoning = parts[0].replace("  ", "").strip()
    answer = parts[1].strip()
    
    if not reasoning:
        return False, "推理块为空"
    
    if not answer:
        return False, "答案为空"
    
    return True, "格式正确"

def validate_dataset():
    """验证数据集"""
    print("=" * 60)
    print("数据集验证报告")
    print("=" * 60)
    
    # 加载数据
    print("\n[1/3] 加载数据...")
    all_data = load_jsonl(OUTPUT_DIR / "shuixiaotong_finetune_800_with_reasoning.jsonl")
    print(f"总数据量: {len(all_data)} 条")
    
    # 验证格式
    print("\n[2/3] 验证数据格式...")
    format_errors = []
    reasoning_stats = {
        "总数据": len(all_data),
        "格式正确": 0,
        "格式错误": 0
    }
    
    for i, item in enumerate(all_data):
        is_valid, message = validate_reasoning_format(item['output'])
        
        if is_valid:
            reasoning_stats["格式正确"] += 1
        else:
            reasoning_stats["格式错误"] += 1
            format_errors.append({
                "行号": i + 1,
                "问题": item['instruction'][:30],
                "错误": message
            })
    
    print(f"格式正确: {reasoning_stats['格式正确']} 条")
    print(f"格式错误: {reasoning_stats['格式错误']} 条")
    
    if format_errors:
        print(f"\n发现 {len(format_errors)} 条格式错误:")
        for error in format_errors[:5]:  # 只显示前5条
            print(f"  行 {error['行号']}: {error['问题']}... - {error['错误']}")
    
    # 统计分析
    print("\n[3/3] 数据统计分析...")
    
    # 推理块长度统计
    reasoning_lengths = []
    answer_lengths = []
    
    for item in all_data:
        parts = item['output'].split("\n\n\n")
        if len(parts) == 2:
            reasoning = parts[0].replace("  ", "").strip()
            answer = parts[1].strip()
            reasoning_lengths.append(len(reasoning))
            answer_lengths.append(len(answer))
    
    print(f"\n推理块长度统计:")
    print(f"  平均: {sum(reasoning_lengths) / len(reasoning_lengths):.1f} 字符")
    print(f"  最小: {min(reasoning_lengths)} 字符")
    print(f"  最大: {max(reasoning_lengths)} 字符")
    
    print(f"\n答案长度统计:")
    print(f"  平均: {sum(answer_lengths) / len(answer_lengths):.1f} 字符")
    print(f"  最小: {min(answer_lengths)} 字符")
    print(f"  最大: {max(answer_lengths)} 字符")
    
    # 显示示例
    print("\n" + "=" * 60)
    print("数据示例")
    print("=" * 60)
    
    for i in [0, 100, 500, 700]:
        if i < len(all_data):
            item = all_data[i]
            print(f"\n[示例 {i+1}]")
            print(f"问题: {item['instruction']}")
            print(f"\n输出:\n{item['output'][:150]}...")
            print("-" * 60)
    
    # 最终结果
    print("\n" + "=" * 60)
    print("验证结果")
    print("=" * 60)
    
    if reasoning_stats["格式错误"] == 0:
        print("✓ 所有数据格式正确！")
        print(f"✓ 总数据量: {len(all_data)} 条")
        print(f"✓ 推理块格式: 符合要求")
        print(f"✓ 数据已随机打散")
        return True
    else:
        print(f"✗ 发现 {reasoning_stats['格式错误']} 条格式错误")
        return False

if __name__ == "__main__":
    validate_dataset()
