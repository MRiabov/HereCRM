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

        # Geocode if address provided but no coordinates
        if params.center_address and (params.center_lat is None or params.center_lon is None):
            lat, lon, _, _, _, _ = await self.geocoding_service.geocode(params.center_address)
            if lat is not None and lon is not None:
                params.center_lat = lat
                params.center_lon = lon
        
        # Default radius if location present
        if (params.center_lat is not None and params.center_lon is not None) and not params.radius:
            params.radius = 200.0  # Default 200m

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

        # Truncate results if too many
        MAX_RESULTS = 10
        total_count = len(results)
        if total_count > MAX_RESULTS:
            results = results[:MAX_RESULTS]
            truncated_count = total_count - MAX_RESULTS
        else:
            truncated_count = 0

        # Format results
        output = self._format_results(results, params.detailed)
        
        if not output:
            return "No results found."

        if truncated_count > 0:
            output += f"\n\n...and {truncated_count} more results."

        return output

    def _format_results(self, results: list, detailed: bool) -> str:
        lines = []
        for item in results:
            if hasattr(item, 'phone'): # Customer
                lines.append(self._format_customer(item, detailed))
            elif hasattr(item, 'description'): # Job
                lines.append(self._format_job(item, detailed))
            elif hasattr(item, 'content'): # Request
                lines.append(self._format_request(item, detailed))
            else:
                lines.append(str(item))
        return "\n".join(lines)

    def _format_customer(self, c, detailed: bool) -> str:
        # Concise: "Name (Phone)"
        # Detailed: "Name (Phone) - Address - Details"
        base = f"Customer: {c.name}"
        if c.phone:
            base += f" ({c.phone})"
        
        if not detailed:
            return base
            
        extras = []
        if c.street:
            extras.append(c.street)
        elif c.original_address_input:
            extras.append(c.original_address_input)
            
        if c.city:
            extras.append(c.city)
            
        if hasattr(c, 'postal_code') and c.postal_code:
            extras.append(c.postal_code)
            
        if c.details:
            extras.append(c.details)
            
        if extras:
            base += " - " + ", ".join(extras)
            
        return base

    def _format_job(self, j, detailed: bool) -> str:
        # Concise: "Job: Desc (Status)"
        # Detailed: "Job: Desc (Status) - Date - Customer: Name"
        desc = j.description or "No description"
        base = f"Job: {desc} (Status: {j.status})"
        
        if not detailed:
            return base
            
        extras = []
        if j.scheduled_at:
            extras.append(f"Scheduled: {j.scheduled_at.strftime('%Y-%m-%d %H:%M')}")
            
        if j.customer:
            extras.append(f"Customer: {j.customer.name}")
            
        if j.location:
            extras.append(f"Loc: {j.location}")

        if extras:
            base += " - " + "; ".join(extras)
            
        return base

    def _format_request(self, r, detailed: bool) -> str:
        base = f"Request: {r.content} (Status: {r.status})"
        # Request doesn't have much extra detail yet
        return base

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
