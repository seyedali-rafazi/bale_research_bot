import os
from typing import Optional
from dotenv import load_dotenv
import redis.asyncio as redis

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client: Optional[redis.Redis] = None

async def init_redis():
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
    return redis_client

async def close_redis():
    global redis_client
    if redis_client is not None:
        await redis_client.close()
        redis_client = None
