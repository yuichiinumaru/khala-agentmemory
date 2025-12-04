"""
Multi-level cache management system for KHALA.

Provides unified interface for L1 (in-memory), L2 (Redis), 
and L3 (persistent) caching with intelligent cache selection
and performance optimization.
"""

import asyncio
import json
import logging
import threading
import time
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union, TypeVar, TypeVar
from dataclasses import dataclass, field
from collections import OrderedDict, defaultdict
import uuid
import hashlib

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available, L2 cache disabled")

from ..surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

T = TypeVar('T')

class CacheLevel(Enum):
    """Cache level enumeration."""
    L1 = "l1"  # In-memory cache
    L2 = "l2"  # Redis cache
    L3 = "l3"  # Persistent cache


class CacheableItem:
    """Interface for cacheable items."""
    
    def __init__(self, key: str, value: Any, **kwargs):
        self.key = key
        self.value = value
        self.created_at = datetime.now(timezone.utc)
        self.access_count = 0
        self.last_accessed = self.created_at
        self.size_bytes = self._calculate_size()
        self.metadata = kwargs
    
    def _calculate_size(self) -> int:
        """Calculate approximate size in bytes."""
        try:
            return len(str(self.key).encode('utf-8')) + len(str(self.value).encode('utf-8'))
        except:
            return 1024  # Default fallback size
    
    def touch(self):
        """Mark as accessed."""
        self.access_count += 1
        self.last_accessed = datetime.now(timezone.utc)


