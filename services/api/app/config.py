"""
配置管理模块
Configuration Management Module
"""
import os
from typing import Optional


class Settings:
    """应用配置 / Application Settings"""
    
    def __init__(self):
        # 数据库配置 / Database Configuration
        self.database_url: str = os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://changelens:changelens123@localhost:5432/changelens"
        )
        
        # Redis配置 / Redis Configuration
        self.redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        # Worker服务URL / Worker Service URL
        self.worker_url: str = os.getenv("WORKER_URL", "http://localhost:8001")
        
        # 回归注入配置 / Regression Injection Configuration
        self.regression_cpu_enabled: bool = os.getenv("REGRESSION_CPU_ENABLED", "false").lower() == "true"
        self.regression_db_enabled: bool = os.getenv("REGRESSION_DB_ENABLED", "false").lower() == "true"
        self.regression_dependency_enabled: bool = os.getenv("REGRESSION_DEPENDENCY_ENABLED", "false").lower() == "true"
        
        # 回归强度配置 / Regression Intensity Configuration
        self.cpu_regression_intensity: int = int(os.getenv("CPU_REGRESSION_INTENSITY", "1000"))  # 循环次数
        self.db_regression_intensity: int = int(os.getenv("DB_REGRESSION_INTENSITY", "100"))  # 慢查询倍数
        self.dependency_regression_delay_ms: int = int(os.getenv("DEPENDENCY_REGRESSION_DELAY_MS", "500"))  # 延迟毫秒
        
        # 部署阶段 / Deployment Phase
        self.deployment_phase: str = os.getenv("DEPLOYMENT_PHASE", "baseline")  # baseline, blue-green, canary


# 全局配置实例 / Global Settings Instance
settings = Settings()
