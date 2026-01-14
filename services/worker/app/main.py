"""
ChangeLens Worker 服务
ChangeLens Worker Service

处理来自API服务的异步任务
"""
import os
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import redis

from app.tasks import process_task, process_long_running_task

# Redis连接 / Redis connection
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(redis_url, decode_responses=True)

app = FastAPI(
    title="ChangeLens Worker",
    description="Background Task Processing Service",
    version="1.0.0"
)


class TaskRequest(BaseModel):
    """任务请求模型 / Task Request Model"""
    task_id: str
    data: Dict[str, Any]


class TaskResponse(BaseModel):
    """任务响应模型 / Task Response Model"""
    task_id: str
    status: str
    message: str


@app.get("/health")
async def health_check():
    """健康检查端点 / Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "changelens-worker"
    }


@app.post("/api/tasks", response_model=TaskResponse)
async def submit_task(request: TaskRequest):
    """
    提交任务端点
    Submit task endpoint
    
    接收来自API服务的任务，异步处理并存储结果
    """
    try:
        # 处理任务（根据任务类型选择不同的处理函数）
        # Process task (select different processing function based on task type)
        if request.data.get("long_running", False):
            result = await process_long_running_task(request.task_id, request.data)
        else:
            result = await process_task(request.task_id, request.data)
        
        # 将结果存储到Redis（可选，用于结果查询）
        # Store result in Redis (optional, for result querying)
        redis_client.setex(
            f"task:{request.task_id}",
            3600,  # 1小时过期 / 1 hour expiration
            str(result)
        )
        
        return TaskResponse(
            task_id=request.task_id,
            status="completed",
            message="任务处理完成 / Task processed successfully"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"任务处理失败 / Task processing failed: {str(e)}"
        )


@app.get("/api/tasks/{task_id}")
async def get_task_result(task_id: str):
    """
    获取任务结果端点
    Get task result endpoint
    """
    result = redis_client.get(f"task:{task_id}")
    if result is None:
        raise HTTPException(status_code=404, detail="任务未找到 / Task not found")
    
    return {"task_id": task_id, "result": result}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
