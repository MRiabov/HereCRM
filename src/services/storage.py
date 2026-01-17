import boto3
from botocore.exceptions import ClientError
import logging
from typing import Optional

from src.config import settings

logger = logging.getLogger(__name__)

class StorageError(Exception):
    """Base class for storage related errors."""
    pass

class S3Service:
    def __init__(self):
        self.bucket_name = settings.s3_bucket_name
        self.endpoint_url = settings.s3_endpoint_url
        self.access_key = settings.s3_access_key_id
        self.secret_key = settings.s3_secret_access_key
        self.region = settings.s3_region_name

        self.s3_client = None
        if all([self.endpoint_url, self.access_key, self.secret_key]):
            self.s3_client = boto3.client(
                's3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region
            )
        else:
            logger.warning("S3 credentials not fully configured. S3Service will be inoperable.")

    def upload_file(self, file_content: bytes, key: str, content_type: str = 'application/pdf') -> str:
        """
        Uploads file content to S3 and returns the public URL.
        """
        if not self.s3_client:
            raise StorageError("S3 client not initialized. Check configuration.")

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_content,
                ContentType=content_type
            )
            return self.get_public_url(key)
        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            raise StorageError(f"S3 upload failed: {e}")

    def get_public_url(self, key: str) -> str:
        """
        Constructs the public URL for a given key.
        Note: This assumes the bucket/object has public read access or is configured for public access.
        """
        if not self.endpoint_url:
            raise StorageError("S3 endpoint URL not configured.")
        
        # Construct URL based on endpoint and bucket
        # Common format for B2/S3: {endpoint}/{bucket}/{key}
        # Or {bucket}.{endpoint}/{key}
        # We'll use the one that matches most S3-compatible APIs
        if "backblazeb2.com" in self.endpoint_url:
            return f"{self.endpoint_url}/{self.bucket_name}/{key}"
        
        return f"{self.endpoint_url.rstrip('/')}/{self.bucket_name}/{key}"

storage_service = S3Service()

