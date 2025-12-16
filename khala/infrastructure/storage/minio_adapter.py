import os
import io
import logging
import asyncio
from typing import Optional
from minio import Minio
from minio.error import S3Error
from khala.domain.interfaces.blob_storage import BlobStorage

logger = logging.getLogger(__name__)

class MinIOStorage(BlobStorage):
    def __init__(self, endpoint: str = None, access_key: str = None, secret_key: str = None, secure: bool = False):
        self.endpoint = endpoint or os.environ.get("MINIO_ENDPOINT", "localhost:9000")
        self.access_key = access_key or os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = secret_key or os.environ.get("MINIO_SECRET_KEY", "minioadmin")
        self.bucket_raw = "vivi-infra-raw"
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=secure
        )
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        try:
            if not self.client.bucket_exists(self.bucket_raw):
                self.client.make_bucket(self.bucket_raw)
                logger.info(f"Created MinIO bucket: {self.bucket_raw}")
        except Exception as e:
            logger.error(f"Failed to check/create bucket {self.bucket_raw}: {e}")

    async def upload(self, data: bytes, filename: str, content_type: Optional[str] = None) -> str:
        """
        Uploads data to MinIO.
        Returns URI: s3://{bucket}/{filename}
        """
        # Run synchronous MinIO call in thread pool to avoid blocking async loop
        loop = asyncio.get_running_loop()
        
        def _upload_sync():
            try:
                stream = io.BytesIO(data)
                self.client.put_object(
                    self.bucket_raw,
                    filename,
                    stream,
                    len(data),
                    content_type=content_type or "application/octet-stream"
                )
                return f"s3://{self.bucket_raw}/{filename}"
            except S3Error as e:
                logger.error(f"MinIO Upload Error: {e}")
                raise e

        return await loop.run_in_executor(None, _upload_sync)

    async def get_download_url(self, uri: str, expiry_seconds: int = 3600) -> str:
        """
        Generates presigned URL from URI s3://bucket/filename
        """
        if not uri.startswith("s3://"):
             raise ValueError("Invalid URI scheme. Expected s3://")
        
        # Parse URI: s3://bucket/filename
        parts = uri.replace("s3://", "").split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid S3 URI format: {uri}")
        
        bucket, object_name = parts
        
        loop = asyncio.get_running_loop()
        def _get_url_sync():
            return self.client.get_presigned_url(
                "GET",
                bucket,
                object_name,
                expires=timedelta(seconds=expiry_seconds)
            )

        from datetime import timedelta # Import inside to avoid scope issues if needed, or move top
        return await loop.run_in_executor(None, _get_url_sync)
