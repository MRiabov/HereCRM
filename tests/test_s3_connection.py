import pytest
from src.services.storage import S3Service, storage_service
from src.config import settings
from unittest.mock import patch, MagicMock

@patch('boto3.client')
def test_s3_service_initialization(mock_boto_client):
    """Test that S3Service initializes the boto3 client correctly."""
    # Temporarily set settings
    with patch.object(settings, 's3_endpoint_url', 'http://localhost:9000'), \
         patch.object(settings, 's3_access_key_id', 'test_id'), \
         patch.object(settings, 's3_secret_access_key', 'test_secret'), \
         patch.object(settings, 's3_bucket_name', 'test_bucket'):
        
        service = S3Service()
        assert service.s3_client is not None
        mock_boto_client.assert_called_once_with(
            's3',
            endpoint_url='http://localhost:9000',
            aws_access_key_id='test_id',
            aws_secret_access_key='test_secret',
            region_name='us-east-1'
        )

def test_get_public_url():
    """Test public URL construction."""
    with patch.object(settings, 's3_endpoint_url', 'https://s3.backblazeb2.com'), \
         patch.object(settings, 's3_bucket_name', 'my-bucket'):
        service = S3Service()
        url = service.get_public_url('test_key.pdf')
        assert url == 'https://s3.backblazeb2.com/my-bucket/test_key.pdf'

@patch('boto3.client')
def test_upload_file(mock_boto_client):
    """Test file upload orchestration."""
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3
    
    with patch.object(settings, 's3_endpoint_url', 'http://localhost:9000'), \
         patch.object(settings, 's3_access_key_id', 'id'), \
         patch.object(settings, 's3_secret_access_key', 'secret'), \
         patch.object(settings, 's3_bucket_name', 'bucket'):
        
        service = S3Service()
        file_content = b"fake pdf content"
        key = "invoice_1.pdf"
        
        url = service.upload_file(file_content, key)
        
        mock_s3.put_object.assert_called_once_with(
            Bucket='bucket',
            Key=key,
            Body=file_content,
            ContentType='application/pdf'
        )
        assert "invoice_1.pdf" in url
