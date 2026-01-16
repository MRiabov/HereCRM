from sqlalchemy.ext.asyncio import AsyncSession
from src.repositories import CustomerRepository, JobRepository, RequestRepository
from src.services.geocoding import GeocodingService
from src.uimodels import SearchTool


class SearchService:
    def __init__(self, session: AsyncSession, geocoding_service: GeocodingService):
        self.session = session
        self.geocoding_service = geocoding_service
        self.customer_repo = CustomerRepository(session)
        self.job_repo = JobRepository(session)
        self.request_repo = RequestRepository(session)

    async def search(self, params: SearchTool, business_id: int) -> str:
        """
        Execute a unified search across Customers, Jobs, and Requests.
        """
        return ""
