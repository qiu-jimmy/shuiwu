"""
时间查询工具

提供当前时间、日期等信息，帮助 Agent 准确理解用户问题中的时间上下文。
"""
import logging
from datetime import datetime
from typing import Dict

from agno.tools import tool

logger = logging.getLogger(__name__)


@tool
def get_current_time() -> str:
    """
    获取当前时间和日期

    当用户问题中提到时间相关内容时使用此工具，例如：
    - "3月份的政策"
    - "今年的税率"
    - "最近的规定"

    使用此工具可以确保 Agent 知道准确的当前时间，避免误解。

    Returns:
        str: 格式化的当前时间信息
    """
    try:
        now = datetime.now()

        # 获取各种时间格式
        time_info = {
            "current_date": now.strftime("%Y年%m月%d日"),
            "current_time": now.strftime("%H:%M:%S"),
            "year": now.year,
            "month": now.month,
            "day": now.day,
            "weekday": now.weekday(),
            "weekday_name": ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][now.weekday()],
            "quarter": (now.month - 1) // 3 + 1,
            "is_leap_year": now.year % 4 == 0 and (now.year % 100 != 0 or now.year % 400 == 0),
        }

        # 格式化输出
        result = f"""当前时间信息：
- 完整日期：{time_info['current_date']} {time_info['current_time']}
- 年份：{time_info['year']}年
- 月份：{time_info['month']}月
- 日期：{time_info['day']}日
- 星期：{time_info['weekday_name']}
- 季度：第{time_info['quarter']}季度
- 闰年：{'是' if time_info['is_leap_year'] else '不是'}闰年

使用说明：
当用户提到"3月份"、"今年"、"最近"等时间词时，应该参考上述当前时间进行判断。
例如：如果现在是{time_info['year']}年{time_info['month']}月，用户问"3月份"，应该理解为{time_info['year']}年3月份。"""

        logger.info(f"获取当前时间: {time_info['current_date']} {time_info['current_time']}")

        return result

    except Exception as e:
        logger.error(f"获取当前时间失败: {e}", exc_info=True)
        return f"获取时间失败: {str(e)}"


@tool
def parse_time_expression(expression: str) -> str:
    """
    解析时间表达式

    解析用户输入的时间表达式，返回具体的日期范围。

    支持的表达式：
    - "今年"、"本年"
    - "去年"、"上年"
    - "明年"
    - "本季度"
    - "上季度"
    - "下季度"
    - "本月"
    - "上月"
    - "下月"
    - "3月份" (表示当年的3月份)
    - "最近3个月"
    - "过去半年"

    Args:
        expression: 时间表达式，如"今年"、"3月份"等

    Returns:
        str: 解析后的时间范围
    """
    try:
        now = datetime.now()
        year = now.year
        month = now.month
        day = now.day

        expr = expression.strip().lower()

        result = {
            "expression": expression,
            "current_date": now.strftime("%Y年%m月%d日"),
            "interpreted_range": None,
            "note": ""
        }

        # 解析年份相关
        if "今年" in expr or "本年" in expr:
            result["interpreted_range"] = f"{year}年1月1日 - {year}年12月31日"
            result["note"] = f"今年指{year}年"

        elif "去年" in expr or "上年" in expr:
            result["interpreted_range"] = f"{year-1}年1月1日 - {year-1}年12月31日"
            result["note"] = f"去年指{year-1}年"

        elif "明年" in expr:
            result["interpreted_range"] = f"{year+1}年1月1日 - {year+1}年12月31日"
            result["note"] = f"明年指{year+1}年"

        # 解析月份相关（匹配"1月"、"2月"等）
        elif any(f"{i}月" in expr for i in range(1, 13)):
            for i in range(1, 13):
                if f"{i}月" in expr:
                    result["interpreted_range"] = f"{year}年{i}月1日 - {year}年{i}月最后一天"
                    result["note"] = f"理解为{year}年{i}月份"
                    break

        # 解析季度相关
        elif "本季度" in expr or "这个季度" in expr:
            q = (month - 1) // 3 + 1
            start_month = (q - 1) * 3 + 1
            end_month = q * 3
            result["interpreted_range"] = f"{year}年{start_month}月 - {year}年{end_month}月"
            result["note"] = f"本季度指第{q}季度"

        elif "上季度" in expr:
            q = (month - 1) // 3
            if q == 0:
                q = 4
                year -= 1
            start_month = (q - 1) * 3 + 1
            end_month = q * 3
            result["interpreted_range"] = f"{year}年{start_month}月 - {year}年{end_month}月"
            result["note"] = f"上季度指{year}年第{q}季度"

        elif "下季度" in expr:
            q = (month - 1) // 3 + 2
            if q > 4:
                q = 1
                year += 1
            start_month = (q - 1) * 3 + 1
            end_month = q * 3
            result["interpreted_range"] = f"{year}年{start_month}月 - {year}年{end_month}月"
            result["note"] = f"下季度指{year}年第{q}季度"

        # 解析"本月"
        elif "本月" in expr:
            result["interpreted_range"] = f"{year}年{month}月1日 - {year}年{month}月最后一天"
            result["note"] = f"本月指{year}年{month}月"

        # 解析"上月"
        elif "上月" in expr or "上个月" in expr:
            if month == 1:
                last_month = 12
                last_year = year - 1
            else:
                last_month = month - 1
                last_year = year
            result["interpreted_range"] = f"{last_year}年{last_month}月"
            result["note"] = f"上月指{last_year}年{last_month}月"

        # 解析"下月"
        elif "下月" in expr or "下个月" in expr:
            if month == 12:
                next_month = 1
                next_year = year + 1
            else:
                next_month = month + 1
                next_year = year
            result["interpreted_range"] = f"{next_year}年{next_month}月"
            result["note"] = f"下月指{next_year}年{next_month}月"

        # 解析"最近X个月"
        elif "最近" in expr or "过去" in expr or "前" in expr:
            import re
            match = re.search(r'最近(\d+)|过去(\d+)|前(\d+)', expr)
            if match:
                months = int(match.group(1) or match.group(2) or match.group(3))
                # 计算X个月前的日期
                from datetime import timedelta
                past_date = now - timedelta(days=months * 30)
                result["interpreted_range"] = f"{past_date.strftime('%Y年%m月%d日')} - {now.strftime('%Y年%m月%d日')}"
                result["note"] = f"最近{months}个月指从{months}个月前至今"

        else:
            result["note"] = f"无法识别表达式: {expression}，请提供更明确的时间描述"
            result["interpreted_range"] = "未知"

        # 格式化输出
        output = f"""时间表达式解析：
- 原始表达式：{result['expression']}
- 当前日期：{result['current_date']}
- 解析结果：{result['interpreted_range']}
- 说明：{result['note']}

建议：根据上述解析结果理解用户的时间范围。"""

        logger.info(f"解析时间表达式: {expression} -> {result['interpreted_range']}")

        return output

    except Exception as e:
        logger.error(f"解析时间表达式失败: {e}, expression: {expression}", exc_info=True)
        return f"解析时间表达式失败: {str(e)}"


def create_time_tools() -> list:
    """
    创建时间工具集

    Returns:
        list: 时间工具列表
    """
    return [
        get_current_time,
        parse_time_expression,
    ]
