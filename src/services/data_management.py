import logging
import pandas as pd
import io
import httpx
import zipfile
from datetime import datetime, timezone
from typing import Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models import Customer, Job, ImportJob, ExportRequest, PipelineStage, Expense, LedgerEntry, ExportStatus, JobStatus
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
        """
        import_job = ImportJob(
            business_id=business_id,
            status="PROCESSING",
            file_url=file_url,
            created_at=datetime.now(timezone.utc)
        )
        self.session.add(import_job)
        await self.session.commit()
        await self.session.refresh(import_job)

        try:
            import os
            allow_local = os.environ.get("ALLOW_LOCAL_IMPORT", "false").lower() == "true"

            if file_url.startswith(("http://", "https://")):
                async with httpx.AsyncClient() as client:
                    response = await client.get(file_url)
                    response.raise_for_status()
                    content = response.content
            elif allow_local:
                logger.warning(f"Local file import attempted and allowed for: {file_url}")
                with open(file_url, "rb") as f:
                    content = f.read()
            else:
                raise ValueError("Local file import is disabled or scheme is unsupported. Use a valid http/https URL.")

            df = self._parse_file(content, media_type, file_url)
            import_job.record_count = len(df)
            import_job.filename = file_url.split("/")[-1]
            df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]

            async with self.session.begin_nested():
                await self._process_dataframe(business_id, df)
            
            import_job.status = "COMPLETED"
            import_job.completed_at = datetime.now(timezone.utc)

        except Exception as e:
            logger.exception("Import failed")
            import_job.status = "FAILED"
            import_job.error_log = [{"error": str(e)}]
        
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
        for index, row in df.iterrows():
            name = row.get("name")
            if pd.isna(name):
                name = row.get("client_name") or row.get("customer_name")
            if not name:
                continue

            phone = str(row.get("phone", "")) if not pd.isna(row.get("phone")) else None
            if phone:
                phone = "".join(filter(str.isdigit, phone))

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
                await self.session.flush()

            if not pd.isna(row.get("address")):
                customer.street = row.get("address")
            if not pd.isna(row.get("city")):
                customer.city = row.get("city")
            if not pd.isna(row.get("notes")):
                customer.details = row.get("notes")

            if not pd.isna(row.get("job_description")) or not pd.isna(row.get("job_price")):
                job_status_raw = row.get("job_status", "PENDING")
                try:
                    job_status = JobStatus(str(job_status_raw).upper())
                except ValueError:
                    job_status = JobStatus.PENDING

                job = Job(
                    business_id=business_id,
                    customer_id=customer.id,
                    description=row.get("job_description"),
                    value=float(row.get("job_price", 0)) if not pd.isna(row.get("job_price")) else None,
                    status=job_status,
                    location=row.get("address")
                )
                self.session.add(job)

    async def _get_export_data(self, business_id: int, entity_type: str, query: str, filters: Dict[str, Any]) -> Tuple[pd.DataFrame, str]:
        min_date = None
        max_date = None
        if filters.get("min_date"):
            try:
                min_date = datetime.fromisoformat(filters["min_date"].replace("Z", "+00:00"))
            except ValueError: pass
        if filters.get("max_date"):
            try:
                max_date = datetime.fromisoformat(filters["max_date"].replace("Z", "+00:00"))
            except ValueError: pass

        data = []
        if entity_type == "job":
            headers = ["id", "customer", "description", "status", "value", "scheduled_at", "location", "created_at"]
            jobs = await self.job_repo.search(query=query, business_id=business_id, status=filters.get("status"), min_date=min_date, max_date=max_date, query_type="added")
            for j in jobs:
                data.append({
                    "id": j.id,
                    "customer": j.customer.name if j.customer else "",
                    "description": j.description,
                    "status": j.status,
                    "value": j.value,
                    "scheduled_at": j.scheduled_at,
                    "location": j.location or (j.customer.street if j.customer else ""),
                    "created_at": j.created_at
                })
            return pd.DataFrame(data, columns=headers), "jobs"

        elif entity_type == "request":
            headers = ["id", "customer", "description", "status", "urgency", "expected_value", "created_at"]
            from src.repositories import RequestRepository
            req_repo = RequestRepository(self.session)
            requests = await req_repo.search(query=query, business_id=business_id, status=filters.get("status"), min_date=min_date, max_date=max_date)
            for r in requests:
                data.append({
                    "id": r.id,
                    "customer": r.customer.name if r.customer else (r.customer_details.get("name") if r.customer_details else ""),
                    "description": r.description,
                    "status": r.status,
                    "urgency": r.urgency,
                    "expected_value": r.expected_value,
                    "created_at": r.created_at
                })
            return pd.DataFrame(data, columns=headers), "requests"

        elif entity_type == "expense":
            headers = ["date", "amount", "category", "description", "job_id"]
            stmt = select(Expense).where(Expense.business_id == business_id)
            if min_date: stmt = stmt.where(Expense.created_at >= min_date)
            if max_date: stmt = stmt.where(Expense.created_at <= max_date)
            result = await self.session.execute(stmt)
            for e in result.scalars().all():
                data.append({"date": e.created_at, "amount": e.amount, "category": e.category, "description": e.description, "job_id": e.job_id})
            return pd.DataFrame(data, columns=headers), "expenses"

        elif entity_type == "ledger":
            headers = ["date", "employee_id", "amount", "type", "description"]
            stmt = select(LedgerEntry).where(LedgerEntry.business_id == business_id)
            if min_date: stmt = stmt.where(LedgerEntry.created_at >= min_date)
            if max_date: stmt = stmt.where(LedgerEntry.created_at <= max_date)
            result = await self.session.execute(stmt)
            for le in result.scalars().all():
                data.append({"date": le.created_at, "employee_id": le.employee_id, "amount": le.amount, "type": le.entry_type, "description": le.description})
            return pd.DataFrame(data, columns=headers), "ledger"

        else: # customer
            headers = ["id", "name", "phone", "email", "address", "stage", "created_at"]
            customers = await self.customer_repo.search(query=query, business_id=business_id, entity_type=entity_type, pipeline_stage=filters.get("status"), min_date=min_date, max_date=max_date, query_type="added")
            for c in customers:
                data.append({"id": c.id, "name": c.name, "phone": c.phone, "email": c.email, "address": f"{c.street or ''} {c.city or ''}".strip(), "stage": c.pipeline_stage.value, "created_at": c.created_at})
            return pd.DataFrame(data, columns=headers), "customers"

    async def export_data(self, business_id: int, query: str, format: str, filters: Dict[str, Any] = None) -> ExportRequest:
        query = query or ""
        filters = filters or {}
        format = format.lower()
        
        export_req = ExportRequest(
            business_id=business_id,
            query=query,
            format=format, # Store lowercase to match enum values
            status=ExportStatus.PROCESSING,
            created_at=datetime.now(timezone.utc)
        )
        self.session.add(export_req)
        await self.session.commit() # Commit early so we have the record
        await self.session.refresh(export_req)

        try:
            entity_type = filters.get("entity_type")
            
            # Decide if we are doing a single file or a ZIP
            if format == "zip" or entity_type == "all" or (query.lower() == "all" and not entity_type):
                # Export EVERYTHING
                entities = ["customer", "job", "request", "expense", "ledger"]
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                    for ent in entities:
                        df, name = await self._get_export_data(business_id, ent, query, filters)
                        if not df.empty:
                            csv_buffer = io.BytesIO()
                            df.to_csv(csv_buffer, index=False)
                            zip_file.writestr(f"{name}.csv", csv_buffer.getvalue())
                
                zip_buffer.seek(0)
                file_bytes = zip_buffer.read()
                content_type = "application/zip"
                filename = f"export_all_{business_id}_{int(datetime.now().timestamp())}.zip"
                export_req.format = "zip"
            else:
                # Single file export
                df, name = await self._get_export_data(business_id, entity_type, query, filters)
                output = io.BytesIO()
                ext = "xlsx" if format == "excel" else "csv"
                filename = f"export_{name}_{business_id}_{int(datetime.now().timestamp())}.{ext}"
                
                if format == "excel":
                    for col in df.columns:
                        if pd.api.types.is_datetime64_any_dtype(df[col]):
                            df[col] = df[col].dt.tz_localize(None)
                    df.to_excel(output, index=False)
                    content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                else:
                    df.to_csv(output, index=False)
                    content_type = "text/csv"
                
                output.seek(0)
                file_bytes = output.read()

            s3_key = f"exports/{business_id}/{filename}"
            public_url = storage_service.upload_file(file_bytes, s3_key, content_type)

            export_req.s3_key = s3_key
            export_req.public_url = public_url
            export_req.status = ExportStatus.COMPLETED

        except Exception as e:
            logger.exception("Export failed")
            export_req.status = ExportStatus.FAILED
            export_req.error_log = str(e)
            
        await self.session.commit()
        return export_req
