import asyncio
import os
import sys
import platform

#  移除 WindowsSelectorEventLoopPolicy，使用默认策略
# 这可能与 MCP 的 streamable-http 连接冲突
# 参考项目使用默认策略也能正常工作
# if platform.system() == "Windows":
#     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 禁用 TensorFlow oneDNN 优化，加快启动速度
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

# 让 sentence-transformers 使用 PyTorch 后端而不是 TensorFlow
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["USE_TF"] = "0"

# 禁止加载 sentence-transformers (项目不使用,但 agno 会尝试导入)
# 这可以避免 60+ 秒的启动延迟
sys.modules["sentence_transformers"] = None
sys.modules["sentence_transformers.cross_encoder"] = None
sys.modules["sentence_transformers.losses"] = None

# 修复 Agno 2.4.3 的 bug：空 runs 数组导致 IndexError
# 必须在导入 Agno 之前应用补丁
try:
    from app.infra import agno_patch  # auto-applies on import
except ImportError:
    pass  # 补丁文件不存在时忽略

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv()

from app.services.mcp.mcp_service import mcp_service_manager
from app.infra.business_db import business_db
from app.services.models.model_cache import model_cache

# 初始化日志系统
from app.infra.logging_config import init_logging, get_logger

# 从环境变量获取日志级别，默认为INFO
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = os.getenv("LOG_DIR", "logs")

# 初始化日志配置
init_logging(
    log_dir=LOG_DIR,
    level=LOG_LEVEL,
    enable_console=True,
    enable_file=True
)

# 获取应用主logger
logger = get_logger("app.main")


async def init_mcp_services_async():
    """异步初始化MCP服务（后台执行）"""
    try:
        logger.info("正在初始化MCP服务（后台）...")
        mcp_service_manager._ensure_database_initialized()
        logger.info("MCP服务初始化完成")
    except Exception as e:
        logger.error(f"MCP服务初始化失败: {e}")
        from app.utils.exception_logger import log_exception
        log_exception(e, extra_info={"task": "init_mcp_services"})


async def preconnect_mcp_services_async():
    """预先连接所有MCP服务（后台执行）"""
    try:
        logger.info("正在预先连接MCP服务（后台）...")
        services_dict = mcp_service_manager.list_services()

        for service_id in services_dict.keys():
            try:
                logger.info(f"正在连接MCP服务: {service_id}")
                result = await mcp_service_manager.check_service_status(service_id)
                if result.get("is_reachable"):
                    logger.info(f"MCP服务 {service_id} 连接成功")
                else:
                    logger.warning(f"MCP服务 {service_id} 连接失败: {result.get('error')}")
            except Exception as e:
                logger.warning(f"MCP服务 {service_id} 预连接失败: {e}")

        logger.info("MCP服务预连接完成")
    except Exception as e:
        logger.error(f"MCP服务预连接失败: {e}")
        from app.utils.exception_logger import log_exception
        log_exception(e, extra_info={"task": "preconnect_mcp_services"})


async def init_model_cache_async():
    """异步初始化模型配置缓存（后台执行）"""
    try:
        logger.info("正在加载模型配置缓存（后台）...")
        model_cache.load_all_models()
        logger.info("模型配置缓存加载完成")
    except Exception as e:
        logger.error(f"模型配置缓存加载失败: {e}")
        from app.utils.exception_logger import log_exception
        log_exception(e, extra_info={"task": "init_model_cache"})


async def init_business_database_async():
    """异步初始化业务数据库（后台执行）"""
    try:
        logger.info("正在初始化业务数据库（后台）...")
        business_db.initialize()
        logger.info("业务数据库初始化完成")
    except Exception as e:
        logger.error(f"业务数据库初始化失败: {e}")
        from app.utils.exception_logger import log_exception
        log_exception(e, extra_info={"task": "init_business_database"})


