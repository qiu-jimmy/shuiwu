"""
分销推广模块 - API路由
处理分销商注册、推广码管理、佣金结算等分销推广相关接口

**功能说明：**
- 用户可申请成为分销商，获取专属推广码
- 新用户通过推广码注册时自动绑定推荐关系
- 新用户完成订单后，系统自动计算并记录分销佣金
- 分销商可查看佣金统计、分销记录、申请提现
- 管理员可审核提现申请、管理分销商
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, Body
from pydantic import BaseModel

from app.schemas.distribution import (
    DistributorStatsResponse,
    DistributionRecordListResponse,
    WithdrawalRequestCreate,
    WithdrawalRequestListResponse,
    DistributorCodeResponse
)
from app.schemas.auth import BindInviteCodeRequest
from app.schemas.common import ApiResponse
from app.services.distribution.distribution_service import distribution_service
from app.services.auth.auth_service import auth_service
from app.services.config.config_service import config_service
from app.utils.dependencies import get_current_user_info
from app.utils.response import response

router = APIRouter(prefix="/api/distribution", tags=["分销推广"])


# ============================================================================
# 分销商管理
# ============================================================================


class BecomeDistributorRequest(BaseModel):
    """成为分销商请求"""
    # 目前无需参数，使用认证用户信息


@router.post(
    "/become-distributor",
    summary="成为分销商",
    description="""
    申请成为分销商，获取专属推广码。

    **业务规则：**
    - 每个用户只能申请一次成为分销商
    - 成功后将自动生成6位推广码（大写字母+数字组合）
    - 推广码可用于邀请新用户注册
    - 新用户通过推广码注册后将自动绑定推荐关系

    **使用场景：**
    - 用户点击"成为分销商"按钮
    - 前端调用此接口为用户创建分销商账户
    - 成功后展示推广码和分享链接

    **后续流程：**
    1. 调用 GET /api/distribution/my-code 获取推广码
    2. 生成推广二维码（前端使用 qrcode.js）
    3. 分享推广链接或二维码给新用户
    """,
    responses={
        200: {
            "description": "申请成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "成为分销商成功",
                        "data": {
                            "user_id": "user_1234567890",
                            "distributor_code": "ABC123",
                            "status": "active",
                            "total_commission": 0,
                            "available_commission": 0
                        }
                    }
                }
            }
        },
        400: {
            "description": "申请失败",
            "content": {
                "application/json": {
                    "examples": {
                        "already_distributor": {
                            "summary": "已是分销商",
                            "value": {
                                "code": 0,
                                "message": "您已经是分销商",
                                "data": None
                            }
                        }
                    }
                }
            }
        }
    }
)
async def become_distributor(
    current_user: dict = Depends(get_current_user_info)
) -> Dict[str, Any]:
    """
    成为分销商

    Args:
        current_user: 当前认证用户信息

    Returns:
        包含分销商信息的响应
    """
    result = distribution_service.become_distributor(current_user["user_id"])
    if result.get("success"):
        return response.success(data=result.get("distributor"), message="成为分销商成功")
    return response.fail(message=result.get("error", "成为分销商失败"))


@router.get(
    "/my-code",
    summary="获取我的推广码",
    description="""
    获取当前用户的推广码、分享链接和邀请人信息。

    **返回内容：**
    - distributor_code: 6位推广码（如 ABC123）
    - share_link: 完整分享链接
    - share_text: 推荐文案
    - inviter: 邀请人信息（如果有绑定）

    **前端使用：**
    1. 调用此接口获取推广信息
    2. 使用 distributor_code 生成二维码（推荐使用 qrcode.js）
    3. 展示 share_link 供用户复制分享
    4. 可直接使用 share_text 作为分享文案
    5. 如果有 inviter，显示邀请人信息（头像、昵称、邀请码）

    **分享链接格式：**
    https://yourdomain.com/register?ref=ABC123

    **新用户注册时：**
    - 前端将 ref 参数值填入注册表单的"邀请码"字段
    - 后端自动绑定推荐关系
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "examples": {
                        "with_inviter": {
                            "summary": "有邀请人",
                            "value": {
                                "code": 1,
                                "message": "获取成功",
                                "data": {
                                    "distributor_code": "ABC123",
                                    "share_link": "https://yourdomain.com/register?ref=ABC123",
                                    "share_text": "邀请您使用我们的服务，输入邀请码：ABC123",
                                    "inviter": {
                                        "inviter_id": "user_xxx",
                                        "inviter_nickname": "推广大使",
                                        "inviter_avatar": "https://example.com/avatar.jpg",
                                        "inviter_code": "XYZ789"
                                    }
                                }
                            }
                        },
                        "without_inviter": {
                            "summary": "无邀请人",
                            "value": {
                                "code": 1,
                                "message": "获取成功",
                                "data": {
                                    "distributor_code": "ABC123",
                                    "share_link": "https://yourdomain.com/register?ref=ABC123",
                                    "share_text": "邀请您使用我们的服务，输入邀请码：ABC123",
                                    "inviter": None
                                }
                            }
                        }
                    }
                }
            }
        },
        400: {
            "description": "获取失败",
            "content": {
                "application/json": {
                    "examples": {
                        "not_distributor": {
                            "summary": "不是分销商",
                            "value": {
                                "code": 0,
                                "message": "您还不是分销商",
                                "data": None
                            }
                        }
                    }
                }
            }
        }
    }
)
async def get_my_distributor_code(
    current_user: dict = Depends(get_current_user_info)
) -> Dict[str, Any]:
    """
    获取我的推广码

    Args:
        current_user: 当前认证用户信息

    Returns:
        包含推广码、分享链接和邀请人信息的响应
    """
    result = distribution_service.get_my_distributor_code(current_user["user_id"])
    if result.get("success"):
        return response.success(data={
            "distributor_code": result.get("distributor_code"),
            "share_link": result.get("share_link"),
            "share_text": result.get("share_text"),
            "inviter": result.get("inviter")  # 新增：邀请人信息
        })
    return response.fail(message=result.get("error", "获取推广码失败"))