class L1MemoryCache:
    """L1 in-memory cache with LRU eviction."""
    
    def __init__(self, max_memory_mb: int = 100, ttl_seconds: int = 300):
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, CacheableItem] = {}
        self.access_order: List[str] = []
        self.lock = threading.RLock()
        self.total_size_bytes = 0
        self.evictions = 0
        
        # Cleanup task for TTL
        self._cleanup_task = None
        self._cleanup_running = False
    
    def start_cleanup(self):
        """Start TTL cleanup task."""
        if not self._cleanup_running:
            self._cleanup_running = True
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    def stop_cleanup(self):
        """Stop TTL cleanup task."""
        self._cleanup_running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self.lock:
            item = self.cache.get(key)
            
            if item is None:
                return None
            
            # Check TTL
            if self._is_expired(item):
                await self._remove(key)
                return None
            
            # Touch and return
            self._record_access(key)
            return item.value
    
    async def put(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Put value into cache."""
        ttl = ttl_seconds if ttl_seconds is not None else self.ttl_seconds
        
        with self.lock:
            # Remove existing if present
            existing = self.cache.get(key)
            if existing:
                self._remove_existing(key)
            
            # Create new item
            item = CacheableItem(key, value)
            if ttl != self.ttl_seconds:
                item.metadata['ttl_seconds'] = ttl
            
            # Check if item fits
            if not self._fits_in_memory(item):
                self._evict_to_fit(item)
            
            # Add to cache
            self.cache[key] = item
            self._record_access(key)
            
        return True
    
    def _remove_existing(self, key: str) -> None:
        """Remove existing item before adding new one."""
        if key in self.cache:
            item = self.cache[key]
            self._decrement_size(item.size_bytes)
            if key in self.access_order:
                self.access_order.remove(key)
            del self.cache[key]
    
    def _record_access(self, key: str) -> None:
        """Record cache access for LRU tracking."""
        item = self.cache[key]
        item.touch()
        
        # Update access order (LRU)
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)
    
    def _is_expired(self, item: CacheableItem) -> bool:
        """Check if item is expired."""
        now = datetime.now(timezone.utc)
        
        # Check custom TTL
        if 'ttl_seconds' in item.metadata:
            return (now - item.created_at).total_seconds() > item.metadata['ttl_seconds']
        
        # Check default TTL
        return (now - item.created_at).total_seconds() > self.ttl_seconds
    
    async def _remove(self, key: str) -> None:
        """Remove item from cache."""
        if key in self.cache:
            item = self.cache[key]
            self._decrement_size(item.size_bytes)
            if key in self.access_order:
                self.access_order.remove(key)
            del self.cache[key]
    
    def _decrement_size(self, size_bytes: int) -> None:
        """Decrement total size and update metrics."""
        self.total_size_bytes = max(0, self.total_size_bytes - size_bytes)
    
    def _increment_size(self, size_bytes: int) -> None:
        """Increment total size and update metrics."""
        self.total_size_bytes += size_bytes
    
    def _fits_in_memory(self, item: CacheableItem) -> bool:
        """Check if item fits in remaining memory."""
        return (self.total_size_bytes + item.size_bytes) <= self.max_memory_bytes
    
    def _evict_to_fit(self, new_item: CacheableItem) -> None:
        """Evict LRU items until new item fits."""
        items_to_remove = []
        current_size = self.total_size_bytes
        
        for key in reversed(self.access_order):  # Remove oldest first
            items_to_remove.append(key)
            if key in self.cache:
                current_size -= self.cache[key].size_bytes
                if current_size + new_item.size_bytes <= self.max_memory_bytes:
                    break
        
        # Actually remove items
        for key in items_to_remove:
            if key in self.cache:
                del self.cache[key]
                self._decrement_size(self.cache[key].size_bytes)
            if key in self.access_order:
                self.access_order.remove(key)
            self.evictions += 1
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of expired items."""
        while self._cleanup_running:
            try:
                expired_keys = []
                
                with self.lock:
                    for key, item in self.cache.items():
                        if self._is_expired(item):
                            expired_keys.append(key)
                
                for key in expired_keys:
                    await self._remove(key)
                
                if expired_keys:
                    logger.debug(f"L1 cleanup removed {len(expired_keys)} expired items")
                
            except Exception as e:
                logger.error(f"L1 cleanup error: {e}")
            
            # Run cleanup every 30 seconds
            await asyncio.sleep(30)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            return {
                "total_items": len(self.cache),
                "total_size_bytes": self.total_size_bytes,
                "max_memory_bytes": self.max_memory_bytes,
                "evictions": self.evictions,
                "hit_rate": getattr(self, '_hit_rate', 0.0),
                "ttl_seconds": self.ttl_seconds
            }


class L2RedisCache:
    """L2 Redis-based cache with persistence."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/2", 
                 ttl_seconds: int = 3600, max_items: int = 10000):
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self.max_items = max_items
        self.redis_client = None
        self.key_prefix = "khala_cache:"
        
    async def start(self):
        """Start Redis client."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, L2 cache disabled")
            return
        
        try:
            self.redis_client = redis.Redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("L2 Redis cache connected")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
    
    async def stop(self):
        """Stop Redis client."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache."""
        if not self.redis_client:
            return None
        
        try:
            redis_key = self._make_key(key)
            cached_data = await self.redis_client.hgetall(redis_key)
            
            if not cached_data:
                return None
            
            # Check TTL
            ttl = await self.redis_client.ttl(redis_key)
            if ttl == -1:  # No TTL set or expired
                await self.redis_client.delete(redis_key)
                return None
            
            # Deserialize and return
            cached_value = cached_data.get(b'value')
            if cached_value:
                try:
                    return json.loads(cached_value.decode('utf-8'))
                except json.JSONDecodeError:
                    return cached_value.decode('utf-8')
            
        except Exception as e:
            logger.error(f"L2 cache get error for key {key}: {e}")
        
        return None
    
    async def put(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Put value into Redis cache."""
        if not self.redis_client:
            return False
        
        try:
            redis_key = self._make_key(key)
            ttl = ttl_seconds if ttl_seconds is not None else self.ttl_seconds
            
            # Serialize value
            try:
                serialized_value = json.dumps(value, default=str)
            except (TypeError, ValueError):
                serialized_value = str(value)
            
            # Store with TTL
            await self.redis_client.hset(redis_key, {
                b'value': serialized_value,
                b'timestamp': datetime.now(timezone.utc).isoencode().encode('utf-8'),
                b'type': type(value).__name__
            })
            await self.redis_client.expire(redis_key, ttl)
            
            return True
            
        except Exception as e:
            logger.error(f"L2 cache put error for key {key}: {e}")
            return False
    
    def _make_key(self, key: str) -> str:
        """Generate cache key for Redis."""
        return f"{self.key_prefix}{key}"


class L3PersistentCache:
    """L3 persistent cache using database storage."""
    
    def __init__(self, ttl_seconds: int = 86400, max_entries: int = 100000):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self.db_client = None
        self.table_name = "cache_storage"
        
    async def start(self):
        """Initialize database connection."""
        try:
            self.db_client = SurrealDBClient()
            await self._ensure_table_exists()
            logger.info("L3 persistent cache initialized")
        except Exception as e:
            logger.error(f"Failed to initialize L3 cache: {e}")
            self.db_client = None
    
    async def stop(self):
        """Stop database connection."""
        if self.db_client:
            self.db_client = None
    
    async def _ensure_table_exists(self):
        """Ensure cache table exists in database."""
        # Table creation is now handled by SchemaManager
        pass
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from persistent cache."""
        if not self.db_client:
            return None
        
        try:
            record = await self.db_client.get_cache_entry(key)
            
            if not record:
                return None
            
            # Check if expired
            now = datetime.now(timezone.utc)
            if record.get('expires_at') and now > record['expires_at']:
                await self.db_client.delete_cache_entry(key)
                return None
            
            # Update access count
            await self.db_client.update_cache_entry(key, {
                'access_count': record.get('access_count', 0) + 1
            })
            
            return record.get('value')
            
        except Exception as e:
            logger.error(f"L3 cache get error for key {key}: {e}")
            return None
    
    async def put(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Put value into persistent cache."""
        if not self.db_client:
            return False
        
        try:
            now = datetime.now(timezone.utc)
            ttl = ttl_seconds if ttl_seconds is not None else self.ttl_seconds
            expires_at = now + timedelta(seconds=ttl)
            
            await self.db_client.create_cache_entry(
                id=key,
                value=value,
                created_at=now,
                expires_at=expires_at,
                access_count=0,
                metadata={}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"L3 cache put error for key {key}: {e}")
            return False


@dataclass
class CacheMetrics:
    """Cache performance metrics."""
    l1_hit_count: int = 0
    l1_miss_count: int = 0
    l1_requests: int = 0
    l2_hit_count: int = 0
    l2_miss_count: int = 0
    l2_requests: int = 0
    l3_hit_count: int = 0
    l3_miss_count: int = 0
    l3_requests: int = 0
    total_responses: int = 0
    avg_response_time_ms: float = 0.0
    
    @property
    def l1_hit_rate(self) -> float:
        return self.l1_hit_count / max(1, self.l1_requests) if self.l1_requests > 0 else 0.0
    
    @property
    def l2_hit_rate(self) -> float:
        return self.l2_hit_count / max(1, self.l2_requests) if self.l2_requests > 0 else 0.0
    
    @property
    def l3_hit_rate(self) -> float:
        return self.l3_hit_count / max(1, self.l3_requests) if self.l3_requests > 0 else 0.0
    
    @property
    def overall_hit_rate(self) -> float:
        total_hits = self.l1_hit_count + self.l2_hit_count + self.l3_hit_count
        total_requests = self.l1_requests + self.l2_requests + self.l3_requests
        return total_hits / max(1, total_requests) if total_requests > 0 else 0.0


class CacheManager:
    """Unified cache management interface."""
    
    def __init__(
        self,
        l1_max_mb: int = 100,
        l1_ttl_seconds: int = 300,
        l2_redis_url: str = "redis://localhost:6379/2",
        l2_ttl_seconds: int = 3600,
        l2_max_items: int = 10000,
        l3_ttl_seconds: int = 86400,
        l3_max_entries: int = 100000
    ):
        """Initialize cache manager."""
        self.l1_cache = L1MemoryCache(l1_max_mb, l1_ttl_seconds)
        self.l2_cache = L2RedisCache(l2_redis_url, l2_ttl_seconds, l2_max_items)
        self.l3_cache = L3PersistentCache(l3_ttl_seconds, l3_max_entries)
        
        self.metrics = CacheMetrics()
        self.cache_warming = True
        self.write_strategy = "write_through"  # or "write_behind"
        
        # Start components
        self.started = False
    
    async def start(self) -> None:
        """Start all cache components."""
        if self.started:
            return
        
        await self.l2_cache.start()
        await self.l3_cache.start()
        self.l1_cache.start_cleanup()
        
        self.started = True
        logger.info("Cache manager started with L1/L2/L3 cache levels")
    
    async def stop(self) -> None:
        """Stop all cache components."""
        if not self.started:
            return
        
        self.l1_cache.stop_cleanup()
        await self.l2_cache.stop()
        await self.l3_cache.stop()
        
        self.started = False
        logger.info("Cache manager stopped")
    
    async def get(self, key: str, preferred_level: Optional[CacheLevel] = None) -> Optional[T]:
        """Get value with intelligent level selection."""
        start_time = time.time()
        
        # Try preferred level first
        if preferred_level and preferred_level == CacheLevel.L3:
            result = await self._get_l3(key)
            if result is not None:
                self.metrics.l3_hit_count += 1
                self.metrics.l3_requests += 1
            else:
                self.metrics.l3_miss_count += 1
                self.metrics.l3_requests += 1
            return result
        
        # Try L1 first (fastest)
        result = await self._get_l1(key)
        if result is not None:
            elapsed = (time.time() - start_time) * 1000
            self.metrics.avg_response_time_ms = (
                (self.metrics.avg_response_time_ms * self.metrics.total_responses + elapsed) /
                (self.metrics.total_responses + 1)
            )
            self.metrics.l1_hit_count += 1
            self.metrics.l1_requests += 1
            return result
        
        # Try L2
        result = await self._get_l2(key)
        if result is not None:
            # Promote to L1
            await self._put_l1(key, result)
            elapsed = (time.time() - start_time) * 1000
            self.metrics.avg_response_time_ms = (
                (self.metrics.avg_response_time_ms * self.metrics.total_responses + elapsed) /
                (self.metrics.total_responses + 1)
            )
            self.metrics.l2_hit_count += 1
            self.metrics.l2_requests += 1
            return result
        
        # Try L3
        result = await self._get_l3(key)
        if result is not None:
            # Promote to higher levels
            await self._put_l2(key, result)
            await self._put_l1(key, result)
            elapsed = (time.time() - start_time) * 1000
            self.metrics.avg_response_time_ms = (
                (self.metrics.avg_response_time_ms * self.metrics.total_responses + elapsed) /
                (self.metrics.total_responses + 1)
            )
            self.metrics.l3_hit_count += 1
            self.metrics.l3_requests += 1
            return result
        
        # Miss at all levels
        self.metrics.l1_miss_count += 1
        self.metrics.l2_miss_count += 1
        self.metrics.l3_miss_count += 1
        self.metrics.l1_requests += 1
        self.metrics.l2_requests += 1
        self.metrics.l3_requests += 1
        
        self.metrics.total_responses += 1
        return None
    
    async def put(
        self, 
        key: str, 
        value: T, 
        levels: Optional[List[CacheLevel]] = None,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """Put value into specified cache levels."""
        levels_to_use = levels or [CacheLevel.L1, CacheLevel.L2, CacheLevel.L3]
        
        success = True
        
        for level in levels_to_use:
            try:
                if level == CacheLevel.L1:
                    success = await self._put_l1(key, value, ttl_seconds)
                elif level == CacheLevel.L2:
                    success = await self._put_l2(key, value, ttl_seconds)
                elif level == CacheLevel.L3:
                    success = await self._put_l3(key, value, ttl_seconds)
                
                if not success:
                    logger.warning(f"Failed to cache {key} at level {level.value}")
                    
            except Exception as e:
                logger.error(f"Error caching {key} at level {level.value}: {e}")
                success = False
        
        return success
    
    async def _get_l1(self, key: str) -> Optional[T]:
        """Get from L1 cache."""
        return await self.l1_cache.get(key)
    
    async def _get_l2(self, key: str) -> Optional[T]:
        """Get from L2 cache."""
        return await self.l2_cache.get(key)
    
    async def _get_l3(self, key: str) -> Optional[T]:
        """Get from L3 cache."""
        return await self.l3_cache.get(key)
    
    async def _put_l1(self, key: str, value: T, ttl_seconds: Optional[int] = None) -> bool:
        """Put into L1 cache."""
        return await self.l1_cache.put(key, value, ttl_seconds)
    
    async def _put_l2(self, key: str, value: T, ttl_seconds: Optional[int] = None) -> bool:
        """Put into L2 cache."""
        return await self.l2_cache.put(key, value, ttl_seconds)
    
    async def _put_l3(self, key: str, value: T, ttl_seconds: Optional[int] = None) -> bool:
        """Put into L3 cache."""
        return await self.l3_cache.put(key, value, ttl_seconds)
    
    def generate_cache_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        # Create deterministic key from arguments
        key_parts = [str(arg) for arg in args]
        key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
        key_string = "_".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()[:32]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive cache metrics."""
        return {
            "hit_rates": {
                "l1": self.metrics.l1_hit_rate,
                "l2": self.metrics.l2_hit_rate, 
                "l3": self.metrics.l3_hit_rate,
                "overall": self.metrics.overall_hit_rate
            },
            "levels": {
                "l1": self.l1_cache.get_stats(),
                "l2": {"connected": self.l2_cache.redis_client is not None},
                "l3": {"connected": self.l3_cache.db_client is not None}
            },
            "performance": {
                "total_responses": self.metrics.total_responses,
                "avg_response_time_ms": self.metrics.avg_response_time_ms
            }
        }
    
    async def clear_all(self) -> bool:
        """Clear all cache levels."""
        try:
            # Clear L1 (in-memory)
            self.l1_cache.cache.clear()
            self.l1_cache.access_order.clear()
            self.l1_cache.total_size_bytes = 0
            
            # Clear L2 (Redis)
            if self.l2_cache.redis_client:
                keys = await self.l2_cache.redis_client.keys(f"{self.l2_cache.key_prefix}*")
                if keys:
                    await self.l2_cache.redis_client.delete(*keys)
            
            # Clear L3 (database)
            if self.l3_cache.db_client:
                # Delete all cache entries
                await self.l3_cache.db_client.execute_async("DELETE FROM cache_storage")
            
            # Reset metrics
            self.metrics = CacheMetrics()
            
            logger.info("All cache levels cleared")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear caches: {e}")
            return False
    
    async def warm_cache(self, common_items: Dict[str, Any]) -> int:
        """Warm cache with common data."""
        warmed_count = 0
        
        for key, value in common_items.items():
            try:
                success = await self.put(key, value)
                if success:
                    warmed_count += 1
            except Exception as e:
                logger.warning(f"Failed to warm cache for key {key}: {e}")
        
        logger.info(f"Warmed cache with {warmed_count} items")
        return warmed_count


# Factory function
def create_cache_manager(
    l1_max_mb: int = 100,
    l1_ttl_seconds: int = 300,
    l2_redis_url: str = "redis://localhost:6379/2",
    l2_ttl_seconds: int = 3600,
    l3_ttl_seconds: int = 86400
) -> CacheManager:
    """Create configured cache manager."""
    return CacheManager(
        l1_max_mb=l1_max_mb,
        l1_ttl_seconds=l1_ttl_seconds,
        l2_redis_url=l2_redis_url,
        l2_ttl_seconds=l2_ttl_seconds,
        l3_ttl_seconds=l3_ttl_seconds
    )
