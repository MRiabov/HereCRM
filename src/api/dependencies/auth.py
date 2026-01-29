from fastapi import Header, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.services.integration_service import IntegrationService
from src.repositories.integration_repository import IntegrationRepository
from src.models import IntegrationConfig


async def get_integration_service(
    session: AsyncSession = Depends(get_db),
) -> IntegrationService:
    repository = IntegrationRepository(session)
    return IntegrationService(repository)


async def get_api_key_auth(
    x_api_key: str = Header(..., alias="X-API-Key"),
    service: IntegrationService = Depends(get_integration_service),
) -> IntegrationConfig:
    """
    Dependency to authenticate requests using an API Key.
    Returns the IntegrationConfig object if valid.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API Key"
        )

    config = await service.validate_key(x_api_key)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API Key",
        )

    return config
