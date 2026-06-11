from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: str = Field("local", alias="TAX_AGENT_ENV")
    log_level: str = Field("INFO", alias="TAX_AGENT_LOG_LEVEL")
    host: str = Field("0.0.0.0", alias="TAX_AGENT_HOST")
    port: int = Field(8011, alias="TAX_AGENT_PORT")

    legacy_backend_base_url: str = "http://127.0.0.1:8001"

    llm_model: str = "qwen-plus"
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_temperature: float = 0.3

    embedding_model: str = "text-embedding-3-small"
    embedding_api_key: str = ""
    embedding_base_url: str = ""
    embedding_dimensions: int = 1536

    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_user: str = "postgres"
    pg_password: str = ""
    pg_database: str = "agno"
    pg_knowledge_schema: str = "knowledge"

    enable_real_llm: bool = False
    enable_real_rag: bool = False
    enable_langsmith: bool = False

    @property
    def postgres_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.pg_user}:{self.pg_password}"
            f"@{self.pg_host}:{self.pg_port}/{self.pg_database}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