class MiniQrcodeRequest(BaseModel):
    """小程序分销海报请求"""
    page: Optional[str] = None
    img: int = 1

    class Config:
        json_schema_extra = {
            "example": {
                "page": "pages/index/index",
                "img": 1
            }
        }


@router.post(
    "/mini-qrcode",
    summary="获取小程序分销海报",
    description="""
    生成当前用户的微信小程序分销海报（包含小程序码）。

    **功能说明：**
    - 生成不限制的小程序码（永久有效，数量无限制）
    - 小程序码的 scene 参数包含用户的邀请码
    - 小程序码会自动拼接在海报模板底部
    - 返回完整的分销海报图片（PNG格式）
    - 支持选择不同的海报模板（1-4）

    **业务流程：**
    1. 用户必须是分销商才能生成海报
    2. 系统生成包含用户邀请码的小程序码
    3. 将小程序码拼接在海报模板上
    4. 返回拼接后的海报图片（base64编码）
    5. 用户可保存图片分享给其他人

    **扫码流程：**
    1. 新用户扫描海报上的小程序码
    2. 进入小程序时，scene 参数包含邀请码
    3. 小程序解析 scene 参数获取邀请码
    4. 用户注册时自动填写邀请码，建立推广关系

    **请求参数：**
    - page: 小程序页面路径（可选，默认主页）
      - 如 pages/index/index
      - 根路径前不要加 /
      - 不能携带参数（参数放在 scene 中）
    - img: 海报模板编号（1-4，默认1）
      - 1: poster1.png（二维码位于右下角，距右边18px，距底部15px）
      - 2: poster2.png（二维码向左移20px，向上移20px）
      - 3: poster3.png（二维码向左移20px，向上移20px）
      - 4: poster4.png（二维码向左移20px，向上移20px）

    **响应格式：**
    - Content-Type: application/json
    - 返回 base64 编码的海报图片数据
    - data_url: data:image/png;base64,...（可直接用于 img 标签）

    **前端使用示例：**
    ```javascript
    // 发起请求
    wx.request({
      url: 'https://api.example.com/api/distribution/mini-qrcode',
      method: 'POST',
      header: {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
      },
      data: {
        page: 'pages/index/index',
        img: 1
      },
      success: (res) => {
        if (res.data.code === 1) {
          // 直接使用 data_url
          this.posterUrl = res.data.data.data_url;
          // 或者
          this.posterBase64 = res.data.data.base64;
        }
      }
    });

    // 在页面中显示
    <image src="{{posterUrl}}" mode="widthFix" />
    ```

    **小程序端解析 scene 参数示例：**
    ```javascript
    // app.js 或首页 onLoad
    onLoad(options) {
      const scene = decodeURIComponent(options.scene || '');
      // scene 就是邀请码，如 "ABC123"
      if (scene) {
        // 自动填入邀请码字段
        this.inviteCode = scene;
      }
    }
    ```

    **注意：**
    - 调用频率受限（5000次/分钟），建议前端缓存
    - 需要配置 WECHAT_MINI_APPID 和 WECHAT_MINI_APPSECRET 环境变量
    - 小程序码永久有效，可预生成
    - 海报模板路径：templates/poster{1-4}.png
    """,
    responses={
        200: {
            "description": "生成成功，返回base64编码的图片数据",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "生成成功",
                        "data": {
                            "distributor_code": "ABC123",
                            "base64": "iVBORw0KGgoAAAANSUhEUgAA...",
                            "data_url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
                        }
                    }
                }
            }
        },
        400: {
            "description": "生成失败",
            "content": {
                "application/json": {
                    "examples": {
                        "not_distributor": {
                            "summary": "不是分销商",
                            "value": {
                                "code": 0,
                                "message": "您还不是分销商",
                                "data": None
                            }
                        },
                        "config_error": {
                            "summary": "配置错误",
                            "value": {
                                "code": 0,
                                "message": "微信小程序配置不完整",
                                "data": None
                            }
                        },
                        "api_error": {
                            "summary": "API调用失败",
                            "value": {
                                "code": 0,
                                "message": "生成小程序码失败: [40097] invalid args",
                                "data": None
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
async def get_mini_qrcode(
    request: MiniQrcodeRequest,
    current_user: dict = Depends(get_current_user_info)
):
    """
    获取小程序推广码

    Args:
        request: 海报请求参数（包含 page 和 img）
        current_user: 当前认证用户信息

    Returns:
        包含base64编码小程序码的响应
    """
    import base64

    result = await distribution_service.generate_mini_qrcode(
        user_id=current_user["user_id"],
        page=request.page,
        img=request.img
    )

    if not result.get("success"):
        return response.fail(message=result.get("error", "生成小程序码失败"))

    # 转换为base64
    qrcode_bytes = result.get("qrcode")
    base64_str = base64.b64encode(qrcode_bytes).decode('utf-8')
    data_url = f"data:image/png;base64,{base64_str}"

    return response.success(data={
        "distributor_code": result.get("distributor_code"),
        "base64": base64_str,
        "data_url": data_url
    }, message="生成成功")


@router.get(
    "/stats",
    summary="获取分销商统计",
    description="""
    获取当前用户的分销统计数据。

    **统计指标：**
    - 推广数据：下级用户数、订单数
    - 佣金数据：累计、可提现、冻结、已提现
    - 本月数据：本月新增、本月佣金

    **数据说明：**
    - total_children_count: 累计推广的用户数
    - total_order_count: 累计产生的订单数
    - total_commission: 累计获得的总佣金
    - available_commission: 可提现佣金（已结算）
    - frozen_commission: 冻结佣金（待结算）
    - total_withdrawn: 累计已提现金额
    - month_children_count: 本月新增用户数
    - month_order_count: 本月新增订单数
    - month_commission: 本月获得佣金

    **更新频率：** 实时更新
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "获取成功",
                        "data": {
                            "total_children_count": 10,
                            "total_order_count": 5,
                            "total_commission": 100.50,
                            "available_commission": 50.00,
                            "frozen_commission": 30.50,
                            "total_withdrawn": 20.00,
                            "month_children_count": 2,
                            "month_order_count": 1,
                            "month_commission": 10.00
                        }
                    }
                }
            }
        },
        400: {
            "description": "获取失败",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "您还不是分销商",
                        "data": None
                    }
                }
            }
        }
    }
)
async def get_distributor_stats(
    current_user: dict = Depends(get_current_user_info)
) -> Dict[str, Any]:
    """
    获取分销商统计

    Args:
        current_user: 当前认证用户信息

    Returns:
        包含统计数据的响应
    """
    result = distribution_service.get_distributor_stats(current_user["user_id"])
    if result.get("success"):
        return response.success(data=result.get("stats"))
    return response.fail(message=result.get("error", "获取统计信息失败"))


# ============================================================================
# 分销记录
# ============================================================================


@router.get(
    "/records",
    summary="获取分销记录",
    description="""
    获取当前用户的分销佣金记录列表。

    **记录说明：**
    - 每条记录对应一笔订单的佣金
    - 订单支付后自动创建分销记录
    - 佣金状态：pending（待结算）→ available（可提现）→ settled（已结算）

    **查询参数：**
    - status: 按佣金状态筛选
      - pending: 待结算
      - available: 可提现
      - settled: 已结算
      - expired: 已过期
    - page: 页码，从1开始
    - page_size: 每页数量，最大100

    **排序方式：** 按创建时间倒序

    **记录字段：**
    - record_id: 记录ID
    - new_user_nickname: 下级用户昵称
    - commission_amount: 佣金金额
    - commission_status: 佣金状态
    - order_amount: 订单金额
    - created_at: 创建时间
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "获取成功",
                        "data": {
                            "total": 25,
                            "page": 1,
                            "page_size": 20,
                            "records": [
                                {
                                    "record_id": "DR123456789",
                                    "new_user_nickname": "张三",
                                    "commission_amount": 10.00,
                                    "commission_status": "available",
                                    "order_amount": 100.00,
                                    "created_at": "2025-01-15T10:00:00"
                                }
                            ]
                        }
                    }
                }
            }
        }
    }
)
async def list_my_records(
    status: Optional[str] = Query(None, description="佣金状态筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: dict = Depends(get_current_user_info)
) -> Dict[str, Any]:
    """
    获取分销记录列表

    Args:
        status: 佣金状态筛选
        page: 页码
        page_size: 每页数量
        current_user: 当前认证用户信息

    Returns:
        包含分销记录列表的响应
    """
    result = distribution_service.list_my_records(
        current_user["user_id"],
        status=status,
        page=page,
        page_size=page_size
    )
    if result.get("success"):
        return response.success(data=result)
    return response.fail(message=result.get("error", "获取分销记录失败"))


# ============================================================================
# 提现申请
# ============================================================================


class CreateWithdrawalRequest(BaseModel):
    """创建提现申请请求"""
    amount: float
    withdrawal_method: str
    account_name: str
    account_number: str
    bank_name: Optional[str] = None
    bank_branch: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "amount": 50.00,
                "withdrawal_method": "wechat",
                "account_name": "张三",
                "account_number": "wx123456",
                "bank_name": None,
                "bank_branch": None
            }
        }


