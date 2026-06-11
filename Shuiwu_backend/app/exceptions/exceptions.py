"""
自定义异常类
定义所有业务异常类型
"""
from typing import Optional, Any


class BaseAPIException(Exception):
    """API异常基类"""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        detail: Optional[Any] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.message)


# ==================== 认证相关异常 ====================

class AuthenticationException(BaseAPIException):
    """认证异常基类"""

    def __init__(self, message: str, code: str = "AUTH_FAILED", detail: Optional[Any] = None):
        super().__init__(message, code, 401, detail)


class TokenMissingException(AuthenticationException):
    """Token缺失"""

    def __init__(self, detail: Optional[Any] = None):
        super().__init__("未提供认证token", "NO_TOKEN", detail)


class TokenInvalidException(AuthenticationException):
    """Token无效"""

    def __init__(self, detail: Optional[Any] = None):
        super().__init__("无效的认证token", "INVALID_TOKEN", detail)


class TokenExpiredException(AuthenticationException):
    """Token过期"""

    def __init__(self, detail: Optional[Any] = None):
        super().__init__("认证token已过期", "TOKEN_EXPIRED", detail)


class PasswordIncorrectException(AuthenticationException):
    """密码错误"""

    def __init__(self, detail: Optional[Any] = None):
        super().__init__("密码错误", "INVALID_PASSWORD", detail)


# ==================== 授权相关异常 ====================

class AuthorizationException(BaseAPIException):
    """授权异常基类"""

    def __init__(self, message: str, code: str = "FORBIDDEN", detail: Optional[Any] = None):
        super().__init__(message, code, 403, detail)


class UserDisabledException(AuthorizationException):
    """用户被禁用"""

    def __init__(self, detail: Optional[Any] = None):
        super().__init__("用户已被禁用", "USER_DISABLED", detail)


class UserBannedException(AuthorizationException):
    """用户被封禁"""

    def __init__(self, detail: Optional[Any] = None):
        super().__init__("用户已被封禁", "USER_BANNED", detail)


class PermissionDeniedException(AuthorizationException):
    """权限不足"""

    def __init__(self, message: str = "权限不足", detail: Optional[Any] = None):
        super().__init__(message, "PERMISSION_DENIED", detail)


class ResourceOwnerException(AuthorizationException):
    """资源所有权异常"""

    def __init__(self, message: str = "无权访问此资源", detail: Optional[Any] = None):
        super().__init__(message, "NOT_RESOURCE_OWNER", detail)


# ==================== 资源相关异常 ====================

class NotFoundException(BaseAPIException):
    """资源不存在"""

    def __init__(self, message: str = "资源不存在", code: str = "NOT_FOUND", detail: Optional[Any] = None):
        super().__init__(message, code, 404, detail)


class UserNotFoundException(NotFoundException):
    """用户不存在"""

    def __init__(self, detail: Optional[Any] = None):
        super().__init__("用户不存在", "USER_NOT_FOUND", detail)


class SessionNotFoundException(NotFoundException):
    """会话不存在"""

    def __init__(self, detail: Optional[Any] = None):
        super().__init__("会话不存在", "SESSION_NOT_FOUND", detail)


class KnowledgeBaseNotFoundException(NotFoundException):
    """知识库不存在"""

    def __init__(self, detail: Optional[Any] = None):
        super().__init__("知识库不存在", "KNOWLEDGE_BASE_NOT_FOUND", detail)


# ==================== 业务逻辑异常 ====================

class BusinessException(BaseAPIException):
    """业务逻辑异常基类"""

    def __init__(
        self,
        message: str,
        code: str = "BUSINESS_ERROR",
        status_code: int = 400,
        detail: Optional[Any] = None
    ):
        super().__init__(message, code, status_code, detail)


class ValidationException(BusinessException):
    """参数验证失败"""

    def __init__(self, message: str = "参数验证失败", detail: Optional[Any] = None):
        super().__init__(message, "VALIDATION_ERROR", 400, detail)


class ConflictException(BusinessException):
    """资源冲突"""

    def __init__(self, message: str = "资源冲突", code: str = "CONFLICT", detail: Optional[Any] = None):
        super().__init__(message, code, 409, detail)


class PhoneExistsException(ConflictException):
    """手机号已存在"""

    def __init__(self, detail: Optional[Any] = None):
        super().__init__("手机号已被注册", "PHONE_EXISTS", detail)


class SmsCodeException(BusinessException):
    """短信验证码错误"""

    def __init__(self, message: str = "验证码错误或已过期", detail: Optional[Any] = None):
        super().__init__(message, "SMS_CODE_ERROR", 400, detail)


# ==================== 外部服务异常 ====================

class ExternalServiceException(BaseAPIException):
    """外部服务异常"""

    def __init__(
        self,
        message: str,
        service: str = "external_service",
        code: str = "EXTERNAL_SERVICE_ERROR",
        detail: Optional[Any] = None
    ):
        self.service = service
        super().__init__(message, code, 502, detail)


class DatabaseException(BaseAPIException):
    """数据库异常"""

    def __init__(self, message: str = "数据库操作失败", detail: Optional[Any] = None):
        super().__init__(message, "DATABASE_ERROR", 500, detail)


class AIServiceException(ExternalServiceException):
    """AI服务异常"""

    def __init__(self, message: str = "AI服务调用失败", detail: Optional[Any] = None):
        super().__init__(message, "ai_service", "AI_SERVICE_ERROR", detail)


class McpServiceException(ExternalServiceException):
    """MCP服务异常"""

    def __init__(self, message: str = "MCP服务调用失败", detail: Optional[Any] = None):
        super().__init__(message, "mcp_service", "MCP_SERVICE_ERROR", detail)
