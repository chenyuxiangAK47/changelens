"""
ChangeLens API 主服务
ChangeLens API Main Service

提供RESTful API端点，支持数据查询、任务处理、回归注入和指标监控
"""
import time
import asyncio
from datetime import datetime
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
import asyncpg
import httpx
from redis import Redis

from app.config import settings
from app.models import Item, ProcessRequest, ProcessResponse, MetricsResponse, RegressionRequest
from app.regression_injector import regression_injector

# 全局变量用于存储指标
# Global variables for storing metrics
metrics_store = {
    "latencies": [],  # 存储所有请求延迟 / Store all request latencies
    "errors": 0,  # 错误计数 / Error count
    "requests": 0,  # 请求计数 / Request count
    "start_time": time.time()
}

# 数据库连接池 / Database connection pool
db_pool: Optional[asyncpg.Pool] = None
redis_client: Optional[Redis] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理 / Application lifecycle management"""
    global db_pool, redis_client
    
    # 启动时初始化连接 / Initialize connections on startup
    try:
        # 初始化数据库连接池
        # Initialize database connection pool
        db_pool = await asyncpg.create_pool(
            settings.database_url.replace("postgresql+asyncpg://", "postgresql://"),
            min_size=5,
            max_size=20
        )
        
        # 初始化Redis连接
        # Initialize Redis connection
        redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
        
        print("✅ 数据库和Redis连接已建立 / Database and Redis connections established")
    except Exception as e:
        print(f"❌ 连接初始化失败 / Connection initialization failed: {e}")
    
    yield
    
    # 关闭时清理连接 / Cleanup connections on shutdown
    if db_pool:
        await db_pool.close()
    if redis_client:
        redis_client.close()
    print("🔌 连接已关闭 / Connections closed")


app = FastAPI(
    title="ChangeLens API",
    description="Change-Induced Performance Regression & Safe Release Benchmark API",
    version="1.0.0",
    lifespan=lifespan
)


async def get_db():
    """获取数据库连接 / Get database connection"""
    if db_pool is None:
        raise HTTPException(status_code=503, detail="数据库连接不可用 / Database connection unavailable")
    return db_pool


@app.get("/health")
async def health_check():
    """健康检查端点 / Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "changelens-api"
    }


@app.get("/api/data", response_model=List[Item])
async def get_data(db=Depends(get_db)):
    """
    获取数据端点（会触发数据库查询）
    Get data endpoint (triggers database query)
    """
    start_time = time.time()
    
    try:
        # 注入数据库回归（如果启用）
        # Inject DB regression (if enabled)
        await regression_injector.inject_db_regression()
        
        # 执行数据库查询
        # Execute database query
        async with db.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, name, value, created_at, updated_at FROM items ORDER BY created_at DESC LIMIT 100"
            )
        
        items = [
            Item(
                id=row["id"],
                name=row["name"],
                value=row["value"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
            for row in rows
        ]
        
        # 记录延迟 / Record latency
        latency_ms = (time.time() - start_time) * 1000
        metrics_store["latencies"].append(latency_ms)
        metrics_store["requests"] += 1
        
        return items
    
    except Exception as e:
        metrics_store["errors"] += 1
        metrics_store["requests"] += 1
        raise HTTPException(status_code=500, detail=f"查询失败 / Query failed: {str(e)}")


@app.post("/api/process", response_model=ProcessResponse)
async def process_task(request: ProcessRequest):
    """
    处理任务端点（提交异步任务到Worker）
    Process task endpoint (submit async task to Worker)
    """
    start_time = time.time()
    
    try:
        # 注入CPU回归（如果启用）
        # Inject CPU regression (if enabled)
        await regression_injector.inject_cpu_regression()
        
        # 注入依赖回归（如果启用）
        # Inject dependency regression (if enabled)
        try:
            await regression_injector.inject_dependency_regression()
        except TimeoutError:
            # 依赖超时，记录错误但继续处理
            # Dependency timeout, record error but continue processing
            metrics_store["errors"] += 1
        
        # 提交任务到Worker服务
        # Submit task to Worker service
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.worker_url}/api/tasks",
                json={"task_id": request.task_id, "data": request.data},
                timeout=5.0
            )
            response.raise_for_status()
        
        # 记录延迟 / Record latency
        latency_ms = (time.time() - start_time) * 1000
        metrics_store["latencies"].append(latency_ms)
        metrics_store["requests"] += 1
        
        return ProcessResponse(
            task_id=request.task_id,
            status="submitted",
            message="任务已提交 / Task submitted"
        )
    
    except httpx.TimeoutException:
        metrics_store["errors"] += 1
        metrics_store["requests"] += 1
        raise HTTPException(status_code=504, detail="Worker服务超时 / Worker service timeout")
    except Exception as e:
        metrics_store["errors"] += 1
        metrics_store["requests"] += 1
        raise HTTPException(status_code=500, detail=f"处理失败 / Processing failed: {str(e)}")


