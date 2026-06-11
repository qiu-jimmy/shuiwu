"""
阿里云OSS客户端配置和初始化
"""
import os
from typing import Optional

import alibabacloud_oss_v2 as oss
from sqlalchemy import text
from app.infra.db import get_sync_engine


class OSSClientManager:
    """OSS客户端管理器"""

    def __init__(self):
        self._client: Optional[oss.Client] = None
        self._config = {}
        self._initialized = False

    def initialize_from_db(self) -> bool:
        """从数据库加载OSS配置并初始化客户端"""
        if self._initialized and self._client:
            return True

        try:
            # 首先尝试从环境变量获取配置
            access_key_id = os.getenv('OSS_ACCESS_KEY_ID')
            access_key_secret = os.getenv('OSS_ACCESS_KEY_SECRET')
            region = os.getenv('OSS_REGION', 'cn-hangzhou')
            bucket = os.getenv('OSS_BUCKET')
            endpoint = os.getenv('OSS_ENDPOINT')

            # 如果环境变量中有完整配置，直接使用
            if all([access_key_id, access_key_secret, bucket]):
                return self.initialize_direct(access_key_id, access_key_secret, region, bucket, endpoint)

            # 否则从数据库读取配置
            engine = get_sync_engine()
            with engine.connect() as conn:
                # 从系统配置表读取OSS配置
                row = conn.execute(text("""
                    SELECT config FROM system.configs
                    WHERE config_key = 'oss_settings'
                """)).fetchone()

                if not row:
                    print("未找到OSS配置，请先配置OSS参数（环境变量或数据库）")
                    return False

                import json
                # 安全地获取配置值 - psycopg3 Row 对象通过列名访问
                try:
                    config_value = row['config']  # 通过列名访问
                except (KeyError, TypeError):
                    # 如果列名访问失败，尝试索引访问
                    try:
                        config_value = row[0]
                    except (IndexError, TypeError):
                        print(f"无法获取配置值，row类型: {type(row)}")
                        return False

                if isinstance(config_value, str):
                    config = json.loads(config_value)
                elif isinstance(config_value, dict):
                    config = config_value
                else:
                    print(f"配置格式错误: {type(config_value)}")
                    return False

                # 从环境变量或配置中获取凭证
                access_key_id = os.getenv('OSS_ACCESS_KEY_ID') or config.get('access_key_id')
                access_key_secret = os.getenv('OSS_ACCESS_KEY_SECRET') or config.get('access_key_secret')
                region = config.get('region', 'cn-hangzhou')
                bucket = config.get('bucket')
                endpoint = config.get('endpoint')

                if not all([access_key_id, access_key_secret, region, bucket]):
                    print("OSS配置不完整，需要: access_key_id, access_key_secret, region, bucket")
                    return False

                # 创建凭证提供者
                credentials_provider = oss.credentials.StaticCredentialsProvider(
                    access_key_id=access_key_id,
                    access_key_secret=access_key_secret
                )

                # 加载SDK默认配置
                cfg = oss.config.load_default()
                cfg.credentials_provider = credentials_provider
                cfg.region = region

                # 方式一：只填写Region（推荐）
                # SDK会根据Region自动构造HTTPS访问域名，避免endpoint不匹配问题
                # 如果需要自定义endpoint，请确保格式正确且与bucket Region一致
                # 注意：endpoint不应包含协议前缀，例如：oss-cn-hangzhou.aliyuncs.com
                if endpoint and endpoint.strip():
                    # 移除可能的协议前缀
                    endpoint_clean = endpoint.replace('https://', '').replace('http://', '').strip()
                    if endpoint_clean:
                        cfg.endpoint = endpoint_clean

                # 创建OSS客户端
                self._client = oss.Client(cfg)
                self._config = {
                    'bucket': bucket,
                    'region': region,
                    'endpoint': endpoint
                }
                self._initialized = True

                print(f"OSS客户端初始化成功 - Bucket: {bucket}, Region: {region}")
                return True

        except Exception as e:
            print(f"初始化OSS客户端失败: {e}")
            return False

    def initialize_direct(self, access_key_id: str, access_key_secret: str,
                         region: str, bucket: str, endpoint: Optional[str] = None) -> bool:
        """直接初始化OSS客户端（用于测试或首次配置）"""
        try:
            # 创建凭证提供者
            credentials_provider = oss.credentials.StaticCredentialsProvider(
                access_key_id=access_key_id,
                access_key_secret=access_key_secret
            )

            # 加载SDK默认配置
            cfg = oss.config.load_default()
            cfg.credentials_provider = credentials_provider
            cfg.region = region

            # 方式一：只填写Region（推荐）
            # SDK会根据Region自动构造HTTPS访问域名，避免endpoint不匹配问题
            # 如果需要自定义endpoint，请确保格式正确且与bucket Region一致
            # 注意：endpoint不应包含协议前缀，例如：oss-cn-hangzhou.aliyuncs.com
            if endpoint and endpoint.strip():
                # 移除可能的协议前缀
                endpoint_clean = endpoint.replace('https://', '').replace('http://', '').strip()
                if endpoint_clean:
                    cfg.endpoint = endpoint_clean

            # 创建OSS客户端
            self._client = oss.Client(cfg)
            self._config = {
                'bucket': bucket,
                'region': region,
                'endpoint': endpoint
            }
            self._initialized = True

            print(f"OSS客户端初始化成功 - Bucket: {bucket}, Region: {region}")
            return True

        except Exception as e:
            print(f"初始化OSS客户端失败: {e}")
            return False

    @property
    def client(self) -> Optional[oss.Client]:
        """获取OSS客户端"""
        if not self._initialized:
            self.initialize_from_db()
        return self._client

    @property
    def bucket(self) -> Optional[str]:
        """获取Bucket名称"""
        if not self._initialized:
            self.initialize_from_db()
        return self._config.get('bucket')

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized and self._client is not None

    def save_config_to_db(self, access_key_id: str, access_key_secret: str,
                         region: str, bucket: str, endpoint: Optional[str] = None) -> bool:
        """保存OSS配置到数据库"""
        try:
            import json
            engine = get_sync_engine()
            with engine.connect() as conn:
                # 确保system schema存在
                conn.execute(text("CREATE SCHEMA IF NOT EXISTS system"))
                conn.commit()

                # 创建configs表（如果不存在）
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS system.configs (
                        config_key VARCHAR(100) PRIMARY KEY,
                        config JSONB NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                conn.commit()

                # 保存OSS配置
                config = {
                    'access_key_id': access_key_id,
                    'access_key_secret': access_key_secret,
                    'region': region,
                    'bucket': bucket,
                    'endpoint': endpoint
                }

                conn.execute(text("""
                    INSERT INTO system.configs (config_key, config)
                    VALUES ('oss_settings', :config)
                    ON CONFLICT (config_key) DO UPDATE
                    SET config = :config, updated_at = CURRENT_TIMESTAMP
                """), {"config": json.dumps(config)})
                conn.commit()

                print("OSS配置已保存到数据库")
                return True

        except Exception as e:
            print(f"保存OSS配置失败: {e}")
            return False


# 全局OSS客户端管理器实例
oss_client_manager = OSSClientManager()
