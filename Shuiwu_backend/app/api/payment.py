"""
微信支付模块 - API路由
"""
import json
import os
from datetime import datetime
from fastapi import APIRouter, Request, Header, HTTPException, Depends, Query
from typing import Optional
from sqlalchemy import text
from app.schemas.payment import (
    CreatePaymentRequest,
    CreatePaymentResponse,
    PaymentStatusResponse,
    RefundResponse,
    WechatPayParams
)
from app.services.wechat_pay.wechat_pay_service import wechat_pay_service
from app.services.member.member_service import member_service
from app.utils.response import response
from app.utils.dependencies import get_current_user_info
from app.infra.db import get_sync_engine

router = APIRouter(prefix="/api/payments", tags=["微信支付"])

# 测试模式开关（从环境变量读取）
PAYMENT_TEST_MODE = os.getenv("PAYMENT_TEST_MODE", "false").lower() == "true"


@router.post(
    "/jsapi",
    summary="发起JSAPI支付",
    description="""
    发起微信小程序JSAPI支付。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **请求参数：**
    - order_id: 订单ID
    - openid: 微信用户OpenID

    **返回信息：**
    - prepay_id: 预支付交易会话标识
    - pay_params: 小程序支付所需参数（appId, timeStamp, nonceStr, package, signType, paySign）

    **使用流程：**
    1. 前端调用此接口获取支付参数
    2. 使用返回的pay_params调用小程序 wx.requestPayment() API
    3. 用户完成支付后，微信通过回调接口通知后端
    4. 前端轮询查询订单状态，或等待支付结果页跳转

    **小程序支付示例：**
    ```javascript
    wx.requestPayment({
      appId: res.data.pay_params.appId,
      timeStamp: res.data.pay_params.timeStamp,
      nonceStr: res.data.pay_params.nonceStr,
      package: res.data.pay_params.package,
      signType: res.data.pay_params.signType,
      paySign: res.data.pay_params.paySign,
      success(res) {
        console.log('支付成功', res)
      },
      fail(res) {
        console.log('支付失败', res)
      }
    })
    ```
    """,
    responses={
        200: {
            "description": "创建支付成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "创建支付成功",
                        "data": {
                            "prepay_id": "wx1234567890abcdef12345678901234",
                            "pay_params": {
                                "appId": "wx1234567890abcdef",
                                "timeStamp": "1642234567",
                                "nonceStr": "5K8264ILTKCH16CQ2502SI8ZNMTM67VS",
                                "package": "prepay_id=wx1234567890abcdef12345678901234",
                                "signType": "RSA",
                                "paySign": "A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q7R8S9T0U1V2W3X4Y5Z6a7b8c9d0e1f2"
                            }
                        }
                    }
                }
            }
        },
        400: {
            "description": "创建失败",
            "content": {
                "application/json": {
                    "examples": {
                        "order_not_found": {
                            "summary": "订单不存在",
                            "value": {
                                "code": 0,
                                "message": "订单不存在",
                                "data": None
                            }
                        },
                        "order_already_paid": {
                            "summary": "订单已支付",
                            "value": {
                                "code": 0,
                                "message": "订单已支付",
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
async def create_payment(
    request: CreatePaymentRequest,
    current_user: dict = Depends(get_current_user_info)
):
    """发起JSAPI支付"""
    result = await wechat_pay_service.create_jsapi_order(
        order_id=request.order_id,
        openid=request.openid
    )

    if result.get("success"):
        return response.success(
            data={
                "prepay_id": result.get("prepay_id"),
                "pay_params": result.get("pay_params")
            },
            message="创建支付成功"
        )
    return response.fail(message=result.get("error", "创建支付失败"))


@router.post(
    "/notify",
    summary="微信支付回调通知",
    description="""
    接收微信支付异步回调通知。

    **注意：** 此接口不需要认证，微信服务器直接调用

    **处理流程：**
    1. 验证回调签名（确保请求来自微信）
    2. 解密回调数据
    3. 更新订单支付状态
    4. 激活用户会员权益
    5. 计算分销佣金（如果有）
    6. 返回成功响应给微信

    **安全说明：**
    - 所有回调都会进行签名验证
    - 签名验证失败会返回错误
    - 即使处理失败也会返回200，避免微信重复推送

    **重试机制：**
    - 微信会在一定时间内重试发送回调
    - 需保证幂等性处理
    """,
    responses={
        200: {
            "description": "处理成功（返回给微信的格式）",
            "content": {
                "application/json": {
                    "example": {
                        "code": "SUCCESS",
                        "message": "成功"
                    }
                }
            }
        },
        400: {
            "description": "签名验证失败",
            "content": {
                "application/json": {
                    "example": {
                        "code": "FAIL",
                        "message": "签名验证失败"
                    }
                }
            }
        }
    }
)
async def payment_notify(request: Request):
    """处理微信支付回调通知"""
    try:
        # 获取请求头中的签名信息
        timestamp = request.headers.get("Wechatpay-Timestamp", "")
        nonce = request.headers.get("Wechatpay-Nonce", "")
        signature = request.headers.get("Wechatpay-Signature", "")
        serial = request.headers.get("Wechatpay-Serial", "")

        # 获取请求体
        body = await request.body()
        body_str = body.decode('utf-8')

        # 处理支付回调
        result = await wechat_pay_service.handle_payment_notify(
            timestamp=timestamp,
            nonce=nonce,
            body=body_str,
            signature=signature
        )

        # 返回给微信的格式
        if result.get("success"):
            return {
                "code": "SUCCESS",
                "message": "成功"
            }
        else:
            # 即使处理失败，也返回200，避免微信重复推送
            # 但message中包含错误信息
            return {
                "code": "FAIL",
                "message": result.get("error", "处理失败")
            }

    except Exception as e:
        # 异常情况下也返回200，避免微信重复推送
        return {
            "code": "FAIL",
            "message": f"处理异常: {str(e)}"
        }


@router.get(
    "/{order_id}/status",
    summary="查询支付状态",
    description="""
    主动查询订单的支付状态。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **路径参数：**
    - order_id: 订单ID

    **返回信息：**
    - trade_state: 交易状态（SUCCESS-支付成功, REFUND-转入退款, NOTPAY-未支付, CLOSED-已关闭, REVOKED-已撤销, USERPAYING-用户支付中, PAYERROR-支付失败）
    - transaction_id: 微信支付交易号（支付成功后返回）

    **使用场景：**
    - 用户支付完成后，前端轮询查询订单状态
    - 支付超时后主动查询
    - 作为支付回调的补充验证机制
    """,
    responses={
        200: {
            "description": "查询成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "操作成功",
                        "data": {
                            "order_id": "ORD1234567890ABCDEF",
                            "trade_state": "SUCCESS",
                            "transaction_id": "4200001234567890123456789"
                        }
                    }
                }
            }
        },
        404: {
            "description": "订单不存在",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "订单不存在",
                        "data": None
                    }
                }
            }
        }
    }
)
async def query_payment_status(
    order_id: str,
    current_user: dict = Depends(get_current_user_info)
):
    """查询支付状态"""
    result = await wechat_pay_service.query_payment_status(order_id)

    if result.get("success"):
        return response.success(data={
            "order_id": order_id,
            "trade_state": result.get("trade_state"),
            "transaction_id": result.get("transaction_id")
        })
    return response.fail(message=result.get("error", "查询支付状态失败"))


