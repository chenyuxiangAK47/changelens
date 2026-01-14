"""
回归注入器模块
Regression Injector Module

实现三种类型的回归注入：
1. CPU回归：额外计算、锁竞争
2. 数据库回归：慢查询、缺失索引
3. 下游依赖回归：模拟外部调用变慢/超时
"""
import asyncio
import time
import random
from typing import Optional
from app.config import settings


class RegressionInjector:
    """回归注入器类 / Regression Injector Class"""
    
    def __init__(self):
        self.cpu_enabled = settings.regression_cpu_enabled
        self.db_enabled = settings.regression_db_enabled
        self.dependency_enabled = settings.regression_dependency_enabled
    
    async def inject_cpu_regression(self, intensity: Optional[int] = None) -> None:
        """
        注入CPU回归：通过额外计算和锁竞争模拟CPU瓶颈
        Inject CPU regression: Simulate CPU bottleneck through extra computation and lock contention
        """
        if not self.cpu_enabled:
            return
        
        intensity = intensity or settings.cpu_regression_intensity
        
        # 额外计算循环 / Extra computation loop
        result = 0
        for i in range(intensity):
            result += i * i
            # 模拟锁竞争 / Simulate lock contention
            if i % 100 == 0:
                await asyncio.sleep(0.001)  # 模拟锁等待 / Simulate lock wait
        
        # 确保结果被使用（防止编译器优化）
        # Ensure result is used (prevent compiler optimization)
        _ = result
    
    async def inject_db_regression(self, query_complexity: Optional[int] = None) -> None:
        """
        注入数据库回归：通过慢查询模拟数据库瓶颈
        Inject DB regression: Simulate database bottleneck through slow queries
        """
        if not self.db_enabled:
            return
        
        complexity = query_complexity or settings.db_regression_intensity
        
        # 模拟慢查询：执行复杂计算
        # Simulate slow query: Execute complex computation
        result = 0
        for i in range(complexity * 1000):
            result += i
            # 模拟数据库I/O延迟
            # Simulate database I/O delay
            if i % 10000 == 0:
                await asyncio.sleep(0.01)
        
        _ = result
    
    async def inject_dependency_regression(self, delay_ms: Optional[int] = None) -> None:
        """
        注入下游依赖回归：模拟外部服务调用变慢或超时
        Inject dependency regression: Simulate slow or timeout external service calls
        """
        if not self.dependency_enabled:
            return
        
        delay = delay_ms or settings.dependency_regression_delay_ms
        
        # 模拟网络延迟
        # Simulate network delay
        await asyncio.sleep(delay / 1000.0)
        
        # 随机模拟超时（5%概率）
        # Randomly simulate timeout (5% probability)
        if random.random() < 0.05:
            raise TimeoutError("下游依赖服务超时 / Downstream dependency service timeout")
    
    async def inject_all_regressions(self) -> None:
        """
        注入所有启用的回归类型
        Inject all enabled regression types
        """
        tasks = []
        
        if self.cpu_enabled:
            tasks.append(self.inject_cpu_regression())
        if self.db_enabled:
            tasks.append(self.inject_db_regression())
        if self.dependency_enabled:
            tasks.append(self.inject_dependency_regression())
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def set_cpu_regression(self, enabled: bool) -> None:
        """设置CPU回归状态 / Set CPU regression state"""
        self.cpu_enabled = enabled
    
    def set_db_regression(self, enabled: bool) -> None:
        """设置数据库回归状态 / Set DB regression state"""
        self.db_enabled = enabled
    
    def set_dependency_regression(self, enabled: bool) -> None:
        """设置依赖回归状态 / Set dependency regression state"""
        self.dependency_enabled = enabled


# 全局回归注入器实例 / Global Regression Injector Instance
regression_injector = RegressionInjector()
