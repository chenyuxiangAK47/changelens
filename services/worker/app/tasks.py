"""
任务处理模块
Task Processing Module

定义后台任务的处理逻辑
"""
import asyncio
import time
from typing import Dict, Any


async def process_task(task_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    处理任务
    Process task
    
    模拟后台任务处理（数据处理、外部调用等）
    Simulate background task processing (data processing, external calls, etc.)
    """
    # 模拟任务处理时间（100-500ms）
    # Simulate task processing time (100-500ms)
    processing_time = 0.1 + (hash(task_id) % 400) / 1000.0
    await asyncio.sleep(processing_time)
    
    # 模拟数据处理
    # Simulate data processing
    result = {
        "task_id": task_id,
        "status": "completed",
        "processed_data": {k: str(v).upper() for k, v in data.items()},
        "processing_time_ms": processing_time * 1000,
        "timestamp": time.time()
    }
    
    return result


async def process_long_running_task(task_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    处理长时间运行的任务
    Process long-running task
    
    模拟需要更长时间处理的任务（1-5秒）
    Simulate tasks that require longer processing time (1-5 seconds)
    """
    processing_time = 1.0 + (hash(task_id) % 4000) / 1000.0
    await asyncio.sleep(processing_time)
    
    result = {
        "task_id": task_id,
        "status": "completed",
        "processed_data": data,
        "processing_time_ms": processing_time * 1000,
        "timestamp": time.time()
    }
    
    return result
