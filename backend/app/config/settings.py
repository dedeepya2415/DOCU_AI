from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str
    APP_VERSION: str

    UPLOAD_DIR: str
    GENERATED_DIR: str
    TEMPLATE_DIR: str

    OPENAI_API_KEY: str
    OPENAI_MODEL: str

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True
    )


settings = Settings()