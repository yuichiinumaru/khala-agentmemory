"""Distributed lock implementation using Redis or SurrealDB."""
import asyncio
import logging
from typing import Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class DistributedLock(ABC):
    """Abstract base class for distributed locks."""

    @abstractmethod
    async def acquire(self) -> bool:
        """Acquire the lock."""
        pass

    @abstractmethod
    async def release(self) -> None:
        """Release the lock."""
        pass

class SurrealDBLock(DistributedLock):
    """Distributed lock implementation using SurrealDB."""

    def __init__(self, client, lock_name: str, expire_seconds: int = 60):
        self.client = client
        self.lock_name = lock_name
        self.expire_seconds = expire_seconds

    async def acquire(self) -> bool:
        """Acquire the lock."""
        # Clean up expired locks first to prevent deadlocks
        await self._cleanup_expired()

        try:
            # Try to create lock
            q = """
            CREATE lock SET
                id = $id,
                expires_at = time::now() + $duration;
            """
            params = {
                "id": self.lock_name,
                "duration": f"{self.expire_seconds}s"
            }

            async with self.client.get_connection() as conn:
                 await conn.query(q, params)
                 return True

        except Exception as e:
            logger.debug(f"Lock acquire failed (locked or error): {e}")
            return False

    async def release(self) -> None:
        """Release the lock."""
        try:
             async with self.client.get_connection() as conn:
                 await conn.query("DELETE lock WHERE id = $id", {"id": self.lock_name})
        except Exception as e:
            logger.error(f"Failed to release lock: {e}")

    async def _cleanup_expired(self) -> None:
        """Remove expired locks."""
        try:
            q = "DELETE lock WHERE id = $id AND expires_at < time::now();"
            async with self.client.get_connection() as conn:
                await conn.query(q, {"id": self.lock_name})
        except Exception as e:
            logger.warning(f"Failed to cleanup expired locks: {e}")
