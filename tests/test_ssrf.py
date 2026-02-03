import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from src.utils.url_validator import validate_safe_url
from src.services.data_management import DataManagementService
from src.models import ImportStatus, EntityType

@pytest.mark.asyncio
@pytest.mark.parametrize("url", [
    "http://google.com",
    "https://example.com/foo.csv",
    "http://8.8.8.8/file.csv",
])
async def test_validate_safe_url_valid(url):
    # Mock loop.getaddrinfo
    with patch("asyncio.get_running_loop") as mock_get_loop:
        mock_loop = MagicMock()
        mock_get_loop.return_value = mock_loop
        # 8.8.8.8
        mock_loop.getaddrinfo = AsyncMock(return_value=[(2, 1, 6, '', ('8.8.8.8', 80))])

        await validate_safe_url(url)

@pytest.mark.asyncio
@pytest.mark.parametrize("url", [
    "http://localhost",
    "http://127.0.0.1",
    "http://[::1]",
    "http://192.168.1.5",
    "http://10.0.0.1",
    "http://0.0.0.0",
    "http://169.254.169.254",
    "http://[::ffff:127.0.0.1]", # IPv4 mapped
])
async def test_validate_safe_url_invalid_ips(url):
     # For explicit IPs, it fails before resolution.
     # For localhost, it resolves.

     with patch("asyncio.get_running_loop") as mock_get_loop:
        mock_loop = MagicMock()
        mock_get_loop.return_value = mock_loop
        # Mock resolving to local/private if resolution happens
        mock_loop.getaddrinfo = AsyncMock(return_value=[(2, 1, 6, '', ('127.0.0.1', 80))])

        with pytest.raises(ValueError, match="Restricted IP|restricted IP"):
            await validate_safe_url(url)

@pytest.mark.asyncio
async def test_validate_safe_url_dns_resolution_to_private():
    url = "http://my-internal-service.local"
    with patch("asyncio.get_running_loop") as mock_get_loop:
        mock_loop = MagicMock()
        mock_get_loop.return_value = mock_loop
        mock_loop.getaddrinfo = AsyncMock(return_value=[(2, 1, 6, '', ('192.168.1.1', 80))])

        with pytest.raises(ValueError, match="Hostname resolved to restricted IP"):
            await validate_safe_url(url)

@pytest.mark.asyncio
async def test_import_data_ssrf_protection(async_session):
    service = DataManagementService(async_session)
    unsafe_url = "http://127.0.0.1/sensitive.csv"
    business_id = 1

    import_job = await service.import_data(
        business_id=business_id,
        file_url=unsafe_url,
        media_type="text/csv",
        entity_type=EntityType.CUSTOMER
    )

    assert import_job.status == ImportStatus.FAILED
    assert "Restricted IP address" in str(import_job.error_log) or "Error validating URL" in str(import_job.error_log)
