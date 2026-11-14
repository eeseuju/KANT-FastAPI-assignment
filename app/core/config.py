from pydantic_settings import BaseSettings, SettingsConfigDict

# 환경변수에서 읽어 오는 설정
class Settings(BaseSettings):
    database_url: str
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
