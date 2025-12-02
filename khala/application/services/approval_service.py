import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from khala.domain.approval.entities import ApprovalRequest, ApprovalStatus, ApprovalActionType
from khala.domain.approval.repository import ApprovalRepository

logger = logging.getLogger(__name__)

class ApprovalService:
    def __init__(self, repository: ApprovalRepository):
        self.repository = repository

    async def request_approval(
        self,
        user_id: str,
        action_type: ApprovalActionType,
        payload: Dict[str, Any],
        description: str
    ) -> str:
        request = ApprovalRequest(
            user_id=user_id,
            action_type=action_type,
            payload=payload,
            description=description
        )
        await self.repository.create(request)
        logger.info(f"Created approval request {request.id} for user {user_id} (action: {action_type.value})")
        return request.id

    async def get_pending_requests(self, user_id: str) -> List[ApprovalRequest]:
        return await self.repository.get_pending_by_user(user_id)

    async def approve_request(self, request_id: str, reviewer_id: Optional[str] = None) -> None:
        request = await self.repository.get(request_id)
        if not request:
            raise ValueError(f"Approval request {request_id} not found")

        request.approve(reviewer_id)
        await self.repository.update(request)
        logger.info(f"Approved request {request_id}")

    async def reject_request(self, request_id: str, reason: str, reviewer_id: Optional[str] = None) -> None:
        request = await self.repository.get(request_id)
        if not request:
            raise ValueError(f"Approval request {request_id} not found")

        request.reject(reason, reviewer_id)
        await self.repository.update(request)
        logger.info(f"Rejected request {request_id}")

    async def mark_completed(self, request_id: str) -> None:
         request = await self.repository.get(request_id)
         if not request:
             raise ValueError(f"Approval request {request_id} not found")

         request.complete()
         await self.repository.update(request)
