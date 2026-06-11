"""
批量上传 policy 文件夹中的 markdown 文档到知识库 kb_user_268_8cea69c9

功能：
1. 获取知识库 kb_user_268_8cea69c9 的实例
2. 使用多重检查避免重复上传：
   - 检查 file 表中是否已存在该文件名
   - 检查 knowledge_base_registry 的 document_ids 中是否已存在
   - 检查知识库表中是否已存在该文档
3. 批量上传文档到 OSS、数据库和知识库
"""

import os
import sys
import base64
import threading
from pathlib import Path
from typing import List, Dict, Set
from concurrent.futures import ThreadPoolExecutor, as_completed

# Windows 控制台编码设置
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载环境变量
from dotenv import load_dotenv
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"[OK] 已加载环境变量文件: {env_path}")
else:
    print(f"[!] 警告: .env 文件不存在: {env_path}")

from app.services.knowledge.knowledge_service import knowledge_service
from app.services.files.files_service import files_service


# ==================== 配置区域 ====================

# Policy 文件夹路径
POLICY_DIR = r"C:\Users\yan\Downloads\policy"

# 目标知识库表名
TARGET_TABLE_NAME = "kb_user_268_8cea69c9"

# 用户ID（根据实际需要修改）
USER_ID = "user_2689ea75e1114ec4"

# 并发线程数
MAX_WORKERS = 10

# 分块配置
CHUNKING_RULE = "recursive"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


# ==================== 工具函数 ====================

def get_all_md_files(folder_path: str) -> List[Path]:
    """获取文件夹下所有 .md 文件"""
    folder = Path(folder_path)
    if not folder.exists():
        print(f"⚠️  文件夹不存在: {folder_path}")
        return []

    files = list(folder.glob("*.md"))
    return files


def process_single_file(file_path: Path, kb, table_name: str, stats: Dict, lock: threading.Lock, index: int) -> bool:
    """
    处理单个文件的上传

    Args:
        file_path: 文件路径
        kb: 知识库实例
        table_name: 知识库表名
        stats: 统计字典
        lock: 线程锁
        index: 文件索引

    Returns:
        是否成功
    """
    try:
        filename = file_path.name

        # ============== 多重检查，避免重复上传 ==============

        # 1. 检查 file 表中是否已存在该文件名
        if files_service.repository.check_file_exists_by_name(USER_ID, filename):
            with lock:
                stats['skipped'] += 1
            print(f"   [⊘] [{index}] {filename}: file表已存在，跳过")
            return True

        # 2. 检查 knowledge_base_registry 的 document_ids 中是否已存在
        if knowledge_service.repository.check_document_in_registry(table_name, filename):
            with lock:
                stats['skipped'] += 1
            print(f"   [⊘] [{index}] {filename}: registry已存在，跳过")
            return True

        # 3. 检查知识库表中是否已存在该文档
        if knowledge_service.repository.check_document_exists(table_name, filename):
            with lock:
                stats['skipped'] += 1
            print(f"   [⊘] [{index}] {filename}: 知识库表已存在，跳过")
            return True

        # ============== 开始上传流程 ==============

        # 第一步：上传文件到OSS和数据库
        print(f"   [1/2] [{index}] 上传到OSS: {filename}")
        file_record = files_service.upload_file_from_path(
            user_id=USER_ID,
            file_path=str(file_path),
            folder_path="policy",
            kb_name=None  # 这里的 kb_name 可以从 registry 获取
        )

        if not file_record:
            with lock:
                stats['failed'] += 1
            print(f"   [X] [{index}] {filename}: OSS上传失败")
            return False

        file_url = file_record.get('file_url', '')
        print(f"        OSS成功 -> {file_url}")

        # 第二步：从本地文件导入到知识库
        print(f"   [2/2] [{index}] 导入知识库: {filename}")

        # 读取本地文件为base64
        with open(file_path, 'rb') as f:
            file_content = f.read()
            file_base64 = base64.b64encode(file_content).decode('utf-8')

        result = knowledge_service.upload_document_from_base64(
            knowledge=kb,
            file_base64=file_base64,
            filename=filename,
            user_id=USER_ID,
            chunking_rule=CHUNKING_RULE,
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )

        if result.get('status') == 'success':
            with lock:
                stats['success'] += 1
            print(f"        [OK] 知识库导入成功")
            return True
        else:
            with lock:
                stats['failed'] += 1
            print(f"        [X] 知识库导入失败: {result.get('message', '未知错误')}")
            return False

    except Exception as e:
        with lock:
            stats['failed'] += 1
        print(f"   [X] [{index}] {file_path.name}: {type(e).__name__}: {str(e)[:100]}")
        return False