@router.post(
    "/orders/{order_id}/close",
    summary="关闭订单",
    description="""
    关闭未支付的订单。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **路径参数：**
    - order_id: 订单ID

    **关闭规则：**
    - 只能关闭未支付的订单
    - 只能关闭自己的订单
    - 关闭后订单不能再支付

    **使用场景：**
    - 用户主动取消订单
    - 订单超时自动关闭
    """,
    responses={
        200: {
            "description": "关闭成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "订单已关闭",
                        "data": None
                    }
                }
            }
        },
        400: {
            "description": "关闭失败",
            "content": {
                "application/json": {
                    "examples": {
                        "order_not_found": {
                            "summary": "订单不存在",
                            "value": {
                                "code": 0,
                                "message": "订单不存在",
                                "data": None
                            }
                        },
                        "order_already_paid": {
                            "summary": "订单已支付",
                            "value": {
                                "code": 0,
                                "message": "订单已支付，无法关闭",
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
async def close_order(
    order_id: str,
    current_user: dict = Depends(get_current_user_info)
):
    """关闭订单"""
    result = await wechat_pay_service.close_order(order_id)

    if result.get("success"):
        return response.success(message=result.get("message", "订单已关闭"))
    return response.fail(message=result.get("error", "关闭订单失败"))


@router.post(
    "/refunds",
    summary="申请退款",
    description="""
    对已支付的订单申请退款。

    **认证要求：** 需要在请求头中提供有效的 Bearer Token

    **请求参数：**
    - order_id: 订单ID
    - reason: 退款原因（可选）

    **退款规则：**
    - 只能对已支付的订单申请退款
    - 退款金额按订单全额退款
    - 退款需要时间处理，结果通过回调通知

    **退款流程：**
    1. 验证订单状态（必须是已支付）
    2. 调用微信支付退款接口
    3. 生成退款单号
    4. 退款处理完成后通过回调通知

    **注意：**
    - 退款成功后，会员权益不会自动扣除
    - 如需扣除权益，需要管理员手动处理
    """,
    responses={
        200: {
            "description": "退款申请成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "退款申请成功",
                        "data": {
                            "refund_id": "RF1234567890ABCDEF",
                            "status": "PROCESSING"
                        }
                    }
                }
            }
        },
        400: {
            "description": "退款申请失败",
            "content": {
                "application/json": {
                    "examples": {
                        "order_not_found": {
                            "summary": "订单不存在",
                            "value": {
                                "code": 0,
                                "message": "订单不存在",
                                "data": None
                            }
                        },
                        "order_not_paid": {
                            "summary": "订单未支付",
                            "value": {
                                "code": 0,
                                "message": "订单未支付，无法退款",
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
async def create_refund(
    order_id: str,
    reason: Optional[str] = None,
    current_user: dict = Depends(get_current_user_info)
):
    """申请退款"""
    result = await wechat_pay_service.create_refund(
        order_id=order_id,
        reason=reason
    )

    if result.get("success"):
        return response.success(
            data={
                "refund_id": result.get("refund_id"),
                "status": result.get("status")
            },
            message="退款申请成功"
        )
    return response.fail(message=result.get("error", "申请退款失败"))


@router.post(
    "/test/simulate",
    summary="测试支付模拟",
    description="""
    模拟支付结果（仅测试环境使用）。

    **使用场景：**
    - 前端开发测试，无需接入真实微信支付
    - 模拟支付成功/失败场景
    - 测试会员激活流程

    **请求参数：**
    - order_id: 订单ID
    - success: true=模拟支付成功, false=模拟支付失败

    **成功场景：**
    - 更新订单支付状态为"paid"
    - 激活用户会员权益
    - 计算分销佣金（如有）
    - 返回会员到期时间

    **失败场景：**
    - 更新订单状态为"failed"
    - 不激活会员权益

    **注意：**
    - 此接口仅在 `PAYMENT_TEST_MODE=true` 时可用
    - 生产环境请禁用此接口
    """,
    responses={
        200: {
            "description": "模拟成功",
            "content": {
                "application/json": {
                    "examples": {
                        "success": {
                            "summary": "支付成功",
                            "value": {
                                "code": 1,
                                "message": "测试支付成功，会员已激活",
                                "data": {
                                    "order_id": "ORDFF421DAFCCCA410B",
                                    "new_expire_at": "2026-02-22T12:34:56",
                                    "transaction_id": "TEST_1737536096"
                                }
                            }
                        },
                        "fail": {
                            "summary": "支付失败",
                            "value": {
                                "code": 0,
                                "message": "测试支付失败",
                                "data": {
                                    "order_id": "ORDFF421DAFCCCA410B"
                                }
                            }
                        }
                    }
                }
            }
        },
        403: {
            "description": "测试模式未启用",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "测试模式未启用，请设置环境变量 PAYMENT_TEST_MODE=true",
                        "data": None
                    }
                }
            }
        }
    }
)
async def simulate_payment(
    order_id: str = Query(..., description="订单ID"),
    success: bool = Query(..., description="true=模拟支付成功, false=模拟支付失败"),
    current_user: dict = Depends(get_current_user_info)
):
    """模拟支付结果（测试用）"""
    # 检查测试模式是否启用
    if not PAYMENT_TEST_MODE:
        return response.fail(
            message="测试模式未启用，请设置环境变量 PAYMENT_TEST_MODE=true"
        )

    try:
        if success:
            # 模拟支付成功 - 生成测试交易号
            test_transaction_id = f"TEST_{int(datetime.now().timestamp())}"

            # 调用完成支付逻辑（激活会员、计算佣金等）
            result = member_service.complete_payment(
                order_id=order_id,
                transaction_id=test_transaction_id
            )

            if result.get("success"):
                return response.success(
                    data={
                        "order_id": order_id,
                        "new_expire_at": result.get("new_expire_at"),
                        "transaction_id": test_transaction_id
                    },
                    message="测试支付成功，会员已激活"
                )
            else:
                return response.fail(
                    message=result.get("error", "测试支付失败")
                )
        else:
            # 模拟支付失败 - 更新订单状态为失败
            engine = get_sync_engine()
            with engine.connect() as conn:
                # 检查订单是否存在
                order = conn.execute(
                    text("SELECT order_id, payment_status FROM business.orders WHERE order_id = :order_id"),
                    {"order_id": order_id}
                ).fetchone()

                if not order:
                    return response.fail(message="订单不存在")

                # 如果已支付，不允许模拟失败
                if order[1] == "paid":
                    return response.fail(message="订单已支付，无法模拟失败")

                # 更新订单状态为失败
                conn.execute(
                    text("""
                        UPDATE business.orders
                        SET status = 'failed',
                            updated_at = :updated_at
                        WHERE order_id = :order_id
                    """),
                    {
                        "order_id": order_id,
                        "updated_at": datetime.now()
                    }
                )
                conn.commit()

            return response.success(
                data={"order_id": order_id},
                message="测试支付失败"
            )

    except Exception as e:
        return response.fail(message=f"模拟支付异常: {str(e)}")
