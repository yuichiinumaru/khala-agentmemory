from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid
import logging

from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class ApprovalService:
    """
    Service for managing Human-in-the-Loop checkpoints.
    Strategy 125: Human-in-the-Loop Checkpoints.
    """
    def __init__(self, db_client: SurrealDBClient):
        self.db_client = db_client
        self.table = "approval_request"

    async def request_approval(self, action: str, resource_id: str, requester: str, reason: str) -> str:
        """Create a new approval request."""
        req_id = f"{self.table}:{uuid.uuid4()}"
        data = {
            "id": req_id,
            "action": action,
            "details": {"resource_id": resource_id, "reason": reason},
            "requester": requester,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        async with self.db_client.get_connection() as conn:
            try:
                await conn.create(req_id, data)
            except AttributeError:
                # Fallback if connection wrapper doesn't expose create directly
                query = f"CREATE {req_id} CONTENT $data"
                await conn.query(query, {"data": data})

        return req_id

    async def create_request(self, action: str, details: Dict[str, Any], requester: str) -> str:
         # Alias/Variant for more generic use
         return await self.request_approval(action, str(details), requester, "No reason provided")

    async def get_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get an approval request."""
        if not request_id.startswith(f"{self.table}:"):
            request_id = f"{self.table}:{request_id}"

        async with self.db_client.get_connection() as conn:
            try:
                # Try using select if available
                if hasattr(conn, 'select'):
                    result = await conn.select(request_id)
                else:
                    # Fallback to query
                    query = f"SELECT * FROM {request_id}"
                    result = await conn.query(query)
                    if isinstance(result, list) and result and 'result' in result[0]:
                        result = result[0]['result']

                # Handle result
                if isinstance(result, list) and result:
                     return result[0]
                elif isinstance(result, dict):
                     return result
                return None
            except Exception as e:
                logger.error(f"Failed to get request: {e}")
                return None

    async def approve(self, request_id: str, approver: str) -> bool:
        """Approve a request."""
        return await self._update_status(request_id, "approved", approver)

    async def approve_request(self, request_id: str, approver: str) -> bool:
        """Approve a request (Alias)."""
        return await self.approve(request_id, approver)

    async def reject(self, request_id: str, approver: str) -> bool:
        """Reject a request."""
        return await self._update_status(request_id, "rejected", approver)

    async def reject_request(self, request_id: str, approver: str) -> bool:
        """Reject a request (Alias)."""
        return await self.reject(request_id, approver)

    async def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get all pending approval requests."""
        query = f"SELECT * FROM {self.table} WHERE status = 'pending';"
        async with self.db_client.get_connection() as conn:
            result = await conn.query(query)
            if result and isinstance(result, list) and len(result) > 0:
                if isinstance(result[0], dict) and 'result' in result[0]:
                     return result[0]['result']
                return result
        return []

    async def _update_status(self, request_id: str, status: str, approver: str) -> bool:
        if not request_id.startswith(f"{self.table}:"):
            request_id = f"{self.table}:{request_id}"

        query = f"UPDATE type::thing('approval_request', $id) SET status = $status, approver = $approver, updated_at = $updated_at;"
        params = {
            "id": request_id.split(":")[1] if ":" in request_id else request_id,
            "status": status,
            "approver": approver,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        try:
             async with self.db_client.get_connection() as conn:
                 await conn.query(query, params)
             return True
        except Exception as e:
            logger.error(f"Failed to update approval request: {e}")
            return False
