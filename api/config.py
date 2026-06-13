from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_secret_key: str = "change-me"
    log_level: str = "INFO"

    database_url: str
    anthropic_api_key: str = ""
    fhir_server_url: str = "http://localhost:8080/fhir"


settings = Settings()
