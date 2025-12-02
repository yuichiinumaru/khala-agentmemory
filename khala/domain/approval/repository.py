from abc import ABC, abstractmethod
from typing import List, Optional
from .entities import ApprovalRequest, ApprovalStatus

class ApprovalRepository(ABC):
    @abstractmethod
    async def create(self, request: ApprovalRequest) -> str:
        pass

    @abstractmethod
    async def get(self, request_id: str) -> Optional[ApprovalRequest]:
        pass

    @abstractmethod
    async def get_pending_by_user(self, user_id: str) -> List[ApprovalRequest]:
        pass

    @abstractmethod
    async def update(self, request: ApprovalRequest) -> None:
        pass
