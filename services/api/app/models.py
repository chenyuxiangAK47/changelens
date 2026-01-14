"""
数据模型定义
Data Model Definitions
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class Item(BaseModel):
    """数据项模型 / Item Model"""
    id: Optional[int] = None
    name: str
    value: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ProcessRequest(BaseModel):
    """处理请求模型 / Process Request Model"""
    task_id: str
    data: dict


class ProcessResponse(BaseModel):
    """处理响应模型 / Process Response Model"""
    task_id: str
    status: str
    message: str


class MetricsResponse(BaseModel):
    """指标响应模型 / Metrics Response Model"""
    timestamp: datetime
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    error_rate: float
    request_count: int
    deployment_phase: str
    regression_type: Optional[str] = None


class RegressionRequest(BaseModel):
    """回归注入请求模型 / Regression Injection Request Model"""
    enabled: bool
    intensity: Optional[int] = None  # 强度参数（可选）
