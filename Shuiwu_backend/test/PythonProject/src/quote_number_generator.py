"""
报价单号生成器
规则：DragonAI-年份+月份+单子大小+序号（每个月从6号开始编号）
单子大小：小于10万标记为S，10-30万标记为M，大于30万标记为L
"""
from datetime import datetime
from pathlib import Path
import json


class QuoteNumberGenerator:
    """报价单号生成器"""
    
    def __init__(self, data_file: str = None):
        """初始化生成器"""
        if data_file is None:
            # 默认使用脚本所在目录下的 quote_numbers.json
            import os
            script_dir = Path(__file__).parent
            data_file = str(script_dir / "quote_numbers.json")
        self.data_file = Path(data_file)
        self._load_data()
    
    def _load_data(self):
        """加载历史数据"""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            except:
                self.data = {}
        else:
            self.data = {}
    
    def _save_data(self):
        """保存数据"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def generate(self, amount: float) -> str:
        """生成报价单号
        
        Args:
            amount: 报价金额（元）
        
        Returns:
            报价单号，格式：DragonAI-YYYYMM-{S/M/L}-{序号}
        """
        now = datetime.now()
        year = now.year
        month = now.month
        
        # 确定单子大小
        if amount < 100000:
            size = "S"
        elif amount < 300000:
            size = "M"
        else:
            size = "L"
        
        # 获取当前月的序号（从6号开始）
        key = f"{year}{month:02d}-{size}"
        if key not in self.data:
            # 初始值设为5，下一个就是6（从6号开始编号）
            self.data[key] = 5
        else:
            # 如果已存在，检查当前值是否小于5，如果是则重置为5
            if self.data[key] < 5:
                self.data[key] = 5
        
        self.data[key] += 1
        sequence = self.data[key]
        
        self._save_data()
        
        # 生成报价单号
        quote_number = f"DragonAI-{year}{month:02d}-{size}-{sequence:03d}"
        return quote_number

