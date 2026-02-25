import logging

from pydantic_settings import BaseSettings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


class Settings(BaseSettings):
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    db_path: str = "ferrofluids.db"
    concurrency: int = 15

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
