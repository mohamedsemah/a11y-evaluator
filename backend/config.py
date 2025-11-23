"""
Application configuration using Pydantic Settings
"""
from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with validation"""
    
    # Application
    APP_NAME: str = "Infotainment Accessibility Analyzer"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: str = "CHANGE_THIS_IN_PRODUCTION_TO_RANDOM_SECRET_KEY_MIN_32_CHARS"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    AUTH_REQUIRED: bool = False  # Set to True to enable authentication
    API_KEY: str = ""  # API key for simple authentication
    
    # File upload limits
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50 MB per file
    MAX_TOTAL_SIZE: int = 500 * 1024 * 1024  # 500 MB per session
    MAX_FILES_PER_SESSION: int = 100
    
    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60  # requests per minute per IP
    RATE_LIMIT_PER_HOUR: int = 1000  # requests per hour per IP
    
    # Database
    DATABASE_URL: str = "sqlite:///./accessibility_analyzer.db"
    
    # LLM API Keys (loaded from environment)
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    REPLICATE_API_TOKEN: str = ""
    
    # Session
    SESSION_EXPIRY_HOURS: int = 24
    
    # Paths
    TEMP_SESSIONS_DIR: str = "temp_sessions"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "accessibility_analyzer.log"
    LOG_JSON_FORMAT: bool = True
    
    # Error Tracking (Sentry)
    SENTRY_DSN: str = ""
    SENTRY_ENVIRONMENT: str = "development"
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    
    # Caching (Redis)
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_ENABLED: bool = True
    CACHE_TTL_SECONDS: int = 3600  # 1 hour default
    
    # Background Jobs (Celery)
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    CELERY_ENABLED: bool = False  # Set to True to enable Celery
    
    # File Cleanup
    CLEANUP_INTERVAL_SECONDS: int = 3600  # 1 hour
    MAX_FILE_AGE_HOURS: int = 48
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Get allowed origins as a list"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes"""
        return self.MAX_FILE_SIZE
    
    @property
    def max_total_size_bytes(self) -> int:
        """Get max total size in bytes"""
        return self.MAX_TOTAL_SIZE


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

