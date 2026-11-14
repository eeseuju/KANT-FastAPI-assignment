from pydantic_settings import BaseSettings, SettingsConfigDict


# 환경변수에서 읽어 오는 설정
class Settings(BaseSettings):
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = 'HS256'
    access_token_expire_minutes: int = 30
    # 브라우저에서 이 API를 부르도록 허용할 주소들 (쉼표로 구분)
    cors_origins: str = 'http://localhost:3000,http://localhost:5173,http://127.0.0.1:5500'
    cache_ttl_seconds: int = 30  # 글 목록·상세 캐시 수명(초). 0이면 캐시를 끈다.
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    @property
    # 쉼표로 적은 주소들을 목록으로 변환
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(',') if o.strip()]


settings = Settings()
