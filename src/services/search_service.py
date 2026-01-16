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
        results = []
        
        # Parse dates
        min_date = self._parse_date(params.min_date)
        max_date = self._parse_date(params.max_date)

        # Dispatch based on entity_type
        if params.entity_type == 'customer' or params.entity_type == 'lead':
            results.extend(await self._search_customers(params, business_id, min_date, max_date))
        elif params.entity_type == 'job':
            results.extend(await self._search_jobs(params, business_id, min_date, max_date))
        elif params.entity_type == 'request':
            results.extend(await self._search_requests(params, business_id, min_date, max_date))
        else:
            # Aggregate all
            # We run them concurrently ideally, but sequential is fine for now
            results.extend(await self._search_customers(params, business_id, min_date, max_date))
            results.extend(await self._search_jobs(params, business_id, min_date, max_date))
            results.extend(await self._search_requests(params, business_id, min_date, max_date))

        # Format results (Stubs for now, WP04 covers detailed formatting)
        output = []
        for r in results:
            if hasattr(r, 'name'):
                output.append(f"Customer: {r.name}")
            elif hasattr(r, 'description'):
                output.append(f"Job: {r.description}")
            elif hasattr(r, 'content'):
                output.append(f"Request: {r.content}")
            else:
                output.append(str(r))
        
        if not output:
            return "No results found."

        return "\n".join(output)

    async def _search_customers(self, params: SearchTool, business_id: int, min_date, max_date) -> list:
        return await self.customer_repo.search(
            query=params.query,
            business_id=business_id,
            entity_type=params.entity_type,
            query_type=params.query_type,
            min_date=min_date,
            max_date=max_date,
            radius=params.radius,
            center_lat=params.center_lat,
            center_lon=params.center_lon,
            center_address=params.center_address
        )

    async def _search_jobs(self, params: SearchTool, business_id: int, min_date, max_date) -> list:
        return await self.job_repo.search(
            query=params.query,
            business_id=business_id,
            query_type=params.query_type,
            min_date=min_date,
            max_date=max_date,
            status=params.status,
            radius=params.radius,
            center_lat=params.center_lat,
            center_lon=params.center_lon,
            center_address=params.center_address
        )

    async def _search_requests(self, params: SearchTool, business_id: int, min_date, max_date) -> list:
        return await self.request_repo.search(
            query=params.query,
            business_id=business_id,
            min_date=min_date,
            max_date=max_date,
            status=params.status
        )

    def _parse_date(self, date_str: str | None):
        if not date_str:
            return None
        from datetime import datetime
        try:
            return datetime.fromisoformat(date_str)
        except ValueError:
            return None
