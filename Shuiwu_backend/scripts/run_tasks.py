"""
定时任务脚本

运行方式：
    python scripts/run_tasks.py settle            # 结算待处理佣金
    python scripts/run_tasks.py upgrade          # 升级分销商等级
    python scripts/run_tasks.py cleanup_reports   # 清理超时全景报告
    python scripts/run_tasks.py cleanup_orders    # 取消超时订单
    python scripts/run_tasks.py all              # 执行所有任务

配置 crontab（每小时执行一次）：
    0 * * * * cd /path/to/Shuiwu_backend && D:/project/python/python.exe scripts/run_tasks.py all >> logs/tasks.log 2>&1
"""
import sys
import os
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv()


def print_banner(task_name):
    """打印任务横幅"""
    print("\n" + "=" * 60)
    print(f"  {task_name}")
    print(f"  开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")


def print_result(result):
    """打印任务结果"""
    if result.get("success"):
        print(f" {result.get('message', '执行成功')}")
        if "upgraded_count" in result:
            print(f"   升级数量: {result['upgraded_count']}")
        if "updated_count" in result:
            print(f"   更新数量: {result['updated_count']}")
    else:
        print(f" {result.get('error', '执行失败')}")


def settle_commissions():
    """结算待处理佣金"""
    print_banner("佣金结算任务")

    from app.services.distribution.distribution_service import distribution_service

    result = distribution_service.settle_pending_commissions()
    print_result(result)

    return result


def upgrade_levels():
    """升级分销商等级"""
    print_banner("分销商等级升级任务")

    from app.services.distribution.distribution_service import distribution_service

    result = distribution_service.upgrade_distributor_levels()
    print_result(result)

    if result.get("success") and result.get("upgrade_details"):
        print("\n升级详情:")
        for detail in result["upgrade_details"]:
            print(f"  - {detail['user_id']}: Lv.{detail['old_level']} → Lv.{detail['new_level']} "
                  f"(订单:{detail['total_orders']}, 佣金:{detail['total_commission']:.2f})")

    return result


def cleanup_expired_reports():
    """清理超时的全景报告（将超过10分钟的pending状态报告标记为失败）"""
    print_banner("全景报告超时清理任务")

    from app.services.chashuibao.panoramic_report_repository import panoramic_report_repository

    result = panoramic_report_repository.mark_expired_reports_as_failed(timeout_minutes=10)
    print_result(result)

    return result


def cancel_timeout_orders():
    """取消超时的待支付订单（将超过10分钟的pending订单标记为已取消）"""
    print_banner("超时订单取消任务")

    from app.services.member.member_repository import MemberRepository

    repo = MemberRepository()
    result = repo.cancel_timeout_orders(timeout_minutes=10)
    print_result(result)

    return result


def run_all_tasks():
    """执行所有任务"""
    print_banner("执行所有定时任务")
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    results = {}

    # 任务1：结算佣金
    print("\n[任务 1/4] 佣金结算")
    results["settle"] = settle_commissions()

    # 任务2：升级等级
    print("\n[任务 2/4] 等级升级")
    results["upgrade"] = upgrade_levels()

    # 任务3：清理超时全景报告
    print("\n[任务 3/4] 清理超时全景报告")
    results["cleanup_reports"] = cleanup_expired_reports()

    # 任务4：取消超时订单
    print("\n[任务 4/4] 取消超时订单")
    results["cancel_orders"] = cancel_timeout_orders()

    # 汇总结果
    print("\n" + "=" * 60)
    print("  任务执行汇总")
    print("=" * 60)

    for task_name, result in results.items():
        status = " 成功" if result.get("success") else "❌ 失败"
        print(f"  {task_name}: {status}")

    print(f"\n完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return results


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python scripts/run_tasks.py settle            # 结算待处理佣金")
        print("  python scripts/run_tasks.py upgrade           # 升级分销商等级")
        print("  python scripts/run_tasks.py cleanup_reports   # 清理超时全景报告")
        print("  python scripts/run_tasks.py cleanup_orders    # 取消超时订单")
        print("  python scripts/run_tasks.py all               # 执行所有任务")
        sys.exit(1)

    task = sys.argv[1].lower()

    if task == "settle":
        settle_commissions()
    elif task == "upgrade":
        upgrade_levels()
    elif task == "cleanup_reports":
        cleanup_expired_reports()
    elif task == "cleanup_orders":
        cancel_timeout_orders()
    elif task == "all":
        run_all_tasks()
    else:
        print(f"未知任务: {task}")
        print("可用任务: settle, upgrade, cleanup_reports, cleanup_orders, all")
        sys.exit(1)


if __name__ == "__main__":
    main()
