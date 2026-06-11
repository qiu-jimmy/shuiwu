"""
H5 页面路由
用于微信小程序内嵌 WebView 的回调页面
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/h5", tags=["H5页面"])


def _build_callback_html(order_no: str, mini_program_path: str) -> str:
    """构建授权回调 HTML 页面"""
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>授权完成</title>
    <style>
        body {{
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            color: #333;
        }}
        .loading {{ text-align: center; }}
    </style>
</head>
<body>
    <div class="loading">授权完成，正在返回小程序...</div>
    <script src="https://res.wx.qq.com/open/js/jweixin-1.6.0.js"></script>
    <script>
        var orderNo = "{order_no}";
        var url = '{mini_program_path}';
        if (orderNo) {{
            url += '?orderNo=' + orderNo;
        }}
        wx.miniProgram.navigateTo({{ url: url }});
    </script>
</body>
</html>"""


@router.get("/invoice-callback", response_class=HTMLResponse)
async def invoice_callback(request: Request):
    """发票穿透授权完成回调页面"""
    order_no = request.query_params.get("orderNo", "")
    return _build_callback_html(
        order_no,
        "/subpackage/pages/agent/invoicePenetration/invoicePenetration",
    )


@router.get("/business-callback", response_class=HTMLResponse)
async def business_callback(request: Request):
    """经营风险报告授权完成回调页面"""
    order_no = request.query_params.get("orderNo", "")
    return _build_callback_html(
        order_no,
        "/subpackage/pages/agent/businessRisk/businessRisk",
    )
