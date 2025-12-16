from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class BlobStorage(ABC):
    """
    Interface for blob storage providers (e.g., MinIO, S3, Local).
    """

    @abstractmethod
    async def upload(self, data: bytes, filename: str, content_type: Optional[str] = None) -> str:
        """
        Uploads a blob and returns its URI (e.g., s3://bucket/file).
        """
        pass

    @abstractmethod
    async def get_download_url(self, uri: str, expiry_seconds: int = 3600) -> str:
        """
        Generates a presigned URL for downloading the blob.
        """
        pass
