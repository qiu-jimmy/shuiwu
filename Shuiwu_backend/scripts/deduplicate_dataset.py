"""
数据集去重脚本
对 identity_data.jsonl 和 general_data.jsonl 进行去重处理
"""
import json
from pathlib import Path
from collections import Counter

DATA_DIR = Path(r"D:\zhulong_code\Shuiwu\Shuiwu_backend\Shuiwu_backend\Shuiwu_backend\docs\数据集")


def load_jsonl(filepath):
    """加载JSONL文件"""
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            data.append(json.loads(line.strip()))
    return data


def save_jsonl(data, filepath):
    """保存JSONL文件"""
    with open(filepath, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')


def deduplicate_dataset(data, dataset_name):
    """去重数据集"""
    print(f"\n{'=' * 60}")
    print(f"处理数据集: {dataset_name}")
    print(f"{'=' * 60}")
    
    # 原始数据量
    original_count = len(data)
    print(f"原始数据量: {original_count} 条")
    
    # 检测重复数据（基于instruction字段）
    instructions = [item['instruction'] for item in data]
    instruction_counts = Counter(instructions)
    duplicates = {k: v for k, v in instruction_counts.items() if v > 1}
    
    if duplicates:
        print(f"\n发现重复的instruction: {len(duplicates)} 个")
        for inst, count in list(duplicates.items())[:5]:  # 只显示前5个
            print(f"  - '{inst}': 出现 {count} 次")
        if len(duplicates) > 5:
            print(f"  ... 还有 {len(duplicates) - 5} 个重复项")
    
    # 去重（保留第一次出现的数据）
    seen_instructions = set()
    deduplicated_data = []
    duplicate_items = []
    
    for item in data:
        instruction = item['instruction']
        if instruction not in seen_instructions:
            seen_instructions.add(instruction)
            deduplicated_data.append(item)
        else:
            duplicate_items.append(item)
    
    # 去重后的数据量
    deduplicated_count = len(deduplicated_data)
    removed_count = original_count - deduplicated_count
    
    print(f"\n去重后数据量: {deduplicated_count} 条")
    print(f"移除重复数据: {removed_count} 条")
    print(f"去重率: {removed_count / original_count * 100:.2f}%")
    
    return deduplicated_data, duplicate_items


def check_cross_dataset_duplicates(identity_data, general_data):
    """检查跨数据集的重复"""
    print(f"\n{'=' * 60}")
    print("检查跨数据集重复")
    print(f"{'=' * 60}")
    
    identity_instructions = {item['instruction'] for item in identity_data}
    general_instructions = {item['instruction'] for item in general_data}
    
    cross_duplicates = identity_instructions & general_instructions
    
    if cross_duplicates:
        print(f"发现跨数据集重复: {len(cross_duplicates)} 个")
        for inst in list(cross_duplicates)[:5]:
            print(f"  - '{inst}'")
        if len(cross_duplicates) > 5:
            print(f"  ... 还有 {len(cross_duplicates) - 5} 个")
    else:
        print("未发现跨数据集重复")
    
    return cross_duplicates


def main():
    """主函数"""
    print("=" * 60)
    print("税小通数据集去重工具")
    print("=" * 60)
    
    # 加载数据集
    print("\n[1/4] 加载数据集...")
    identity_file = DATA_DIR / "identity_data.jsonl"
    general_file = DATA_DIR / "general_data.jsonl"
    
    identity_data = load_jsonl(identity_file)
    general_data = load_jsonl(general_file)
    
    print(f"身份数据集: {len(identity_data)} 条")
    print(f"通用数据集: {len(general_data)} 条")
    
    # 检查跨数据集重复
    print("\n[2/4] 检查跨数据集重复...")
    cross_duplicates = check_cross_dataset_duplicates(identity_data, general_data)
    
    # 去重身份数据集
    print("\n[3/4] 去重身份数据集...")
    deduplicated_identity, identity_duplicates = deduplicate_dataset(identity_data, "身份数据集")
    
    # 去重通用数据集
    print("\n[4/4] 去重通用数据集...")
    deduplicated_general, general_duplicates = deduplicate_dataset(general_data, "通用数据集")
    
    # 保存去重后的数据
    print(f"\n{'=' * 60}")
    print("保存去重后的数据集")
    print(f"{'=' * 60}")
    
    # 备份原始文件
    import shutil
    backup_dir = DATA_DIR / "backup"
    backup_dir.mkdir(exist_ok=True)
    
    shutil.copy(identity_file, backup_dir / "identity_data_backup.jsonl")
    shutil.copy(general_file, backup_dir / "general_data_backup.jsonl")
    print(f"原始文件已备份到: {backup_dir}")
    
    # 保存去重后的文件
    save_jsonl(deduplicated_identity, identity_file)
    save_jsonl(deduplicated_general, general_file)
    print(f"去重后的身份数据集已保存: {identity_file}")
    print(f"去重后的通用数据集已保存: {general_file}")
    
    # 保存重复数据记录
    if identity_duplicates or general_duplicates:
        duplicates_file = DATA_DIR / "removed_duplicates.jsonl"
        all_duplicates = identity_duplicates + general_duplicates
        save_jsonl(all_duplicates, duplicates_file)
        print(f"移除的重复数据已保存: {duplicates_file}")
    
    # 重新生成合并数据集
    print(f"\n{'=' * 60}")
    print("重新生成合并数据集")
    print(f"{'=' * 60}")
    
    all_data = deduplicated_identity + deduplicated_general
    merged_file = DATA_DIR / "shuixiaotong_finetune_800.jsonl"
    save_jsonl(all_data, merged_file)
    
    print(f"合并数据集已更新: {merged_file}")
    print(f"总数据量: {len(all_data)} 条")
    
    # 生成去重报告
    print(f"\n{'=' * 60}")
    print("去重报告")
    print(f"{'=' * 60}")
    
    report = {
        "原始数据": {
            "身份数据集": len(identity_data),
            "通用数据集": len(general_data),
            "总计": len(identity_data) + len(general_data)
        },
        "去重后数据": {
            "身份数据集": len(deduplicated_identity),
            "通用数据集": len(deduplicated_general),
            "总计": len(all_data)
        },
        "移除的重复数据": {
            "身份数据集": len(identity_duplicates),
            "通用数据集": len(general_duplicates),
            "总计": len(identity_duplicates) + len(general_duplicates)
        },
        "跨数据集重复": len(cross_duplicates)
    }
    
    report_file = DATA_DIR / "deduplication_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"去重报告已保存: {report_file}")
    
    # 打印报告
    print(f"\n原始数据总量: {report['原始数据']['总计']} 条")
    print(f"去重后数据总量: {report['去重后数据']['总计']} 条")
    print(f"移除重复数据: {report['移除的重复数据']['总计']} 条")
    print(f"跨数据集重复: {report['跨数据集重复']} 个")
    
    print(f"\n{'=' * 60}")
    print("去重完成！")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
