"""
应用环境与核心配置读取器 (Config)
=================================
系统统一的配置数据类。用于从物理系统的 .env 文件读取变量和常量，覆盖如大模型地址、密钥、
日志层级和 PgVector 数据库连接字符串等全局依赖内容。
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    应用全局环境变量设置类。
    基于 Pydantic-Settings，支持自动按类型进行环境变量的读取和验证。
    """
    # 强制让系统自动从根目录下的 '.env' 文件抓取配置
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 服务网关及生命周期基本信息
    env: str = Field("local", alias="TAX_AGENT_ENV")
    log_level: str = Field("INFO", alias="TAX_AGENT_LOG_LEVEL")
    host: str = Field("0.0.0.0", alias="TAX_AGENT_HOST")
    port: int = Field(8011, alias="TAX_AGENT_PORT")

    # 旧系统后台的基础地址，便于第二期 P2 对其回调打通
    legacy_backend_base_url: str = "http://127.0.0.1:8001"

    # 大语言模型基础参数，默认连接通义千问 (qwen-plus)
    llm_model: str = "qwen-plus"
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_temperature: float = 0.3

    # 向量检索核心参数：设置知识嵌入转化模型和对应的 1536 常用向量维度
    embedding_model: str = "text-embedding-3-small"
    embedding_api_key: str = ""
    embedding_base_url: str = ""
    embedding_dimensions: int = 1536

    # 包含 PgVector 插件的 PostgreSQL 连接坐标和密码体系
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_user: str = "postgres"
    pg_password: str = ""
    pg_database: str = "agno"
    pg_knowledge_schema: str = "knowledge"

    # 特性开启与降级开关标记
    enable_real_llm: bool = False
    enable_real_rag: bool = False
    enable_langsmith: bool = False

    @property
    def postgres_url(self) -> str:
        """
        组合并提取基于 async psycopg2 (或同步) 的 PostgreSQL URI 连接字符串。
        """
        return (
            f"postgresql+psycopg://{self.pg_user}:{self.pg_password}"
            f"@{self.pg_host}:{self.pg_port}/{self.pg_database}"
        )


@lru_cache
def get_settings() -> Settings:
    """
    应用唯一单例全局配置。利用 LRU Cache 保障其只会被读取解析一次。
    """
    return Settings()
