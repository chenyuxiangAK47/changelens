"""
ChangeLens Downstream Service
Simulates external dependency with configurable latency and error rates.
"""

import os
import time
import random
import logging
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="ChangeLens Downstream Service", version="1.0.0")

# Configuration
DOWNSTREAM_LATENCY_MS = int(os.getenv("DOWNSTREAM_LATENCY_MS", "50"))
DOWNSTREAM_SPIKE_PROB = float(os.getenv("DOWNSTREAM_SPIKE_PROB", "0.0"))
DOWNSTREAM_SPIKE_MS = int(os.getenv("DOWNSTREAM_SPIKE_MS", "200"))
DOWNSTREAM_ERROR_PROB = float(os.getenv("DOWNSTREAM_ERROR_PROB", "0.0"))

# When regression is enabled via API v2, use higher values
# These are overridden when regression=1 is passed in the request

# Fixed random seed for reproducibility
random.seed(42)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "config": {
            "base_latency_ms": DOWNSTREAM_LATENCY_MS,
            "spike_prob": DOWNSTREAM_SPIKE_PROB,
            "spike_ms": DOWNSTREAM_SPIKE_MS,
            "error_prob": DOWNSTREAM_ERROR_PROB
        }
    }


@app.get("/process")
async def process(order_id: str = Query(...), regression: str = Query("0")):
    """
    Process endpoint - simulates external dependency processing.
    
    Args:
        order_id: Order identifier
        regression: "1" to enable regression mode (increased latency/errors)
    """
    regression_enabled = regression == "1"
    
    # Base latency
    latency_ms = DOWNSTREAM_LATENCY_MS
    
    # Regression: Add latency spikes and errors
    if regression_enabled:
        # Use higher spike probability and error rate when regression is enabled
        spike_prob = max(DOWNSTREAM_SPIKE_PROB, 0.1)  # At least 10% spike probability
        error_prob = max(DOWNSTREAM_ERROR_PROB, 0.15)  # At least 15% error probability
        
        if random.random() < spike_prob:
            latency_ms += DOWNSTREAM_SPIKE_MS
            logger.info(f"Latency spike for order {order_id}: +{DOWNSTREAM_SPIKE_MS}ms")
        
        # Additional base latency increase
        latency_ms += random.randint(20, 50)
        
        # Regression: Simulate errors BEFORE processing
        if random.random() < error_prob:
            logger.warning(f"Downstream error for order {order_id}")
            raise HTTPException(status_code=503, detail="Downstream service temporarily unavailable")
    
    # Simulate processing time
    time.sleep(latency_ms / 1000.0)
    
    return {
        "order_id": order_id,
        "status": "processed",
        "latency_ms": latency_ms,
        "timestamp": time.time()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