@router.post(
    "/withdraw",
    summary="创建提现申请",
    description="""
    创建提现申请，将可提现佣金提现到指定账户。

    **提现条件：**
    1. 必须是分销商
    2. 账户状态正常（未冻结）
    3. 提现金额 >= 最低提现门槛（默认50元）
    4. 提现金额 <= 可提现余额

    **提现方式：**
    - wechat: 微信（需提供：account_name, account_number）
    - alipay: 支付宝（需提供：account_name, account_number）
    - bank: 银行卡（需提供：account_name, account_number, bank_name, bank_branch）

    **提现流程：**
    1. 用户提交提现申请
    2. 系统冻结对应金额（从可提现变为冻结）
    3. 管理员审核
    4. 审核通过：完成打款，金额从冻结变为已提现
    5. 审核拒绝：金额退回可提现余额

    **请求参数：**
    - amount: 提现金额（元，精确到分）
    - withdrawal_method: 提现方式（wechat/alipay/bank）
    - account_name: 账户持有人姓名
    - account_number: 账户号码
    - bank_name: 银行名称（bank方式必填）
    - bank_branch: 支行名称（bank方式必填）
    """,
    responses={
        200: {
            "description": "申请提交成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "提现申请已提交，等待审核",
                        "data": None
                    }
                }
            }
        },
        400: {
            "description": "提现申请失败",
            "content": {
                "application/json": {
                    "examples": {
                        "not_distributor": {
                            "summary": "不是分销商",
                            "value": {
                                "code": 0,
                                "message": "您还不是分销商",
                                "data": None
                            }
                        },
                        "insufficient_balance": {
                            "summary": "余额不足",
                            "value": {
                                "code": 0,
                                "message": "可提现余额不足，当前可提现 30.00 元",
                                "data": None
                            }
                        },
                        "below_minimum": {
                            "summary": "低于最低金额",
                            "value": {
                                "code": 0,
                                "message": "提现金额不能低于 50 元",
                                "data": None
                            }
                        },
                        "account_frozen": {
                            "summary": "账户冻结",
                            "value": {
                                "code": 0,
                                "message": "您的分销商账户已被冻结，无法提现",
                                "data": None
                            }
                        }
                    }
                }
            }
        }
    }
)
async def create_withdrawal(
    request: CreateWithdrawalRequest,
    current_user: dict = Depends(get_current_user_info)
) -> Dict[str, Any]:
    """
    创建提现申请

    Args:
        request: 提现申请请求
        current_user: 当前认证用户信息

    Returns:
        操作结果响应
    """
    result = distribution_service.create_withdrawal_request(
        user_id=current_user["user_id"],
        amount=request.amount,
        withdrawal_method=request.withdrawal_method,
        account_name=request.account_name,
        account_number=request.account_number,
        bank_name=request.bank_name,
        bank_branch=request.bank_branch
    )
    if result.get("success"):
        return response.success(message=result.get("message"))
    return response.fail(message=result.get("error", "创建提现申请失败"))