def batch_upload_policy_files() -> Dict[str, int]:
    """批量上传 policy 文件夹中的文档"""
    stats = {
        "total": 0,
        "success": 0,
        "failed": 0,
        "skipped": 0,
    }
    lock = threading.Lock()

    try:
        # ============== 获取知识库实例 ==============
        print(f"\n{'='*60}")
        print(f"获取知识库实例: {TARGET_TABLE_NAME}")
        print(f"{'='*60}")

        # 从 registry 获取知识库信息
        kb_info = knowledge_service.repository.get_knowledge_base_registry(TARGET_TABLE_NAME)

        if not kb_info:
            print(f"[X] 知识库 {TARGET_TABLE_NAME} 不存在于注册表中")
            return stats

        kb_name = kb_info.get('kb_name')
        kb_user_id = kb_info.get('user_id')
        embedder_model = kb_info.get('embedder_model', 'text-embedding-3-small')

        print(f"[OK] 找到知识库:")
        print(f"     表名: {TARGET_TABLE_NAME}")
        print(f"     知识库名: {kb_name}")
        print(f"     用户ID: {kb_user_id}")
        print(f"     嵌入模型: {embedder_model}")

        # 加载知识库实例
        kb = knowledge_service.get_or_load_knowledge(
            user_id=kb_user_id,
            kb_name=kb_name,
            embedder_model=embedder_model
        )

        # ============== 获取所有文件 ==============
        print(f"\n{'='*60}")
        print(f"扫描文件: {POLICY_DIR}")
        print(f"{'='*60}")

        files = get_all_md_files(POLICY_DIR)
        print(f"找到 {len(files)} 个 .md 文件")

        if not files:
            print("[!] 没有找到任何 .md 文件")
            return stats

        stats['total'] = len(files)

        # ============== 开始批量上传 ==============
        print(f"\n{'='*60}")
        print(f"开始批量上传")
        print(f"{'='*60}")
        print(f"并发线程数: {MAX_WORKERS}")
        print(f"分块规则: {CHUNKING_RULE}, 大小: {CHUNK_SIZE}, 重叠: {CHUNK_OVERLAP}")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(
                    process_single_file,
                    file_path, kb, TARGET_TABLE_NAME, stats, lock, idx + 1
                ): file_path
                for idx, file_path in enumerate(files)
            }

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    with lock:
                        stats['failed'] += 1
                    print(f"   [X] {futures[future].name}: 未知错误 - {str(e)}")

    except Exception as e:
        print(f"\n[X] 批量上传失败: {str(e)}")
        import traceback
        traceback.print_exc()

    return stats


def main():
    """主函数"""
    print("="*80)
    print("Policy 文档批量上传工具")
    print("="*80)

    # 检查目录
    if not os.path.exists(POLICY_DIR):
        print(f"[X] 目录不存在: {POLICY_DIR}")
        return

    print(f"\n[DIR] 目标目录: {POLICY_DIR}")
    print(f"[KB]  目标知识库表: {TARGET_TABLE_NAME}")
    print(f"[USER] 用户ID: {USER_ID}")

    # 执行批量上传
    stats = batch_upload_policy_files()

    # 打印统计信息
    print(f"\n{'='*60}")
    print(f"上传统计:")
    print(f"  总计: {stats['total']} 个文件")
    print(f"  成功: {stats['success']} 个")
    print(f"  失败: {stats['failed']} 个")
    print(f"  跳过: {stats['skipped']} 个")
    print(f"{'='*60}")

    print("\n[OK] 批量上传完成！")


if __name__ == "__main__":
    main()
