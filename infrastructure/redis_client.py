"""
Redis Infrastructure
Caching, rate limiting, and task queue backend
"""
import json
import redis.asyncio as redis
from typing import Optional, Any
from datetime import timedelta

from config import settings


class RedisClient:
    """Async Redis client wrapper"""
    
    def __init__(self):
        self._client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Initialize Redis connection"""
        self._client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True
        )
    
    async def disconnect(self):
        """Close Redis connection"""
        if self._client:
            await self._client.close()
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        if not self._client:
            return None
        return await self._client.get(key)
    
    async def set(self, key: str, value: str, expire: Optional[int] = None):
        """Set value with optional expiration"""
        if not self._client:
            return
        await self._client.set(key, value, ex=expire)
    
    async def delete(self, key: str):
        """Delete key"""
        if not self._client:
            return
        await self._client.delete(key)
    
    async def get_json(self, key: str) -> Optional[Any]:
        """Get and parse JSON value"""
        value = await self.get(key)
        if value:
            return json.loads(value)
        return None
    
    async def set_json(self, key: str, value: Any, expire: Optional[int] = None):
        """Set JSON value"""
        await self.set(key, json.dumps(value), expire)
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter"""
        if not self._client:
            return 0
        return await self._client.incr(key, amount)
    
    async def expire(self, key: str, seconds: int):
        """Set expiration on key"""
        if not self._client:
            return
        await self._client.expire(key, seconds)
    
    async def check_rate_limit(self, key: str, limit: int, window: int) -> bool:
        """Check if rate limit is exceeded"""
        if not self._client:
            return True
        
        current = await self._client.incr(key)
        if current == 1:
            await self._client.expire(key, window)
        
        return current <= limit
    
    async def acquire_lock(self, lock_key: str, timeout: int = 30) -> bool:
        """Acquire distributed lock"""
        if not self._client:
            return False
        acquired = await self._client.set(lock_key, "1", nx=True, ex=timeout)
        return acquired is not None
    
    async def release_lock(self, lock_key: str):
        """Release distributed lock"""
        if not self._client:
            return
        await self._client.delete(lock_key)


# Global Redis instance
redis_client = RedisClient()