@app.get("/api/metrics", response_model=MetricsResponse)
async def get_metrics():
    """
    获取当前性能指标
    Get current performance metrics
    """
    latencies = metrics_store["latencies"]
    
    if not latencies:
        return MetricsResponse(
            timestamp=datetime.now(),
            p50_latency_ms=0.0,
            p95_latency_ms=0.0,
            p99_latency_ms=0.0,
            error_rate=0.0,
            request_count=0,
            deployment_phase=settings.deployment_phase,
            regression_type=None
        )
    
    # 计算百分位数 / Calculate percentiles
    sorted_latencies = sorted(latencies)
    n = len(sorted_latencies)
    
    p50 = sorted_latencies[int(n * 0.50)] if n > 0 else 0.0
    p95 = sorted_latencies[int(n * 0.95)] if n > 0 else 0.0
    p99 = sorted_latencies[int(n * 0.99)] if n > 0 else 0.0
    
    # 计算错误率 / Calculate error rate
    total_requests = metrics_store["requests"]
    error_rate = (metrics_store["errors"] / total_requests * 100) if total_requests > 0 else 0.0
    
    # 确定回归类型 / Determine regression type
    regression_type = None
    if regression_injector.cpu_enabled:
        regression_type = "CPU"
    elif regression_injector.db_enabled:
        regression_type = "DB"
    elif regression_injector.dependency_enabled:
        regression_type = "Dependency"
    
    return MetricsResponse(
        timestamp=datetime.now(),
        p50_latency_ms=round(p50, 2),
        p95_latency_ms=round(p95, 2),
        p99_latency_ms=round(p99, 2),
        error_rate=round(error_rate, 2),
        request_count=total_requests,
        deployment_phase=settings.deployment_phase,
        regression_type=regression_type
    )


@app.post("/api/regression/{regression_type}")
async def inject_regression(regression_type: str, request: RegressionRequest):
    """
    注入回归端点
    Inject regression endpoint
    
    支持的回归类型 / Supported regression types:
    - cpu: CPU回归
    - db: 数据库回归
    - dependency: 下游依赖回归
    """
    if regression_type == "cpu":
        regression_injector.set_cpu_regression(request.enabled)
        if request.intensity:
            settings.cpu_regression_intensity = request.intensity
    elif regression_type == "db":
        regression_injector.set_db_regression(request.enabled)
        if request.intensity:
            settings.db_regression_intensity = request.intensity
    elif regression_type == "dependency":
        regression_injector.set_dependency_regression(request.enabled)
        if request.delay_ms:
            settings.dependency_regression_delay_ms = request.delay_ms
    else:
        raise HTTPException(status_code=400, detail=f"不支持的回归类型 / Unsupported regression type: {regression_type}")
    
    return {
        "status": "success",
        "regression_type": regression_type,
        "enabled": request.enabled,
        "message": f"回归注入已{'启用' if request.enabled else '禁用'} / Regression injection {'enabled' if request.enabled else 'disabled'}"
    }


@app.post("/api/metrics/reset")
async def reset_metrics():
    """重置指标 / Reset metrics"""
    global metrics_store
    metrics_store = {
        "latencies": [],
        "errors": 0,
        "requests": 0,
        "start_time": time.time()
    }
    return {"status": "success", "message": "指标已重置 / Metrics reset"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
