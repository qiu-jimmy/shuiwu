"""
补充数据集到800条
"""
import json
from pathlib import Path

OUTPUT_DIR = Path(r"D:\zhulong_code\Shuiwu\Shuiwu_backend\Shuiwu_backend\Shuiwu_backend\docs\数据集")

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

def supplement_dataset():
    """补充数据集到800条"""
    # 加载现有数据
    identity_data = load_jsonl(OUTPUT_DIR / "identity_data.jsonl")
    general_data = load_jsonl(OUTPUT_DIR / "general_data.jsonl")
    all_data = identity_data + general_data
    
    print(f"现有数据: {len(all_data)}条")
    
    # 检查需要补充的数量
    need_count = 800 - len(all_data)
    print(f"需要补充: {need_count}条")
    
    if need_count <= 0:
        print("数据已足够，无需补充")
        return
    
    # 补充数据
    additional_data = [
        {"instruction": "什么是税收法定原则？", "input": "", "output": "税收法定原则是指税收的征收必须依据法律的规定进行，包括税种、税目、税率、纳税人、征税对象等要素都必须由法律明确规定。这是现代税法的基本原则。"},
        {"instruction": "如何理解实质重于形式原则？", "input": "", "output": "实质重于形式原则要求税务机关在征税时，不应仅根据交易的法律形式，而应根据交易的经济实质来确定纳税义务。这是反避税的重要原则。"},
        {"instruction": "什么是税收中性原则？", "input": "", "output": "税收中性原则是指税收不应干扰市场经济的正常运行，不应影响纳税人的经济决策。税收应当保持中性，避免对资源配置产生扭曲作用。"},
        {"instruction": "如何理解税收公平原则？", "input": "", "output": "税收公平原则包括横向公平和纵向公平。横向公平是指经济能力相同的人应缴纳相同的税收；纵向公平是指经济能力不同的人应缴纳不同的税收。"},
        {"instruction": "什么是税收效率原则？", "input": "", "output": "税收效率原则包括行政效率和经济效率。行政效率要求税收征管成本最小化；经济效率要求税收对经济活动的扭曲最小化，减少超额负担。"},
        {"instruction": "如何理解纳税信用等级？", "input": "", "output": "纳税信用等级分为A、B、C、D、M五级。A级为信用优秀，可享受绿色通道等便利；D级为信用较差，会被重点监控。M级为新设立企业。"},
        {"instruction": "什么是税收协定？", "input": "", "output": "税收协定是两个或多个主权国家之间签订的避免双重征税和防止偷漏税的协议。主要作用是划分征税权、降低税率、消除双重征税。"},
        {"instruction": "如何理解常设机构？", "input": "", "output": "常设机构是企业进行全部或部分营业的固定场所。在税收协定中，常设机构是判断非居民企业是否在某国构成纳税义务的重要标准。"},
        {"instruction": "什么是预提所得税？", "input": "", "output": "预提所得税是对非居民企业来源于境内的所得，由支付人在支付款项时扣缴的所得税。一般适用于股息、利息、特许权使用费等被动收入。"},
    ]
    
    # 添加补充数据
    all_data.extend(additional_data[:need_count])
    
    print(f"补充后数据: {len(all_data)}条")
    
    # 保存数据
    save_jsonl(all_data, OUTPUT_DIR / "shuixiaotong_finetune_800.jsonl")
    
    # 更新身份数据和通用数据
    identity_new = all_data[:400]
    general_new = all_data[400:]
    
    save_jsonl(identity_new, OUTPUT_DIR / "identity_data.jsonl")
    save_jsonl(general_new, OUTPUT_DIR / "general_data.jsonl")
    
    print(f"身份数据: {len(identity_new)}条")
    print(f"通用数据: {len(general_new)}条")
    print(f"合并数据: {len(all_data)}条")
    print("补充完成！")

if __name__ == "__main__":
    supplement_dataset()
