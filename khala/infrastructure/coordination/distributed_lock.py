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
    """
    Distributed lock implementation using SurrealDB.

    Architecture:
    - Uses strict Record IDs (`lock:<name>`) to enforce mutual exclusion.
    - Relies on SurrealDB's atomic CREATE guarantee.
    """

    def __init__(self, client, lock_name: str, expire_seconds: int = 60):
        self.client = client
        self.lock_name = lock_name
        self.expire_seconds = expire_seconds

    async def acquire(self) -> bool:
        """
        Acquire the lock.

        Returns:
            bool: True if acquired, False otherwise.
        """
        # Clean up expired locks first to prevent deadlocks from crashed workers
        await self._cleanup_expired()

        try:
            # Atomic Creation: CREATE type::thing('lock', $id)
            # This fails if the record already exists.
            q = """
            CREATE type::thing('lock', $id) CONTENT {
                created_at: time::now(),
                expires_at: time::now() + $duration,
                holder: "khala-worker"
            };
            """
            params = {
                "id": self.lock_name,
                "duration": f"{self.expire_seconds}s"
            }

            async with self.client.get_connection() as conn:
                 await conn.query(q, params)
                 return True

        except Exception as e:
            # If CREATE fails, it likely means the lock exists.
            # We log debug only, as contention is normal.
            logger.debug(f"Lock '{self.lock_name}' busy or error: {e}")
            return False

    async def release(self) -> None:
        """Release the lock."""
        try:
             # Delete strictly by ID
             q = "DELETE type::thing('lock', $id);"
             async with self.client.get_connection() as conn:
                 await conn.query(q, {"id": self.lock_name})
        except Exception as e:
            logger.error(f"Failed to release lock '{self.lock_name}': {e}")

    async def _cleanup_expired(self) -> None:
        """Remove THIS lock if it is expired."""
        try:
            # Only delete if it is actually expired
            q = "DELETE type::thing('lock', $id) WHERE expires_at < time::now();"
            async with self.client.get_connection() as conn:
                await conn.query(q, {"id": self.lock_name})
        except Exception as e:
            logger.warning(f"Failed to cleanup expired lock '{self.lock_name}': {e}")