@router.get(
    "/withdrawals",
    summary="获取提现记录",
    description="""
    获取当前用户的提现申请记录列表。

    **提现状态：**
    - pending: 待审核
    - processing: 处理中
    - completed: 已完成
    - rejected: 已拒绝
    - cancelled: 已取消

    **查询参数：**
    - page: 页码，从1开始
    - page_size: 每页数量，最大100

    **排序方式：** 按申请时间倒序

    **记录字段：**
    - withdrawal_id: 提现申请ID
    - amount: 提现金额
    - withdrawal_method: 提现方式
    - account_name: 账户持有人姓名
    - account_number: 账户号码（脱敏）
    - status: 提现状态
    - created_at: 申请时间
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "获取成功",
                        "data": {
                            "total": 3,
                            "page": 1,
                            "page_size": 20,
                            "withdrawals": [
                                {
                                    "withdrawal_id": "WD123456789",
                                    "amount": 50.00,
                                    "withdrawal_method": "wechat",
                                    "account_name": "张三",
                                    "account_number": "wx12****56",
                                    "status": "completed",
                                    "created_at": "2025-01-15T10:00:00"
                                }
                            ]
                        }
                    }
                }
            }
        }
    }
)
async def list_my_withdrawals(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: dict = Depends(get_current_user_info)
) -> Dict[str, Any]:
    """
    获取提现记录列表

    Args:
        page: 页码
        page_size: 每页数量
        current_user: 当前认证用户信息

    Returns:
        包含提现记录列表的响应
    """
    result = distribution_service.list_my_withdrawals(
        user_id=current_user["user_id"],
        page=page,
        page_size=page_size
    )
    if result.get("success"):
        return response.success(data=result)
    return response.fail(message=result.get("error", "获取提现记录失败"))


# ============================================================================
# 推广码验证
# ============================================================================


@router.get(
    "/validate-code",
    summary="验证推广码",
    description="""
    验证推广码是否有效。

    **用途：**
    - 用户注册前验证推广码
    - 前端实时提示推广码是否有效
    - 确保用户输入正确的邀请码

    **验证规则：**
    - 推广码必须存在
    - 推广码对应的分销商状态必须为 active
    - 推广码区分大小写

    **无需登录** - 此接口可公开访问

    **使用场景：**
    1. 用户在注册页面输入邀请码
    2. 前端实时调用此接口验证
    3. 根据返回结果提示用户

    **返回值：**
    - valid: true 表示推广码有效
    - promoter_id: 推广人的用户ID（注册时需要）
    """,
    responses={
        200: {
            "description": "验证成功",
            "content": {
                "application/json": {
                    "examples": {
                        "valid": {
                            "summary": "推广码有效",
                            "value": {
                                "code": 1,
                                "message": "推广码有效",
                                "data": {
                                    "valid": True,
                                    "promoter_id": "user_123"
                                }
                            }
                        },
                        "invalid": {
                            "summary": "推广码无效",
                            "value": {
                                "code": 0,
                                "message": "推广码无效",
                                "data": {
                                    "valid": False,
                                    "error": "推广码不存在或已失效"
                                }
                            }
                        }
                    }
                }
            }
        }
    }
)
async def validate_distributor_code(
    code: str = Query(..., description="推广码", min_length=6, max_length=6)
) -> Dict[str, Any]:
    """
    验证推广码有效性

    Args:
        code: 6位推广码

    Returns:
        验证结果
    """
    # 临时修复：直接从数据库查询
    try:
        from app.infra.db import get_sync_engine
        from sqlalchemy import text
        engine = get_sync_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT d.user_id
                    FROM business.distributors d
                    WHERE d.distributor_code = :code AND d.status = 'active'
                    """),
                {"code": code}
            ).fetchone()

            if result:
                return response.success(data={"valid": True, "promoter_id": result[0]}, message="推广码有效")
            return response.fail(data={"valid": False, "error": "推广码无效"}, message="推广码无效")
    except Exception as e:
        return response.fail(data={"valid": False, "error": str(e)}, message="验证失败")


