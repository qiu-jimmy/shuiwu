"""
JWT认证中间件
用于拦截所有请求，验证JWT token（除了登录、注册等公开接口）
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from app.utils.jwt_utils import verify_token
from app.utils.response import response as resp_util


# 不需要认证的路径列表
PUBLIC_PATHS = [
    "/health",
    "/api/test",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/reset-password",
    "/api/auth/send-sms-code",
    "/api/admin/login",  # 管理员登录（公开）
    "/api/knowledge-types/list",
    "/api/member/packages",  # 会员套餐列表（公开）
    "/api/member/benefits",  # 会员权益列表（公开）
    "/api/distribution/validate-code",  # 验证推广码（公开）
    "/api/config/distribution",  # 获取分销配置（公开）
    # 税务知识文档查询接口（公开）
    "/api/tax-knowledge/list",
    "/api/tax-knowledge/detail/*",
    "/api/tax-knowledge/frontend/list",
    "/api/tax-knowledge/frontend/detail/*",
    # 发票穿透回调接口（由查税宝服务调用，不需要认证）
    "/api/invoice-penetration/notify/callback",
    # 全景报告回调接口（由查税宝服务调用，不需要认证）
    "/api/chashuibao/panoramic/notify",
    # 经营风险报告回调接口（由查税宝服务调用，不需要认证）
    "/api/chashuibao/notify/callback",
    # 微信登录
    "/api/auth/wechat-login",
    "/api/payments/notify",
    # 税务师列表接口（公开）
    "/api/tax_accountant/list",
    # 回调页面
    "/h5/invoice-callback",
    "/h5/business-callback",
]


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """JWT认证中间件"""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        path = request.url.path

        # 检查是否为公开路径
        if self._is_public_path(path):
            return await call_next(request)

        # 获取Authorization头
        authorization = request.headers.get("Authorization")

        if not authorization:
            return JSONResponse(
                status_code=401,
                content=resp_util.fail(
                    message="未提供认证token",
                    code="NO_TOKEN"
                )
            )

        # 检查Authorization格式
        if not authorization.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content=resp_util.fail(
                    message="认证token格式错误，应为: Bearer <token>",
                    code="INVALID_TOKEN_FORMAT"
                )
            )

        # 提取token
        token = authorization.split(" ")[1]

        # 验证token
        user_id = verify_token(token)

        if user_id is None:
            return JSONResponse(
                status_code=401,
                content=resp_util.fail(
                    message="无效的认证token",
                    code="INVALID_TOKEN"
                )
            )

        # 将user_id添加到request state中，供后续使用
        request.state.user_id = user_id

        # 查询用户基本信息（包括角色），供权限装饰器使用
        try:
            from app.services.user.user_repository import user_repository
            user = user_repository.get_user_by_id(user_id)
            if user:
                # 添加用户类型（普通用户/管理员）
                request.state.user_type = user.get("user_type", "user")
                # 添加角色信息（用于角色权限系统）
                request.state.role = user.get("role", user.get("user_type", "user"))
        except Exception:
            # 如果查询失败，设置默认值
            request.state.user_type = "user"
            request.state.role = "user"

        # 继续处理请求
        response = await call_next(request)
        return response

    def _is_public_path(self, path: str) -> bool:
        """检查是否为公开路径"""
        # 微信校验文件
        if path == "/xYHtK75aHH.txt":
            return True

        # 完全匹配
        if path in PUBLIC_PATHS:
            return True

        # 前缀匹配（用于匹配路径参数，如 /api/auth/some-dynamic-path）
        for public_path in PUBLIC_PATHS:
            if public_path.endswith("*"):
                # 通配符匹配
                prefix = public_path[:-1]
                if path.startswith(prefix):
                    return True

        # 特殊处理：税务师详情接口（/api/tax_accountant/{accountant_id}）为公开接口
        # 但需要排除需要认证的接口：/apply, /my-application, /my-info
        if path.startswith("/api/tax_accountant/"):
            # 排除需要认证的接口
            auth_required_paths = [
                "/api/tax_accountant/apply",
                "/api/tax_accountant/my-application",
                "/api/tax_accountant/my-info",
            ]
            if path not in auth_required_paths:
                # 其他路径（如详情接口）为公开接口
                return True

        return False
