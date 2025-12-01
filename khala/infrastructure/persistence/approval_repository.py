from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timezone

from khala.domain.approval.entities import ApprovalRequest, ApprovalStatus, ApprovalActionType
from khala.domain.approval.repository import ApprovalRepository
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class SurrealDBApprovalRepository(ApprovalRepository):
    def __init__(self, client: SurrealDBClient):
        self.client = client

    async def create(self, request: ApprovalRequest) -> str:
        query = """
        CREATE type::thing('approval_request', $id) CONTENT {
            user_id: $user_id,
            action_type: $action_type,
            payload: $payload,
            description: $description,
            status: $status,
            created_at: $created_at,
            updated_at: $updated_at,
            reviewed_at: $reviewed_at,
            reviewer_id: $reviewer_id,
            rejection_reason: $rejection_reason
        };
        """

        params = {
            "id": request.id,
            "user_id": request.user_id,
            "action_type": request.action_type.value,
            "payload": request.payload,
            "description": request.description,
            "status": request.status.value,
            "created_at": request.created_at.isoformat(),
            "updated_at": request.updated_at.isoformat(),
            "reviewed_at": request.reviewed_at.isoformat() if request.reviewed_at else None,
            "reviewer_id": request.reviewer_id,
            "rejection_reason": request.rejection_reason
        }

        async with self.client.get_connection() as conn:
            await conn.query(query, params)
            return request.id

    async def get(self, request_id: str) -> Optional[ApprovalRequest]:
        query = "SELECT * FROM type::thing('approval_request', $id);"
        params = {"id": request_id}

        async with self.client.get_connection() as conn:
            response = await conn.query(query, params)

            if response and isinstance(response, list) and len(response) > 0:
                item = response[0]
                if isinstance(item, dict):
                    if 'status' in item and 'result' in item and item['status'] == 'OK':
                        if item['result']:
                            return self._deserialize(item['result'][0])
                    elif 'id' in item: # Direct record
                         return self._deserialize(item)
            return None

    async def get_pending_by_user(self, user_id: str) -> List[ApprovalRequest]:
        query = """
        SELECT * FROM approval_request
        WHERE user_id = $user_id
        AND status = 'pending'
        ORDER BY created_at ASC;
        """
        params = {"user_id": user_id}

        async with self.client.get_connection() as conn:
            response = await conn.query(query, params)
            if response and isinstance(response, list):
                return [self._deserialize(data) for data in response]
            return []

    async def update(self, request: ApprovalRequest) -> None:
        query = """
        UPDATE type::thing('approval_request', $id) CONTENT {
            user_id: $user_id,
            action_type: $action_type,
            payload: $payload,
            description: $description,
            status: $status,
            created_at: $created_at,
            updated_at: time::now(),
            reviewed_at: $reviewed_at,
            reviewer_id: $reviewer_id,
            rejection_reason: $rejection_reason
        };
        """

        params = {
            "id": request.id,
            "user_id": request.user_id,
            "action_type": request.action_type.value,
            "payload": request.payload,
            "description": request.description,
            "status": request.status.value,
            "created_at": request.created_at.isoformat(),
            "reviewed_at": request.reviewed_at.isoformat() if request.reviewed_at else None,
            "reviewer_id": request.reviewer_id,
            "rejection_reason": request.rejection_reason
        }

        async with self.client.get_connection() as conn:
            await conn.query(query, params)

    def _deserialize(self, data: Dict[str, Any]) -> ApprovalRequest:
        req_id = str(data["id"])
        if req_id.startswith("approval_request:"):
            req_id = req_id.split(":")[1]

        def parse_dt(dt_val: Any) -> Optional[datetime]:
            if not dt_val:
                return None
            if isinstance(dt_val, str):
                if dt_val.endswith('Z'):
                    dt_val = dt_val[:-1]
                return datetime.fromisoformat(dt_val).replace(tzinfo=timezone.utc)
            return dt_val

        return ApprovalRequest(
            id=req_id,
            user_id=data["user_id"],
            action_type=ApprovalActionType(data["action_type"]),
            payload=data["payload"],
            description=data["description"],
            status=ApprovalStatus(data["status"]),
            created_at=parse_dt(data["created_at"]) or datetime.now(timezone.utc),
            updated_at=parse_dt(data["updated_at"]) or datetime.now(timezone.utc),
            reviewed_at=parse_dt(data.get("reviewed_at")),
            reviewer_id=data.get("reviewer_id"),
            rejection_reason=data.get("rejection_reason")
        )
