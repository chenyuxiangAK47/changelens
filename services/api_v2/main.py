"""
ChangeLens API v2 - Service with Controlled Regressions
A microservice benchmark for studying change-induced performance regressions.
"""

import os
import sys
import time
import random
import logging
import threading
from datetime import datetime
from typing import Optional
from contextlib import contextmanager

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import httpx

# Configure logging with more detail
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="ChangeLens API v2", version="2.0.0")

# Add global exception handler to catch all exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    import traceback
    tb_str = traceback.format_exc()
    error_msg = f"Global exception handler caught: {type(exc).__name__}: {exc}\nTraceback:\n{tb_str}"
    logger.error(error_msg)
    sys.stderr.write(error_msg + "\n")
    sys.stderr.flush()
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "traceback": tb_str}
    )

# Database connection pool
db_pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None

# Regression toggles (controlled via environment variables)
REG_CPU = os.getenv("REG_CPU", "0") == "1"
REG_DB = os.getenv("REG_DB", "0") == "1"
REG_DOWNSTREAM = os.getenv("REG_DOWNSTREAM", "0") == "1"

# Configuration
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "changelens")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DOWNSTREAM_URL = os.getenv("DOWNSTREAM_URL", "http://downstream:8002")

# Fixed random seed for reproducibility
random.seed(42)

# CPU regression: lock for contention simulation
cpu_lock = threading.Lock()


