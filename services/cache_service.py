"""
Redis Cache Service for KingdomPay
Handles caching, session management, and rate limiting
"""

import json
import pickle
from typing import Any, Optional, Union, Dict, List
from datetime import timedelta
import redis
from flask import current_app
import logging

logger = logging.getLogger(__name__)


class CacheService:
    """Redis-based cache service with session management"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.default_ttl = 3600  # 1 hour default TTL

    def _serialize_value(self, value: Any) -> str:
        """Serialize value for storage"""
        try:
            return json.dumps(value, default=str)
        except (TypeError, ValueError):
            # Fallback to pickle for complex objects
            return pickle.dumps(value).hex()

    def _deserialize_value(self, value: str, use_pickle: bool = False) -> Any:
        """Deserialize value from storage"""
        try:
            if use_pickle:
                return pickle.loads(bytes.fromhex(value))
            return json.loads(value)
        except (json.JSONDecodeError, ValueError, TypeError):
            # Try pickle if JSON fails
            try:
                return pickle.loads(bytes.fromhex(value))
            except (ValueError, TypeError):
                return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a key-value pair with optional TTL"""
        try:
            serialized_value = self._serialize_value(value)
            ttl = ttl or self.default_ttl
            return self.redis.setex(key, ttl, serialized_value)
        except Exception as e:
            logger.error(f"Failed to set cache key {key}: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get value by key"""
        try:
            value = self.redis.get(key)
            if value is None:
                return default
            return self._deserialize_value(value)
        except Exception as e:
            logger.error(f"Failed to get cache key {key}: {e}")
            return default

    def delete(self, key: str) -> bool:
        """Delete a key"""
        try:
            return bool(self.redis.delete(key))
        except Exception as e:
            logger.error(f"Failed to delete cache key {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return bool(self.redis.exists(key))
        except Exception as e:
            logger.error(f"Failed to check existence of key {key}: {e}")
            return False

    def expire(self, key: str, ttl: int) -> bool:
        """Set expiration for a key"""
        try:
            return self.redis.expire(key, ttl)
        except Exception as e:
            logger.error(f"Failed to set expiration for key {key}: {e}")
            return False

    def increment(self, key: str, amount: int = 1, ttl: Optional[int] = None) -> int:
        """Increment a counter"""
        try:
            pipe = self.redis.pipeline()
            pipe.incr(key, amount)
            if ttl:
                pipe.expire(key, ttl)
            results = pipe.execute()
            return results[0]
        except Exception as e:
            logger.error(f"Failed to increment key {key}: {e}")
            return 0

    def decrement(self, key: str, amount: int = 1) -> int:
        """Decrement a counter"""
        try:
            return self.redis.decr(key, amount)
        except Exception as e:
            logger.error(f"Failed to decrement key {key}: {e}")
            return 0

    # Session Management Methods
    def set_session(
        self, session_id: str, data: Dict[str, Any], ttl: int = 3600
    ) -> bool:
        """Store session data"""
        session_key = f"session:{session_id}"
        return self.set(session_key, data, ttl)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session data"""
        session_key = f"session:{session_id}"
        return self.get(session_key)

    def delete_session(self, session_id: str) -> bool:
        """Delete session data"""
        session_key = f"session:{session_id}"
        return self.delete(session_key)

    def extend_session(self, session_id: str, ttl: int = 3600) -> bool:
        """Extend session TTL"""
        session_key = f"session:{session_id}"
        return self.expire(session_key, ttl)

    # User-specific caching
    def cache_user_data(
        self, user_id: int, data: Dict[str, Any], ttl: int = 1800
    ) -> bool:
        """Cache user-specific data"""
        user_key = f"user:{user_id}:data"
        return self.set(user_key, data, ttl)

    def get_cached_user_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get cached user data"""
        user_key = f"user:{user_id}:data"
        return self.get(user_key)

    def invalidate_user_cache(self, user_id: int) -> bool:
        """Invalidate all user-related cache"""
        try:
            pattern = f"user:{user_id}:*"
            keys = self.redis.keys(pattern)
            if keys:
                return bool(self.redis.delete(*keys))
            return True
        except Exception as e:
            logger.error(f"Failed to invalidate user cache for user {user_id}: {e}")
            return False

    # Wallet-specific caching
    def cache_wallet_balance(
        self, wallet_id: int, balance: float, ttl: int = 300
    ) -> bool:
        """Cache wallet balance (short TTL for real-time data)"""
        wallet_key = f"wallet:{wallet_id}:balance"
        return self.set(wallet_key, balance, ttl)

    def get_cached_wallet_balance(self, wallet_id: int) -> Optional[float]:
        """Get cached wallet balance"""
        wallet_key = f"wallet:{wallet_id}:balance"
        return self.get(wallet_key)

    def invalidate_wallet_cache(self, wallet_id: int) -> bool:
        """Invalidate wallet-related cache"""
        try:
            pattern = f"wallet:{wallet_id}:*"
            keys = self.redis.keys(pattern)
            if keys:
                return bool(self.redis.delete(*keys))
            return True
        except Exception as e:
            logger.error(
                f"Failed to invalidate wallet cache for wallet {wallet_id}: {e}"
            )
            return False

    # Rate limiting helpers
    def check_rate_limit(self, key: str, limit: int, window: int) -> Dict[str, Any]:
        """Check if rate limit is exceeded"""
        try:
            current_count = self.increment(key, 1, window)
            remaining = max(0, limit - current_count)
            reset_time = self.redis.ttl(key)

            return {
                "limit": limit,
                "remaining": remaining,
                "reset": reset_time,
                "exceeded": current_count > limit,
            }
        except Exception as e:
            logger.error(f"Failed to check rate limit for key {key}: {e}")
            return {"limit": limit, "remaining": limit, "reset": 0, "exceeded": False}

    # Transaction caching
    def cache_transaction(
        self, transaction_id: str, data: Dict[str, Any], ttl: int = 3600
    ) -> bool:
        """Cache transaction data"""
        tx_key = f"transaction:{transaction_id}"
        return self.set(tx_key, data, ttl)

    def get_cached_transaction(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Get cached transaction data"""
        tx_key = f"transaction:{transaction_id}"
        return self.get(tx_key)

    # Health check
    def health_check(self) -> Dict[str, Any]:
        """Check Redis connection health"""
        try:
            info = self.redis.info()
            return {
                "status": "healthy",
                "redis_version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
                "uptime_in_seconds": info.get("uptime_in_seconds"),
            }
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    # Bulk operations
    def mget(self, keys: List[str]) -> List[Any]:
        """Get multiple keys at once"""
        try:
            values = self.redis.mget(keys)
            return [self._deserialize_value(v) if v else None for v in values]
        except Exception as e:
            logger.error(f"Failed to get multiple keys: {e}")
            return [None] * len(keys)

    def mset(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple key-value pairs"""
        try:
            serialized_mapping = {
                k: self._serialize_value(v) for k, v in mapping.items()
            }
            result = self.redis.mset(serialized_mapping)
            if ttl and result:
                pipe = self.redis.pipeline()
                for key in mapping.keys():
                    pipe.expire(key, ttl)
                pipe.execute()
            return result
        except Exception as e:
            logger.error(f"Failed to set multiple keys: {e}")
            return False
