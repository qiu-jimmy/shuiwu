"""
税务自动计算服务
支持不同税种的自动计算
"""
from typing import Dict, Any, Optional
from decimal import Decimal


class TaxCalculator:
    """税务计算器"""

    # 个人所得税税率表（综合所得）
    PIT_RATES = [
        {"level": 1, "threshold": 0, "rate": Decimal("0.03"), "deduction": 0},
        {"level": 2, "threshold": 36000, "rate": Decimal("0.10"), "deduction": 2520},
        {"level": 3, "threshold": 144000, "rate": Decimal("0.20"), "deduction": 16920},
        {"level": 4, "threshold": 300000, "rate": Decimal("0.25"), "deduction": 31920},
        {"level": 5, "threshold": 420000, "rate": Decimal("0.30"), "deduction": 52920},
        {"level": 6, "threshold": 660000, "rate": Decimal("0.35"), "deduction": 85920},
        {"level": 7, "threshold": 960000, "rate": Decimal("0.45"), "deduction": 181920},
    ]

    # 增值税税率
    VAT_RATES = {
        "general": Decimal("0.13"),      # 一般纳税人 13%
        "small": Decimal("0.03"),         # 小规模纳税人 3%
        "construction": Decimal("0.09"),  # 建筑业 9%
        "transport": Decimal("0.09"),     # 交通运输 9%
        "service": Decimal("0.06"),       # 现代服务业 6%
    }

    @classmethod
    def calculate_pit(
        cls,
        income_info: Dict[str, Any],
        deduction_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        计算个人所得税（综合所得）

        Args:
            income_info: 收入信息，包含:
                - salary: 工资薪金
                - bonus: 奖金
                - labor_income: 劳务报酬
                - author_income: 稿酬
                - royalty_income: 特许权使用费
            deduction_info: 扣除信息，包含:
                - basic_deduction: 基本减除费用（60000/年）
                - special_deduction: 专项扣除（五险一金）
                - additional_deduction: 专项附加扣除
                    * children_education: 子女教育
                    * continuing_education: 继续教育
                    * housing_loan: 住房贷款利息
                    * housing_rent: 住房租金
                    * elderly_support: 赡养老人
                    * infant_care: 3岁以下婴幼儿照护

        Returns:
            计算结果，包含:
                - total_income: 收入总额
                - total_deduction: 扣除总额
                - taxable_income: 应纳税所得额
                - tax_amount: 应纳税额
        """
        # 1. 计算收入总额
        total_income = Decimal(0)

        # 工资薪金（全额计入）
        salary = Decimal(str(income_info.get("salary", 0)))
        total_income += salary

        # 奖金（目前与工资合并计算）
        bonus = Decimal(str(income_info.get("bonus", 0)))
        total_income += bonus

        # 劳务报酬（收入 × (1 - 20%)）
        labor_income = Decimal(str(income_info.get("labor_income", 0)))
        if labor_income > 0:
            total_income += labor_income * Decimal("0.8")

        # 稿酬（收入 × (1 - 20%) × 70%）
        author_income = Decimal(str(income_info.get("author_income", 0)))
        if author_income > 0:
            total_income += author_income * Decimal("0.8") * Decimal("0.7")

        # 特许权使用费（收入 × (1 - 20%)）
        royalty_income = Decimal(str(income_info.get("royalty_income", 0)))
        if royalty_income > 0:
            total_income += royalty_income * Decimal("0.8")

        # 2. 计算扣除总额
        total_deduction = Decimal(0)

        if deduction_info:
            # 基本减除费用（60000元/年 = 5000元/月）
            basic_deduction = Decimal(str(deduction_info.get("basic_deduction", 60000)))
            total_deduction += basic_deduction

            # 专项扣除（五险一金）
            special_deduction = Decimal(str(deduction_info.get("special_deduction", 0)))
            total_deduction += special_deduction

            # 专项附加扣除
            additional = deduction_info.get("additional_deduction", {})
            if isinstance(additional, dict):
                # 子女教育（1000元/月/孩）
                total_deduction += Decimal(str(additional.get("children_education", 0)))
                # 继续教育（400元/月）
                total_deduction += Decimal(str(additional.get("continuing_education", 0)))
                # 住房贷款利息（1000元/月）
                total_deduction += Decimal(str(additional.get("housing_loan", 0)))
                # 住房租金（1500元/月）
                total_deduction += Decimal(str(additional.get("housing_rent", 0)))
                # 赡养老人（2000元/月）
                total_deduction += Decimal(str(additional.get("elderly_support", 0)))
                # 婴幼儿照护（1000元/月/孩）
                total_deduction += Decimal(str(additional.get("infant_care", 0)))

        # 3. 计算应纳税所得额
        taxable_income = max(total_income - total_deduction, Decimal(0))

        # 4. 计算应纳税额（使用超额累进税率）
        tax_amount = cls._calculate_progressive_tax(taxable_income)

        return {
            "total_income": float(total_income.quantize(Decimal("0.01"))),
            "total_deduction": float(total_deduction.quantize(Decimal("0.01"))),
            "taxable_income": float(taxable_income.quantize(Decimal("0.01"))),
            "tax_amount": float(tax_amount.quantize(Decimal("0.01"))),
        }

    @classmethod
    def _calculate_progressive_tax(cls, taxable_income: Decimal) -> Decimal:
        """使用超额累进税率计算税额"""
        tax_amount = Decimal(0)

        for bracket in cls.PIT_RATES:
            if taxable_income > bracket["threshold"]:
                # 计算当前级数的应税所得
                if bracket["level"] < len(cls.PIT_RATES):
                    next_threshold = cls.PIT_RATES[bracket["level"]]["threshold"]
                    taxable_in_bracket = min(taxable_income, next_threshold) - bracket["threshold"]
                else:
                    taxable_in_bracket = taxable_income - bracket["threshold"]

                # 计算税额
                tax_amount += taxable_in_bracket * Decimal(str(bracket["rate"]))

        # 减去速算扣除数
        for bracket in reversed(cls.PIT_RATES):
            if taxable_income > bracket["threshold"]:
                tax_amount -= Decimal(str(bracket["deduction"]))
                break

        return max(tax_amount, Decimal(0))

    @classmethod
    def calculate_vat(
        cls,
        income_info: Dict[str, Any],
        deduction_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        计算增值税

        Args:
            income_info: 收入信息，包含:
                - sales_amount: 销售额
                - input_tax: 进项税额
                - taxpayer_type: 纳税人类型 (general/small)
                - industry: 行业类型
            deduction_info: 扣除信息（可选）

        Returns:
            计算结果
        """
        sales_amount = Decimal(str(income_info.get("sales_amount", 0)))
        input_tax = Decimal(str(income_info.get("input_tax", 0)))
        taxpayer_type = income_info.get("taxpayer_type", "general")
        industry = income_info.get("industry", "general")

        # 确定税率
        if taxpayer_type == "small":
            tax_rate = cls.VAT_RATES["small"]
            output_tax = sales_amount * tax_rate
            tax_amount = output_tax  # 小规模纳税人不可抵扣进项
        else:
            tax_rate = cls.VAT_RATES.get(industry, cls.VAT_RATES["general"])
            output_tax = sales_amount * tax_rate
            tax_amount = max(output_tax - input_tax, Decimal(0))  # 一般纳税人可抵扣

        return {
            "total_income": float(sales_amount.quantize(Decimal("0.01"))),
            "total_deduction": float(input_tax.quantize(Decimal("0.01"))),
            "taxable_income": float(sales_amount.quantize(Decimal("0.01"))),
            "tax_amount": float(tax_amount.quantize(Decimal("0.01"))),
        }

    @classmethod
    def calculate_cit(
        cls,
        income_info: Dict[str, Any],
        deduction_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        计算企业所得税

        Args:
            income_info: 收入信息，包含:
                - total_revenue: 营业收入
                - other_income: 营业外收入
            deduction_info: 扣除信息，包含:
                - cost: 成本
                - expenses: 费用
                - losses: 损失
                - tax_incentive: 税收优惠减免额

        Returns:
            计算结果
        """
        total_revenue = Decimal(str(income_info.get("total_revenue", 0)))
        other_income = Decimal(str(income_info.get("other_income", 0)))
        total_income = total_revenue + other_income

        total_deduction = Decimal(0)
        if deduction_info:
            total_deduction += Decimal(str(deduction_info.get("cost", 0)))
            total_deduction += Decimal(str(deduction_info.get("expenses", 0)))
            total_deduction += Decimal(str(deduction_info.get("losses", 0)))
            # 税收优惠减免
            total_deduction += Decimal(str(deduction_info.get("tax_incentive", 0)))

        taxable_income = max(total_income - total_deduction, Decimal(0))

        # 企业所得税标准税率 25%
        CIT_RATE = Decimal("0.25")
        tax_amount = taxable_income * CIT_RATE

        return {
            "total_income": float(total_income.quantize(Decimal("0.01"))),
            "total_deduction": float(total_deduction.quantize(Decimal("0.01"))),
            "taxable_income": float(taxable_income.quantize(Decimal("0.01"))),
            "tax_amount": float(tax_amount.quantize(Decimal("0.01"))),
        }

    @classmethod
    def calculate(
        cls,
        tax_type: str,
        income_info: Dict[str, Any],
        deduction_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        根据税种自动计算

        Args:
            tax_type: 税种 (pit/vat/cit)
            income_info: 收入信息
            deduction_info: 扣除信息

        Returns:
            计算结果
        """
        tax_type = tax_type.lower()

        if tax_type == "pit":
            return cls.calculate_pit(income_info, deduction_info)
        elif tax_type == "vat":
            return cls.calculate_vat(income_info, deduction_info)
        elif tax_type == "cit":
            return cls.calculate_cit(income_info, deduction_info)
        else:
            raise ValueError(f"不支持的税种: {tax_type}")


# 全局计算器实例
tax_calculator = TaxCalculator()
