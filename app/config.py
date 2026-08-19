from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "cockroachdb://root@localhost:26257/defaultdb?sslmode=disable"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7
    cors_origins: str = "http://localhost:3000"
    cookie_secure: bool = False
    max_upload_bytes: int = 1_000_000

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    class Config:
        env_file = ".env"


settings = Settings()
