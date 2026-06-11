"""
创建测试用户脚本
"""
import os
import sys
import bcrypt
from sqlalchemy import text
from dotenv import load_dotenv

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载环境变量
load_dotenv()

from app.infra.db import get_sync_engine

def create_test_user():
    """创建测试用户"""
    try:
        engine = get_sync_engine()
        with engine.connect() as conn:
            # 检查用户是否存在
            result = conn.execute(
                text('SELECT user_id, phone, nickname FROM business.users WHERE phone = :phone'),
                {'phone': '13800138000'}
            ).fetchone()

            if result:
                print(f'用户已存在: {dict(result._mapping)}')
                return dict(result._mapping)

            # 创建用户
            user_id = 'user_test_13800138000'
            password_hash = bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            conn.execute(text('''
                INSERT INTO business.users (user_id, phone, nickname, password_hash, status, user_type, member_level)
                VALUES (:user_id, :phone, :nickname, :password_hash, :status, :user_type, :member_level)
            '''), {
                'user_id': user_id,
                'phone': '13800138000',
                'nickname': '会员测试用户',
                'password_hash': password_hash,
                'status': 'normal',
                'user_type': 'individual',
                'member_level': 'free'
            })
            conn.commit()

            print(f'测试用户创建成功: {user_id}')
            print('登录信息:')
            print('  用户名: 13800138000')
            print('  密码: password123')

            return {'user_id': user_id, 'phone': '13800138000'}

    except Exception as e:
        print(f'创建测试用户失败: {e}')
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    create_test_user()
