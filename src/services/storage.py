import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
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
                region_name=self.region,
                config=Config(s3={'addressing_style': 'path'})
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
        except Exception as e:
            logger.error(f"Failed to upload file to S3: {e}")
            raise StorageError(f"S3 upload failed: {str(e)}")

    def get_public_url(self, key: str) -> str:
        """
        Generates a presigned URL for the given key.
        """
        if not self.s3_client:
            raise StorageError("S3 client not initialized.")
        
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=604800 # 7 days
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            # Fallback to manual construction if presigning fails
            if "backblazeb2.com" in (self.endpoint_url or ""):
                return f"{self.endpoint_url}/{self.bucket_name}/{key}"
            return f"{self.endpoint_url.rstrip('/')}/{self.bucket_name}/{key}"

storage_service = S3Service()

