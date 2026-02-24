from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    data_file: str = "app/data/documents.json"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
