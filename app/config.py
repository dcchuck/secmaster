from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://secmaster:secmaster@localhost:5432/secmaster"
    test_database_url: str = "postgresql://secmaster_test:secmaster_test@localhost:5433/secmaster_test"
    clerk_secret_key: str = ""
    clerk_jwks_url: str = ""
    rate_limit_free: str = "60/minute"
    rate_limit_paid: str = "300/minute"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
