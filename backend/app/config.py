"""
Presto Backtesting API 설정
백테스팅 전용 - 최소 설정
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """백테스팅 API 설정"""
    app_name: str = "Presto Backtesting API"
    debug: bool = True
    version: str = "1.0.0"
    
    class Config:
        env_file = ".env"


settings = Settings()
