from datetime import datetime

from tax_agent.tools.decorators import compatible_tool


def make_time_tool():
    @compatible_tool
    def get_current_time() -> str:
        """Get current date and time in Asia/Shanghai for tax policy time-sensitive answers."""
        now = datetime.now()
        quarter = (now.month - 1) // 3 + 1
        return f"当前日期：{now:%Y-%m-%d}；当前时间：{now:%H:%M}；当前季度：第{quarter}季度"

    return get_current_time
