import logging
import pandas as pd
import io
import json
import httpx
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models import Business, Customer, Job, ImportJob, ExportRequest, PipelineStage
from src.repositories import BusinessRepository, CustomerRepository, JobRepository

logger = logging.getLogger(__name__)

from src.services.storage import storage_service

class DataManagementService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.customer_repo = CustomerRepository(session)
        self.job_repo = JobRepository(session)
        self.business_repo = BusinessRepository(session)

    async def import_data(self, business_id: int, file_url: str, media_type: str) -> ImportJob:
        """
        Orchestrates the data import process.
        1. Creates ImportJob record (committed immediately).
        2. Downloads and parses file.
        3. Validates and writes to DB in a nested transaction (Atomic).
        4. Updates ImportJob status.
        """
        # 1. Create ImportJob (committed first so we can update it even if import fails)
        import_job = ImportJob(
            business_id=business_id,
            status="processing",
            file_url=file_url,
            created_at=datetime.now(timezone.utc)
        )
        self.session.add(import_job)
        await self.session.commit()
        # Refresh to get ID and stay attached to session
        await self.session.refresh(import_job)

        try:
            # Download file
            import os
            allow_local = os.environ.get("ALLOW_LOCAL_IMPORT", "false").lower() == "true"

            if file_url.startswith(("http://", "https://")):
                async with httpx.AsyncClient() as client:
                    response = await client.get(file_url)
                    response.raise_for_status()
                    content = response.content
            elif allow_local:
                # Local file access restricted by environment variable
                logger.warning(f"Local file import attempted and allowed for: {file_url}")
                with open(file_url, "rb") as f:
                    content = f.read()
            else:
                raise ValueError("Local file import is disabled or scheme is unsupported. Use a valid http/https URL.")

            # Parse file
            df = self._parse_file(content, media_type, file_url)
            
            # Update record count (requires a commit/flush, but we do it at end or before processing)
            import_job.record_count = len(df)
            import_job.filename = file_url.split("/")[-1]
            
            # Normalize headers
            df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]

            # Atomic Import Block
            async with self.session.begin_nested():
                await self._process_dataframe(business_id, df)
            
            # If we get here, nested transaction succeeded.
            import_job.status = "completed"
            import_job.completed_at = datetime.now(timezone.utc)

        except Exception as e:
            logger.exception("Import failed")
            # The nested transaction is rolled back automatically by begin_nested() on exception,
            # or we are outside it.
            # We explicitly update the job status now.
            import_job.status = "failed"
            import_job.error_log = [{"error": str(e)}]
            # Important: we don't re-raise if we want to return the failed job info.
            # But the caller might expect wait().
        
        # Final commit to save the job status (and the data if successful)
        await self.session.commit()
        await self.session.refresh(import_job)
        return import_job

    def _parse_file(self, content: bytes, media_type: str, filename: str) -> pd.DataFrame:
        if "csv" in media_type or filename.endswith(".csv"):
            return pd.read_csv(io.BytesIO(content))
        elif "excel" in media_type or "spreadsheet" in media_type or filename.endswith(".xlsx"):
            return pd.read_excel(io.BytesIO(content))
        elif "json" in media_type or filename.endswith(".json"):
            return pd.read_json(io.BytesIO(content))
        else:
            raise ValueError(f"Unsupported file format: {media_type}")

    async def _process_dataframe(self, business_id: int, df: pd.DataFrame):
        """
        Iterates over the dataframe and creates/updates records.
        """
        for index, row in df.iterrows():
            # Validate required fields
            name = row.get("name")
            if pd.isna(name):
                # Try client_name or customer_name
                name = row.get("client_name") or row.get("customer_name")

            if not name:
                # Skip rows without name? Or fail? Spec says "Import MUST be atomic".
                # But maybe skip empty rows at end of CSV.
                continue

            phone = str(row.get("phone", "")) if not pd.isna(row.get("phone")) else None
            # Basic phone cleanup
            if phone:
                phone = "".join(filter(str.isdigit, phone))

            # Find existing customer
            customer = None
            if phone:
                customer = await self.customer_repo.get_by_phone(phone, business_id)

            if not customer:
                customer = Customer(
                    business_id=business_id,
                    name=name,
                    phone=phone,
                    pipeline_stage=PipelineStage.NOT_CONTACTED
                )
                self.session.add(customer)
                await self.session.flush() # get ID

            # Update customer fields
            if not pd.isna(row.get("address")):
                customer.street = row.get("address")
            if not pd.isna(row.get("city")):
                customer.city = row.get("city")
            if not pd.isna(row.get("notes")):
                customer.details = row.get("notes")

            # Add Job if job fields exist
            if not pd.isna(row.get("job_description")) or not pd.isna(row.get("job_price")):
                job = Job(
                    business_id=business_id,
                    customer_id=customer.id,
                    description=row.get("job_description"),
                    value=float(row.get("job_price", 0)) if not pd.isna(row.get("job_price")) else None,
                    status=row.get("job_status", "pending"),
                    location=row.get("address")
                )
                self.session.add(job)

    async def export_data(self, business_id: int, query: str, format: str, filters: Dict[str, Any] = None) -> ExportRequest:
        """
        Process an export request with structured filters and S3 upload.
        """
        filters = filters or {}
        export_req = ExportRequest(
            business_id=business_id,
            query=query,
            format=format,
            status="processing",
            created_at=datetime.now(timezone.utc)
        )
        self.session.add(export_req)
        await self.session.flush()

        try:
            entity_type = filters.get("entity_type")
            min_date = None
            max_date = None
            
            if filters.get("min_date"):
                try:
                    min_date = datetime.fromisoformat(filters["min_date"].replace("Z", "+00:00"))
                except ValueError:
                    pass
            if filters.get("max_date"):
                try:
                    max_date = datetime.fromisoformat(filters["max_date"].replace("Z", "+00:00"))
                except ValueError:
                    pass

            data = []
            
            # Dispatch to appropriate repository
            if entity_type == "job" or (query and "job" in query.lower()):
                jobs = await self.job_repo.search(
                    query=query,
                    business_id=business_id,
                    status=filters.get("status"),
                    min_date=min_date,
                    max_date=max_date,
                    query_type="added" # Default to added date? Or scheduled? Let's assume general search.
                )
                for j in jobs:
                    row = {
                        "id": j.id,
                        "customer": j.customer.name if j.customer else "",
                        "description": j.description,
                        "status": j.status,
                        "value": j.value,
                        "scheduled_at": j.scheduled_at,
                        "location": j.location or j.customer.street if j.customer else "",
                        "created_at": j.created_at
                    }
                    data.append(row)

            elif entity_type == "expense" or (query and "expense" in query.lower()):
                from src.models import Expense
                stmt = select(Expense).where(Expense.business_id == business_id)
                if min_date: stmt = stmt.where(Expense.date >= min_date)
                if max_date: stmt = stmt.where(Expense.date <= max_date)
                result = await self.session.execute(stmt)
                expenses = result.scalars().all()
                for e in expenses:
                    data.append({
                        "date": e.date,
                        "amount": e.amount,
                        "category": e.category or "",
                        "description": e.description or "",
                        "job_id": e.job_id or ""
                    })

            elif entity_type == "ledger" or (query and any(k in query.lower() for k in ["payroll", "ledger", "payout"])):
                from src.models import LedgerEntry
                stmt = select(LedgerEntry).where(LedgerEntry.business_id == business_id)
                if min_date: stmt = stmt.where(LedgerEntry.date >= min_date)
                if max_date: stmt = stmt.where(LedgerEntry.date <= max_date)
                result = await self.session.execute(stmt)
                entries = result.scalars().all()
                for le in entries:
                    data.append({
                        "date": le.date,
                        "employee_id": le.user_id,
                        "amount": le.amount,
                        "type": le.type.value,
                        "description": le.description or ""
                    })
            
            else:
                # Default to Customer/Lead
                customers = await self.customer_repo.search(
                    query=query, 
                    business_id=business_id,
                    entity_type=entity_type,
                    pipeline_stage=filters.get("status"), # Map status to pipeline_stage for customers
                    min_date=min_date,
                    max_date=max_date,
                    query_type="added" 
                )
                
                for c in customers:
                    row = {
                        "id": c.id,
                        "name": c.name,
                        "phone": c.phone,
                        "address": f"{c.street or ''} {c.city or ''}".strip(),
                        "notes": c.details,
                        "stage": c.pipeline_stage.value,
                        "created_at": c.created_at
                    }
                    data.append(row)

            df = pd.DataFrame(data)

            # 3. Format
            output = io.BytesIO()
            # filename for metadata/key
            ext = "xlsx" if format == "excel" else format
            filename = f"export_{business_id}_{int(datetime.now().timestamp())}.{ext}"
            
            content_type = "text/csv"
            if format == "csv":
                df.to_csv(output, index=False)
                content_type = "text/csv"
            elif format in ["excel", "xlsx"]:
                # Remove timezones for Excel compatibility
                for col in df.columns:
                    if pd.api.types.is_datetime64_any_dtype(df[col]):
                        df[col] = df[col].dt.tz_localize(None)
                df.to_excel(output, index=False)
                content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            elif format == "json":
                df.to_json(output, orient="records")
                content_type = "application/json"
            else:
                raise ValueError(f"Unsupported format: {format}")

            output.seek(0)
            file_bytes = output.read()

            # 4. Upload to S3
            
            # Key structure: exports/{business_id}/{filename}
            s3_key = f"exports/{business_id}/{filename}"
            public_url = storage_service.upload_file(file_bytes, s3_key, content_type)

            export_req.s3_key = s3_key
            export_req.public_url = public_url
            export_req.status = "completed"

        except Exception as e:
            logger.exception("Export failed")
            export_req.status = "failed"
            # Log error somewhere? ExportRequest doesn't have error_log field in model currently, 
            # maybe add it or just log to system log.
            
        await self.session.commit()
        return export_req