# ============================================================================
# 用户绑定邀请人
# ============================================================================


@router.post(
    "/bind-invite-code",
    summary="绑定邀请码",
    description="""
    为当前登录用户绑定邀请码，建立分销邀请关系。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **绑定规则：**
    1. 邀请码必须是有效的分销商推广码（distributor_code）
    2. 用户只能绑定一次，已绑定的无法重复绑定或修改
    3. 不能绑定自己的邀请码
    4. 绑定成功后，用户的 inviter_id 字段将被设置为邀请人的 user_id

    **业务影响：**
    - 绑定后，该用户后续的消费订单将为邀请人产生佣金收益
    - 佣金计算和结算由分销系统自动处理

    **使用场景：**
    - 用户注册时未填写邀请码，后续想要补充绑定
    - 用户通过推广链接访问，但注册时未自动绑定

    **请求头示例：**
    ```
    Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    ```
    """,
    responses={
        200: {
            "description": "绑定成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "绑定邀请码成功",
                        "data": {
                            "inviter_id": "user_1234567890abcdef",
                            "inviter_nickname": "推广大使"
                        }
                    }
                }
            }
        },
        400: {
            "description": "绑定失败",
            "content": {
                "application/json": {
                    "examples": {
                        "already_bound": {
                            "summary": "已绑定过邀请人",
                            "value": {
                                "code": 0,
                                "message": "您已绑定过邀请人，无法重复绑定",
                                "data": None
                            }
                        },
                        "invalid_code": {
                            "summary": "邀请码无效",
                            "value": {
                                "code": 0,
                                "message": "邀请码无效或不存在",
                                "data": None
                            }
                        },
                        "bind_self": {
                            "summary": "不能绑定自己",
                            "value": {
                                "code": 0,
                                "message": "不能绑定自己的邀请码",
                                "data": None
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
async def bind_invite_code(
    request: BindInviteCodeRequest,
    current_user: dict = Depends(get_current_user_info)
) -> Dict[str, Any]:
    """
    绑定邀请码

    Args:
        request: 包含邀请码的请求
        current_user: 当前认证用户信息

    Returns:
        绑定结果
    """
    result = auth_service.bind_invite_code(
        user_id=current_user["user_id"],
        invite_code=request.invite_code
    )

    if not result["success"]:
        error_msg = result.get("error", "绑定邀请码失败")
        return response.fail(message=error_msg)

    return response.success(
        data={
            "inviter_id": result["inviter_id"],
            "inviter_nickname": result["inviter_nickname"]
        },
        message=result.get("message", "绑定邀请码成功")
    )


# ============================================================================
# 管理员接口
# ============================================================================


@router.get(
    "/admin/distributors",
    summary="获取分销商列表（管理员）",
    description="""
    获取所有分销商列表（仅管理员）。

    **查询参数：**
    - status: 筛选状态（active-活跃, frozen-冻结, inactive-非活跃）
    - page: 页码，从1开始
    - page_size: 每页数量，最大100

    **排序方式：** 按创建时间倒序

    **权限要求：** 管理员权限

    **返回字段：**
    - user_id: 用户ID
    - distributor_code: 推广码
    - status: 状态
    - total_children_count: 下级用户数
    - total_order_count: 订单数
    - total_commission: 累计佣金
    - created_at: 创建时间
    """,
    responses={
        200: {
            "description": "获取成功"
        },
        401: {
            "description": "未授权"
        }
    }
)
async def list_distributors_admin(
    status: Optional[str] = Query(None, description="分销商状态"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: dict = Depends(get_current_user_info)
) -> Dict[str, Any]:
    """
    获取分销商列表（管理员）

    Args:
        status: 状态筛选
        page: 页码
        page_size: 每页数量
        current_user: 当前认证用户信息

    Returns:
        分销商列表
    """
    result = distribution_service.list_distributors(status=status, page=page, page_size=page_size)
    if result.get("success"):
        return response.success(data=result)
    return response.fail(message=result.get("error", "获取分销商列表失败"))


@router.get(
    "/admin/distributors/{user_id}",
    summary="获取分销商详情（管理员）",
    description="""
    获取指定分销商的详细信息。

    **返回信息包括:**
    - 分销商基本信息(用户ID、推广码、状态、等级)
    - 统计信息(下级用户数、订单数、累计佣金)
    - 佣金信息(可用佣金、冻结佣金、已提现金额)
    - 上级分销商信息
    - 创建时间等

    **权限要求：** 管理员权限

    **路径参数:**
    - user_id: 分销商用户ID
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "操作成功",
                        "data": {
                            "user_id": "user_123456",
                            "distributor_code": "ABC123",
                            "parent_id": "user_789",
                            "distributor_level": 3,
                            "status": "active",
                            "total_children_count": 15,
                            "total_order_count": 50,
                            "total_commission": 5000.00,
                            "available_commission": 1000.00,
                            "frozen_commission": 500.00,
                            "total_withdrawn": 3500.00,
                            "parent_info": {
                                "user_id": "user_789",
                                "nickname": "上级分销商",
                                "distributor_code": "XYZ789"
                            },
                            "created_at": "2026-01-01T10:00:00"
                        }
                    }
                }
            }
        },
        404: {
            "description": "分销商不存在",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "分销商不存在",
                        "data": None
                    }
                }
            }
        }
    }
)
async def get_distributor_detail_admin(
    user_id: str,
    current_user: dict = Depends(get_current_user_info)
) -> Dict[str, Any]:
    """
    获取分销商详情（管理员）

    Args:
        user_id: 分销商用户ID
        current_user: 当前认证用户信息

    Returns:
        分销商详情
    """
    result = distribution_service.get_distributor_detail(user_id)
    if result.get("success"):
        return response.success(data=result)
    return response.fail(message=result.get("error", "获取分销商详情失败"))


@router.put(
    "/admin/distributors/{user_id}/status",
    summary="更新分销商状态（管理员）",
    description="""
    更新分销商的状态（冻结/解冻/禁用）。

    **状态说明:**
    - active: 活跃（正常）
    - frozen: 冻结（暂停分销资格）
    - inactive: 非活跃（已禁用）

    **权限要求：** 管理员权限

    **路径参数:**
    - user_id: 分销商用户ID
    """,
    responses={
        200: {
            "description": "更新成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "分销商状态已更新",
                        "data": None
                    }
                }
            }
        }
    }
)
async def update_distributor_status_admin(
    user_id: str,
    status: str = Query(..., description="状态: active/frozen/inactive"),
    current_user: dict = Depends(get_current_user_info)
) -> Dict[str, Any]:
    """
    更新分销商状态（管理员）

    Args:
        user_id: 分销商用户ID
        status: 新状态
        current_user: 当前认证用户信息

    Returns:
        操作结果
    """
    result = distribution_service.update_distributor_status(user_id, status, current_user["user_id"])
    if result.get("success"):
        return response.success(message=result.get("message", "分销商状态已更新"))
    return response.fail(message=result.get("error", "更新分销商状态失败"))


@router.get(
    "/admin/withdrawals",
    summary="获取提现申请列表（管理员）",
    description="""
    获取所有提现申请列表（仅管理员）。

    **查询参数：**
    - status: 筛选状态（pending-待审核, processing-处理中, completed-已完成, rejected-已拒绝）
    - page: 页码，从1开始
    - page_size: 每页数量，最大100

    **排序方式：** 按申请时间倒序

    **权限要求：** 管理员权限

    **返回字段：**
    - withdrawal_id: 提现申请ID
    - user_id: 用户ID
    - amount: 提现金额
    - withdrawal_method: 提现方式
    - account_name: 账户持有人姓名
    - account_number: 账户号码
    - status: 状态
    - reject_reason: 拒绝原因（如有）
    - created_at: 申请时间
    """,
    responses={
        200: {
            "description": "获取成功"
        },
        401: {
            "description": "未授权"
        }
    }
)
async def list_withdrawals_admin(
    status: Optional[str] = Query(None, description="提现状态"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: dict = Depends(get_current_user_info)
) -> Dict[str, Any]:
    """
    获取提现申请列表（管理员）

    Args:
        status: 状态筛选
        page: 页码
        page_size: 每页数量
        current_user: 当前认证用户信息

    Returns:
        提现申请列表
    """
    result = distribution_service.list_withdrawals(status=status, page=page, page_size=page_size)
    if result.get("success"):
        return response.success(data=result)
    return response.fail(message=result.get("error", "获取提现列表失败"))


@router.get(
    "/admin/withdrawals/{withdrawal_id}",
    summary="获取提现申请详情（管理员）",
    description="""
    获取指定提现申请的详细信息。

    **返回信息包括:**
    - 提现申请基本信息(申请ID、申请金额、状态等)
    - 分销商信息(分销商ID、分销商昵称、手机号)
    - 银行账户信息(账户类型、银行名称、账户号、持卡人姓名)
    - 审核信息(审核状态、处理时间、交易流水号、处理备注)
    - 统计信息(总佣金、可提现金额、冻结金额、已提现金额)

    **权限要求：** 管理员权限

    **路径参数:**
    - withdrawal_id: 提现申请ID
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "操作成功",
                        "data": {
                            "id": "wd_1234567890",
                            "distributor_id": "user_123456",
                            "distributor_name": "张三",
                            "distributor_phone": "13800138000",
                            "amount": 500.00,
                            "account_type": "bank_card",
                            "bank_name": "中国工商银行",
                            "account_number": "6222021234567890123",
                            "account_holder": "张三",
                            "status": "pending",
                            "created_at": "2026-01-20T10:00:00",
                            "total_commission": 5000.00,
                            "available_balance": 1000.00,
                            "frozen_amount": 500.00,
                            "withdrawn_amount": 3500.00
                        }
                    }
                }
            }
        },
        404: {
            "description": "提现申请不存在",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "提现申请不存在",
                        "data": None
                    }
                }
            }
        }
    }
)
async def get_withdrawal_detail_admin(
    withdrawal_id: str,
    current_user: dict = Depends(get_current_user_info)
) -> Dict[str, Any]:
    """
    获取提现申请详情（管理员）

    Args:
        withdrawal_id: 提现申请ID
        current_user: 当前认证用户信息

    Returns:
        提现申请详情
    """
    result = distribution_service.get_withdrawal_detail(withdrawal_id)
    if result.get("success"):
        return response.success(data=result)
    return response.fail(message=result.get("error", "获取提现详情失败"))


