import time
import logging
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from redis.asyncio import Redis

from app.config import settings
from app.database import get_redis_client
from app.rate_limiter import is_rate_limited
from app.llm_client import stream_llm_response

# 1. Setup structured logging format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("gateway")

app = FastAPI(title="Guardrailed LLM Gateway")

# 2. Define the incoming request body shape
class ChatRequest(BaseModel):
    user_id: str
    message: str

# REQUIREMENT 5: Liveness Endpoint (No dependencies)
@app.get("/health")
async def health():
    return {"status": "healthy"}

# REQUIREMENT 5: Readiness Endpoint (Checks Redis dependency)
@app.get("/ready", status_code=status.HTTP_200_OK)
async def ready(redis_client: Redis = Depends(get_redis_client)):
    try:
        await redis_client.ping()
        return {"status": "ready", "redis": "connected"}
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready: Redis connection failed"
        )

# REQUIREMENT 1: Streaming Chat Endpoint
@app.post("/chat")
async def chat_endpoint(
    request: ChatRequest, 
    redis_client: Redis = Depends(get_redis_client)
):
    start_time = time.time()
    throttled = False
    total_tokens_estimated = 0

    # A. Check Budget / Rate Limit
    throttled = await is_rate_limited(redis_client, request.user_id)
    
    if throttled:
        # REQUIREMENT 2: Return HTTP 429 with clear JSON error if over budget
        latency_ms = int((time.time() - start_time) * 1000)
        # REQUIREMENT 6: Log metrics even when throttled
        logger.info(
            f"METRICS | user_id={request.user_id} | latency={latency_ms}ms | "
            f"tokens=0 | throttled=True"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "Rate limit exceeded", "message": "You have consumed your daily budget of 20 requests."}
        )

    # B. Define a wrapper function to stream and track tokens simultaneously
    async def log_and_stream_generator():
        nonlocal total_tokens_estimated
        try:
            async for chunk in stream_llm_response(request.message):
                # A crude but fast industry heuristic: 1 word ~ 1.3 tokens
                words_in_chunk = len(chunk.split())
                total_tokens_estimated += max(1, int(words_in_chunk * 1.3))
                
                # Send the chunk back in Server-Sent Events (SSE) formatting
                yield f"data: {chunk}\n\n"
        finally:
            # C. REQUIREMENT 6: When streaming ends, finalize latency and log metrics
            latency_ms = int((time.time() - start_time) * 1000)
            logger.info(
                f"METRICS | user_id={request.user_id} | latency={latency_ms}ms | "
                f"tokens={total_tokens_estimated} | throttled=False"
            )

    # Return the stream directly to the user's client
    return StreamingResponse(log_and_stream_generator(), media_type="text/event-stream")