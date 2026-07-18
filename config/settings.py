"""
SRE Bot - Configuration Management
Enterprise-grade settings with environment-based config
"""
import os
from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = Field(default="SRE Bot", description="Application name")
    APP_VERSION: str = Field(default="1.0.0", description="Application version")
    DEBUG: bool = Field(default=False, description="Debug mode")
    ENVIRONMENT: str = Field(default="production", description="Environment")
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str = Field(description="Telegram Bot Token from @BotFather")
    TELEGRAM_WEBHOOK_URL: Optional[str] = Field(default=None, description="Webhook URL for production")
    TELEGRAM_WEBHOOK_SECRET: Optional[str] = Field(default=None, description="Webhook secret")
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/srebot",
        description="PostgreSQL connection string"
    )
    DB_POOL_SIZE: int = Field(default=20, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=10, description="Database max overflow")
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis connection string")
    
    # AI API (User provided)
    AI_API_URL: str = Field(
        default="https://r-bots-free-apis.co08.art/api/v1/api/gptlogic",
        description="AI API endpoint"
    )
    AI_API_TIMEOUT: int = Field(default=30, description="AI API timeout in seconds")
    
    # Monitoring Engine
    MONITOR_WORKERS: int = Field(default=10, description="Number of monitoring workers")
    MONITOR_MAX_RETRIES: int = Field(default=3, description="Max retries for failed checks")
    MONITOR_RETRY_DELAY: int = Field(default=5, description="Retry delay in seconds")
    MONITOR_TIMEOUT: int = Field(default=30, description="Default monitor timeout")
    
    # Supported check intervals (seconds)
    CHECK_INTERVALS: List[int] = Field(
        default=[60, 300, 600, 1800, 3600, 21600, 86400],
        description="Available check intervals"
    )
    
    # Security
    SECRET_KEY: str = Field(default="change-me-in-production", description="Secret key for JWT")
    ENCRYPTION_KEY: Optional[str] = Field(default=None, description="Encryption key for sensitive data")
    
    # Notifications
    NOTIFICATION_COOLDOWN: int = Field(default=300, description="Notification cooldown in seconds")
    MAX_ALERTS_PER_HOUR: int = Field(default=50, description="Max alerts per hour per monitor")
    
    # Status Pages
    STATUS_PAGE_DOMAIN: Optional[str] = Field(default=None, description="Custom domain for status pages")
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, description="Rate limit per minute per user")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="json", description="Log format: json or text")
    
    @validator('DATABASE_URL', pre=True, always=True)
    def fix_database_url(cls, v):
        """Convert Railway's postgres:// to postgresql+asyncpg://"""
        if v and v.startswith('postgres://') and not v.startswith('postgresql+asyncpg://'):
            v = v.replace('postgres://', 'postgresql+asyncpg://', 1)
        elif v and v.startswith('postgresql://') and not v.startswith('postgresql+asyncpg://'):
            v = v.replace('postgresql://', 'postgresql+asyncpg://', 1)
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()