class ApproveWithdrawalRequest(BaseModel):
    """审核通过提现申请"""
    transaction_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "TX123456789"
            }
        }


@router.post(
    "/admin/withdrawals/{withdrawal_id}/approve",
    summary="审核通过提现（管理员）",
    description="""
    审核通过提现申请并完成打款（仅管理员）。

    **操作流程：**
    1. 管理员确认已线下打款
    2. 调用此接口标记为审核通过
    3. 系统扣减分销商冻结金额
    4. 增加已提现金额
    5. 更新提现状态为 completed
    6. 记录交易流水号

    **请求参数：**
    - withdrawal_id: 提现申请ID（路径参数）
    - transaction_id: 支付平台交易流水号（可选）

    **权限要求：** 管理员权限
    """,
    responses={
        200: {
            "description": "审核通过",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "提现已完成",
                        "data": None
                    }
                }
            }
        },
        400: {
            "description": "操作失败",
            "content": {
                "application/json": {
                    "examples": {
                        "not_found": {
                            "summary": "提现申请不存在",
                            "value": {
                                "code": 0,
                                "message": "提现申请不存在",
                                "data": None
                            }
                        },
                        "invalid_status": {
                            "summary": "状态不正确",
                            "value": {
                                "code": 0,
                                "message": "该提现申请已处理",
                                "data": None
                            }
                        }
                    }
                }
            }
        }
    }
)
async def approve_withdrawal(
    withdrawal_id: str,
    request: ApproveWithdrawalRequest,
    current_user: dict = Depends(get_current_user_info)
) -> Dict[str, Any]:
    """
    审核通过提现申请（管理员）

    Args:
        withdrawal_id: 提现申请ID
        request: 审核请求
        current_user: 当前认证用户信息

    Returns:
        操作结果
    """
    result = distribution_service.approve_withdrawal(
        withdrawal_id=withdrawal_id,
        processed_by=current_user["user_id"],
        transaction_id=request.transaction_id
    )
    if result.get("success"):
        return response.success(message=result.get("message"))
    return response.fail(message=result.get("error", "审核失败"))


