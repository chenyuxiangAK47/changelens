"""
ChangeLens API v1 - Baseline Service
A microservice benchmark for studying change-induced performance regressions.
"""

import os
import time
import random
import logging
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="ChangeLens API v1", version="1.0.0")

# Database connection pool
db_pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None

# Configuration
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "changelens")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DOWNSTREAM_URL = os.getenv("DOWNSTREAM_URL", "http://downstream:8002")

# Fixed random seed for reproducibility
random.seed(42)


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


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    init_db()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    if db_pool:
        db_pool.closeall()


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/version")
async def version():
    """Version endpoint with regression flags."""
    return {
        "version": "1.0.0",
        "build": "v1-baseline",
        "regressions": {
            "cpu": False,
            "db": False,
            "downstream": False
        }
    }


class CheckoutRequest(BaseModel):
    user_id: str
    amount: float


@app.post("/checkout")
async def checkout(request: CheckoutRequest):
    """
    Checkout endpoint - processes an order.
    This is the baseline version without regressions.
    """
    start_time = time.time()
    order_id = f"ORD-{int(time.time() * 1000)}-{random.randint(1000, 9999)}"
    
    try:
        # Write order to database
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO orders (order_id, user_id, amount, status)
                    VALUES (%s, %s, %s, %s)
                """, (order_id, request.user_id, request.amount, "pending"))
                conn.commit()
        
        # Call downstream service
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                downstream_response = await client.get(
                    f"{DOWNSTREAM_URL}/process",
                    params={"order_id": order_id}
                )
                downstream_response.raise_for_status()
                downstream_data = downstream_response.json()
        except httpx.RequestError as e:
            logger.warning(f"Downstream service unavailable: {e}")
            downstream_data = {"status": "skipped"}
        
        # Update order status
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE orders SET status = %s WHERE order_id = %s
                """, ("completed", order_id))
                conn.commit()
        
        latency_ms = (time.time() - start_time) * 1000
        
        return {
            "order_id": order_id,
            "status": "completed",
            "latency_ms": round(latency_ms, 2),
            "downstream": downstream_data
        }
    
    except Exception as e:
        logger.error(f"Checkout failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
