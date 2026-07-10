from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str
    APP_VERSION: str

    UPLOAD_DIR: str
    GENERATED_DIR: str
    TEMPLATE_DIR: str

    OPENROUTER_API_KEY: str           # no default — fail fast at startup if missing
    OPENROUTER_MODEL: str

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True
    )


settings = Settings()