class RejectWithdrawalRequest(BaseModel):
    """拒绝提现申请"""
    reject_reason: str

    class Config:
        json_schema_extra = {
            "example": {
                "reject_reason": "账户信息不完整"
            }
        }


@router.post(
    "/admin/withdrawals/{withdrawal_id}/reject",
    summary="拒绝提现（管理员）",
    description="""
    拒绝提现申请（仅管理员）。

    **操作流程：**
    1. 管理员发现提现申请有问题
    2. 调用此接口拒绝申请
    3. 系统将冻结金额退回可提现余额
    4. 更新提现状态为 rejected
    5. 记录拒绝原因

    **请求参数：**
    - withdrawal_id: 提现申请ID（路径参数）
    - reject_reason: 拒绝原因（必填）

    **权限要求：** 管理员权限

    **常见拒绝原因：**
    - 账户信息不完整或不正确
    - 账户持有人姓名与实名不符
    - 银行卡已注销
    - 其他合规问题
    """,
    responses={
        200: {
            "description": "已拒绝",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "提现已拒绝",
                        "data": None
                    }
                }
            }
        },
        400: {
            "description": "操作失败",
            "content": {
                "application/json": {
                    "examples": {
                        "not_found": {
                            "summary": "提现申请不存在",
                            "value": {
                                "code": 0,
                                "message": "提现申请不存在",
                                "data": None
                            }
                        },
                        "invalid_status": {
                            "summary": "状态不正确",
                            "value": {
                                "code": 0,
                                "message": "该提现申请已处理",
                                "data": None
                            }
                        }
                    }
                }
            }
        }
    }
)
async def reject_withdrawal(
    withdrawal_id: str,
    request: RejectWithdrawalRequest,
    current_user: dict = Depends(get_current_user_info)
) -> Dict[str, Any]:
    """
    拒绝提现申请（管理员）

    Args:
        withdrawal_id: 提现申请ID
        request: 拒绝请求
        current_user: 当前认证用户信息

    Returns:
        操作结果
    """
    result = distribution_service.reject_withdrawal(
        withdrawal_id=withdrawal_id,
        processed_by=current_user["user_id"],
        reject_reason=request.reject_reason
    )
    if result.get("success"):
        return response.success(message=result.get("message"))
    return response.fail(message=result.get("error", "拒绝失败"))