async def init_wechat_pay_config_async():
    """异步初始化微信支付配置（后台执行）"""
    try:
        logger.info("正在初始化微信支付配置（后台）...")
        from app.services.wechat_pay.wechat_pay_repository import wechat_pay_config
        await wechat_pay_config.load_config()
        logger.info("微信支付配置初始化完成")
    except Exception as e:
        logger.warning(f"微信支付配置初始化失败（可能未配置微信支付）: {e}")


async def init_system_kb_cache_async():
    """异步初始化系统知识库缓存（后台执行）"""
    try:
        logger.info("正在加载系统知识库缓存（后台）...")
        from app.services.knowledge.system_kb_cache import system_kb_cache

        # 在线程池中执行同步的加载操作
        loop = asyncio.get_event_loop()
        count = await loop.run_in_executor(None, system_kb_cache.load_all_system_knowledge_bases)
        logger.info(f"系统知识库缓存加载完成，共 {count} 个知识库")
    except Exception as e:
        logger.error(f"系统知识库缓存加载失败: {e}")
        from app.utils.exception_logger import log_exception
        log_exception(e, extra_info={"task": "init_system_kb_cache"})


async def run_scheduled_tasks():
    """
    后台定时任务

    每小时自动执行：
    1. 结算待处理佣金
    2. 升级分销商等级
    3. 清理超时全景报告
    4. 取消超时订单
    """
    import asyncio
    from app.services.distribution.distribution_service import distribution_service

    while True:
        try:
            # 每小时执行一次（3600秒）
            await asyncio.sleep(3600)

            logger.info("=" * 50)
            logger.info("开始执行定时任务...")

            # 1. 结算佣金
            try:
                logger.info("[任务 1/4] 结算待处理佣金...")
                settle_result = distribution_service.settle_pending_commissions()
                if settle_result.get("success"):
                    logger.info(f" 佣金结算完成: {settle_result.get('message')}")
                else:
                    logger.error(f" 佣金结算失败: {settle_result.get('error')}")
            except Exception as e:
                logger.error(f" 佣金结算异常: {e}")
                from app.utils.exception_logger import log_exception
                log_exception(e, extra_info={"task": "settle_commissions"})

            # 2. 升级等级
            try:
                logger.info("[任务 2/4] 升级分销商等级...")
                upgrade_result = distribution_service.upgrade_distributor_levels()
                if upgrade_result.get("success"):
                    upgraded_count = upgrade_result.get("upgraded_count", 0)
                    logger.info(f" 等级升级完成: {upgrade_result.get('message')}")
                    if upgraded_count > 0:
                        for detail in upgrade_result.get("upgrade_details", []):
                            logger.info(f"   - {detail['user_id']}: Lv.{detail['old_level']} → Lv.{detail['new_level']} "
                                        f"(订单:{detail['total_orders']}, 佣金:{detail['total_commission']:.2f})")
                else:
                    logger.error(f" 等级升级失败: {upgrade_result.get('error')}")
            except Exception as e:
                logger.error(f" 等级升级异常: {e}")
                from app.utils.exception_logger import log_exception
                log_exception(e, extra_info={"task": "upgrade_levels"})

            # 3. 清理超时全景报告
            try:
                logger.info("[任务 3/4] 清理超时全景报告...")
                from app.services.chashuibao.panoramic_report_repository import panoramic_report_repository
                cleanup_result = panoramic_report_repository.mark_expired_reports_as_failed(timeout_minutes=10)
                if cleanup_result.get("success"):
                    updated_count = cleanup_result.get("updated_count", 0)
                    logger.info(f" 超时报告清理完成: {cleanup_result.get('message')}")
                else:
                    logger.error(f" 超时报告清理失败: {cleanup_result.get('error')}")
            except Exception as e:
                logger.error(f" 超时报告清理异常: {e}")
                from app.utils.exception_logger import log_exception
                log_exception(e, extra_info={"task": "cleanup_expired_reports"})

            # 4. 取消超时订单
            try:
                logger.info("[任务 4/4] 取消超时订单...")
                from app.services.member.member_repository import MemberRepository
                order_repo = MemberRepository()
                cancel_result = order_repo.cancel_timeout_orders(timeout_minutes=30)
                if cancel_result.get("success"):
                    updated_count = cancel_result.get("updated_count", 0)
                    logger.info(f" 超时订单取消完成: {cancel_result.get('message')}")
                else:
                    logger.error(f" 超时订单取消失败: {cancel_result.get('error')}")
            except Exception as e:
                logger.error(f" 超时订单取消异常: {e}")
                from app.utils.exception_logger import log_exception
                log_exception(e, extra_info={"task": "cancel_timeout_orders"})

            logger.info("定时任务执行完成")
            logger.info("=" * 50)

        except asyncio.CancelledError:
            logger.info("定时任务已取消")
            break
        except Exception as e:
            logger.error(f"定时任务执行异常: {e}")
            # 继续执行，不退出
            await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动和关闭时的生命周期管理"""
    # 启动时初始化
    logger.info("正在启动应用...")

    # 同步初始化MCP数据库（阻塞启动）
    logger.info("正在初始化MCP数据库...")
    try:
        mcp_service_manager._ensure_database_initialized()
        logger.info("MCP数据库初始化完成")
    except Exception as e:
        logger.error(f"MCP数据库初始化失败: {e}")

    # 异步初始化业务数据库（不阻塞启动）
    asyncio.create_task(init_business_database_async())

    #  禁用预先连接，因为会导致FastAPI事件循环问题
    # asyncio.create_task(preconnect_mcp_services_async())

    # 异步初始化模型配置缓存（不阻塞启动）
    asyncio.create_task(init_model_cache_async())

    # 异步初始化微信支付配置（不阻塞启动）
    asyncio.create_task(init_wechat_pay_config_async())

    # 异步初始化系统知识库缓存（不阻塞启动）
    asyncio.create_task(init_system_kb_cache_async())

    # 启动后台定时任务（不阻塞启动）
    asyncio.create_task(run_scheduled_tasks())
    logger.info("后台定时任务已启动（每小时执行：结算佣金、升级等级、清理超时报告、取消超时订单）")

    logger.info("应用启动完成，服务器已就绪")

    yield

    # 关闭时清理
    logger.info("正在关闭应用...")

    # 清理MCP服务连接
    logger.info("正在清理MCP服务连接...")
    try:
        await mcp_service_manager.cleanup_all_services()
        logger.info("MCP服务清理完成")
    except Exception as e:
        logger.error(f"MCP服务清理失败: {e}")
        from app.utils.exception_logger import log_exception
        log_exception(e, extra_info={"task": "cleanup_mcp_services"})

    # 关闭数据库连接池
    logger.info("正在关闭数据库连接池...")
    try:
        from app.infra.db import async_engine, sync_engine
        await async_engine.dispose()
        logger.info("异步数据库连接池已关闭")
        sync_engine.dispose()
        logger.info("同步数据库连接池已关闭")
    except Exception as e:
        logger.error(f"关闭数据库连接池失败: {e}")


app = FastAPI(
    title="税务后台 API",
    description="基于FastAPI的后端服务，支持AI对话、知识库、企业认证等功能",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc
    openapi_url="/openapi.json"  # OpenAPI JSON
)

# CORS 配置（本地开发允许所有来源，生产环境请按需收紧）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有请求头
    expose_headers=["*"],  # 暴露所有响应头
)

# 注册JWT认证中间件
from app.middleware.jwt_auth import JWTAuthMiddleware
app.add_middleware(JWTAuthMiddleware)

# 注册全局异常处理器
from app.exceptions.handlers import setup_exception_handlers
setup_exception_handlers(app)

# 导入响应工具
from app.utils.response import response


@app.get("/health", summary="健康检查")
async def health_check():
    return response.success(data={"status": "ok"})


@app.get("/api/test", summary="测试接口")
async def test():
    return response.success(data={"message": "Test successful"})


# 注册业务路由
from app.api.mcp import router as mcp_router
app.include_router(mcp_router)

# 注册认证路由
from app.api.auth import router as auth_router
app.include_router(auth_router)

# 注册其他业务路由
from app.api.models import router as models_router
app.include_router(models_router)

# 注册 Chat 业务路由
# TODO(langchain-agent-rewrite): Chat/Agent routes are temporarily disabled.
# The /api/chat/* endpoints will be served by the new LangChain agent service
# through API redirect/proxy after the rewrite scaffold is integrated.
# from app.api.chat import router as chat_router
# app.include_router(chat_router)

# 注册知识库业务路由
from app.api.knowledge import router as knowledge_router
app.include_router(knowledge_router)

# 注册知识库类型路由
from app.api.knowledge_type import router as knowledge_type_router
app.include_router(knowledge_type_router)

# 注册仪表盘业务路由
from app.api.dashboard import router as dashboard_router
app.include_router(dashboard_router)

# 注册文件管理业务路由
from app.api.files import router as files_router
app.include_router(files_router)

# 注册测试异常路由（用于测试异常输出）
from app.api.test_exceptions import router as test_exceptions_router
app.include_router(test_exceptions_router)

# 注册会员订阅业务路由
from app.api.member import router as member_router
app.include_router(member_router)

# 注册权限示例路由
from app.api.permission_examples import router as permission_examples_router
app.include_router(permission_examples_router)

# 注册分销推广业务路由
from app.api.distribution import router as distribution_router
app.include_router(distribution_router)

# 注册系统配置路由
from app.api.config import router as config_router
app.include_router(config_router)

# 注册用户个人中心路由
from app.api.user_center import router as user_center_router
app.include_router(user_center_router)

# 注册微信支付路由
from app.api.payment import router as payment_router
app.include_router(payment_router)

# 注册智能报税路由
from app.api.tax_declaration import router as tax_declaration_router
app.include_router(tax_declaration_router)

# 注册个体户工商申报路由
from app.api.business_declaration import router as business_declaration_router
app.include_router(business_declaration_router)

# 注册管理系统路由
from app.api.admin import router as admin_router
app.include_router(admin_router)

# 注册企业体检报告路由
from app.api.enterprise_report import router as enterprise_report_router
app.include_router(enterprise_report_router)

# 注册问题反馈系统路由
from app.api.feedback import router as feedback_router
app.include_router(feedback_router)

# 注册问题反馈系统-管理员路由
from app.api.admin_feedback import router as admin_feedback_router
app.include_router(admin_feedback_router)

# 注册会员权限示例路由（增强版权限系统）
from app.api.member_permission_examples import router as member_examples_router
app.include_router(member_examples_router, prefix="/api/examples", tags=["会员权限示例"])

# 注册套餐配置管理路由
from app.api.member_package_config import router as package_config_router
app.include_router(package_config_router, prefix="/api/package-config", tags=["套餐配置管理"])

# 注册税务知识文档管理路由
from app.api.tax_knowledge import router as tax_knowledge_router
app.include_router(tax_knowledge_router)

# 注册税务师入驻模块路由
from app.api.tax_accountant import router as tax_accountant_router
app.include_router(tax_accountant_router)

# 注册查税宝经营风险报告路由
from app.api.chashuibao import router as chashuibao_router
app.include_router(chashuibao_router)

# 注册发票穿透报告路由
from app.api.invoice_penetration import router as invoice_penetration_router
app.include_router(invoice_penetration_router)

# 注册 H5 页面路由（微信小程序 WebView 回调等）
from app.api.h5 import router as h5_router
app.include_router(h5_router)

# 注册用户积分路由
from app.api.points import router as points_router
app.include_router(points_router)

# 注册管理端积分管理路由
from app.api.admin_points import router as admin_points_router
app.include_router(admin_points_router)

# 挂载静态文件目录（用于微信校验文件等，挂载在根路径以满足微信校验要求）
# 注意：此 mount 必须放在所有路由注册之后，避免拦截 API 请求
app.mount("/", StaticFiles(directory="static"), name="static")