def init_db():
    """Initialize database connection pool."""
    global db_pool
    try:
        db_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        logger.info("Database connection pool initialized")
        
        # Create tables if they don't exist
        with db_pool.getconn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS orders (
                        id SERIAL PRIMARY KEY,
                        order_id VARCHAR(100) UNIQUE NOT NULL,
                        user_id VARCHAR(100) NOT NULL,
                        amount DECIMAL(10, 2) NOT NULL,
                        status VARCHAR(50) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
                    CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);
                """)
                conn.commit()
        logger.info("Database tables initialized")
        
        # DB Regression: Drop index if regression is enabled
        if REG_DB:
            logger.warning("DB regression enabled: missing index on user_id")
            with db_pool.getconn() as conn:
                with conn.cursor() as cur:
                    try:
                        cur.execute("DROP INDEX IF EXISTS idx_orders_user_id")
                        conn.commit()
                        logger.info("Dropped index idx_orders_user_id for regression")
                    except Exception as e:
                        logger.error(f"Failed to drop index: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = db_pool.getconn()
    try:
        yield conn
    finally:
        db_pool.putconn(conn)


def simulate_cpu_regression():
    """Simulate CPU regression through lock contention and busy-wait."""
    if not REG_CPU:
        return
    
    # Acquire lock and hold it for a while (simulating contention)
    with cpu_lock:
        # Busy-wait to simulate CPU-bound work
        start = time.time()
        while time.time() - start < 0.05:  # 50ms of CPU work
            _ = sum(range(1000))
        
        # Additional lock contention
        time.sleep(0.02)


def simulate_db_regression(cur, user_id: str):
    """Simulate DB regression through inefficient query."""
    if not REG_DB:
        return
    
    # Deliberately slow query: full table scan without index
    # This is already achieved by dropping the index, but we add extra work
    # Use at least 3 characters for LIKE pattern, or use first char if shorter
    if len(user_id) >= 3:
        pattern = user_id[:3] + '%'
    elif len(user_id) > 0:
        pattern = user_id[:1] + '%'
    else:
        pattern = '%'
    
    try:
        logger.debug(f"Running DB regression query with pattern: {pattern}")
        cur.execute("""
            SELECT COUNT(*) FROM orders 
            WHERE user_id LIKE %s
        """, (pattern,))
        result = cur.fetchone()
        # COUNT(*) should always return a result tuple like (0,) or (5,)
        # Just fetch it, don't access any indices - this is just for simulation
        if result:
            logger.debug(f"DB regression query result: {result}")
        else:
            logger.warning("DB regression query returned None")
    except Exception as e:
        logger.warning(f"DB regression query failed: {e}")
        import traceback
        logger.warning(f"Traceback: {traceback.format_exc()}")
        # Don't fail the request if regression simulation fails


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    init_db()
    logger.info(f"API v2 started with regressions: CPU={REG_CPU}, DB={REG_DB}, Downstream={REG_DOWNSTREAM}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    if db_pool:
        db_pool.closeall()


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.0.0"}


@app.get("/version")
async def version():
    """Version endpoint with regression flags."""
    return {
        "version": "2.0.0",
        "build": "v2-with-regressions",
        "regressions": {
            "cpu": REG_CPU,
            "db": REG_DB,
            "downstream": REG_DOWNSTREAM
        }
    }


class CheckoutRequest(BaseModel):
    user_id: str
    amount: float


@app.post("/checkout")
async def checkout(request: CheckoutRequest):
    """
    Checkout endpoint - processes an order.
    Version 2 includes controlled regressions.
    """
    try:
        start_time = time.time()
        logger.info(f"=== CHECKOUT START ===")
        logger.info(f"Request received: user_id={request.user_id}, amount={request.amount}")
        order_id = f"ORD-{int(time.time() * 1000)}-{random.randint(1000, 9999)}"
        logger.info(f"Generated order_id: {order_id}")
    except Exception as e:
        logger.error(f"Error in checkout initialization: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise
    
    try:
        logger.info(f"Processing checkout for user {request.user_id}, amount {request.amount}")
        # CPU Regression: Simulate CPU-bound work
        simulate_cpu_regression()
        logger.info("CPU regression simulation completed")
        
        # Write order to database
        logger.info("Writing order to database")
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # DB Regression: Run inefficient query
                logger.info("Running DB regression query")
                simulate_db_regression(cur, request.user_id)
                logger.info("DB regression query completed")
                
                logger.info(f"Inserting order {order_id}")
                cur.execute("""
                    INSERT INTO orders (order_id, user_id, amount, status)
                    VALUES (%s, %s, %s, %s)
                """, (order_id, request.user_id, request.amount, "pending"))
                conn.commit()
                logger.info("Order inserted successfully")
        
        # Call downstream service
        logger.info("Calling downstream service")
        downstream_error = False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                downstream_response = await client.get(
                    f"{DOWNSTREAM_URL}/process",
                    params={"order_id": order_id, "regression": "1" if REG_DOWNSTREAM else "0"}
                )
                
                # Downstream regression: Force errors if enabled
                if REG_DOWNSTREAM and random.random() < 0.15:  # 15% error rate
                    downstream_error = True
                    raise HTTPException(status_code=503, detail="Downstream service error")
                
                downstream_response.raise_for_status()
                downstream_data = downstream_response.json()
                logger.info(f"Downstream service responded: {downstream_data}")
        except (httpx.RequestError, HTTPException) as e:
            if REG_DOWNSTREAM and downstream_error:
                logger.warning(f"Downstream regression: forced error for order {order_id}")
                raise HTTPException(status_code=503, detail="Downstream service unavailable")
            logger.warning(f"Downstream service unavailable: {e}")
            downstream_data = {"status": "skipped"}
        
        # Update order status
        logger.info("Updating order status")
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE orders SET status = %s WHERE order_id = %s
                """, ("completed", order_id))
                rows_affected = cur.rowcount
                if rows_affected == 0:
                    logger.warning(f"No rows updated for order {order_id}")
                conn.commit()
                logger.info(f"Order status updated, rows affected: {rows_affected}")
        
        latency_ms = (time.time() - start_time) * 1000
        logger.info(f"Checkout completed successfully, latency: {latency_ms}ms")
        
        return {
            "order_id": order_id,
            "status": "completed",
            "latency_ms": round(latency_ms, 2),
            "downstream": downstream_data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        tb_str = traceback.format_exc()
        # Force output to both logger and stderr
        error_msg = f"Checkout failed: {e}\nTraceback:\n{tb_str}"
        logger.error(error_msg)
        sys.stderr.write(error_msg + "\n")
        sys.stderr.flush()
        # Also print to stdout in case stderr is buffered
        print(error_msg, file=sys.stdout)
        sys.stdout.flush()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
