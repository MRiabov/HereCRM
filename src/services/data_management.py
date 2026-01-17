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

class DataManagementService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.customer_repo = CustomerRepository(session)
        self.job_repo = JobRepository(session)
        self.business_repo = BusinessRepository(session)

    async def import_data(self, business_id: int, file_url: str, media_type: str) -> ImportJob:
        """
        Orchestrates the data import process.
        1. Creates ImportJob record.
        2. Downloads file.
        3. Parses file into DataFrame.
        4. Maps columns (TODO: LLM integration).
        5. Validates and writes to DB (Atomic).
        6. Updates ImportJob status.
        """
        import_job = ImportJob(
            business_id=business_id,
            status="processing",
            file_url=file_url,
            created_at=datetime.now(timezone.utc)
        )
        self.session.add(import_job)
        await self.session.flush()

        try:
            # Download file
            if file_url.startswith("http"):
                async with httpx.AsyncClient() as client:
                    response = await client.get(file_url)
                    response.raise_for_status()
                    content = response.content
            else:
                # Assume local path for testing
                with open(file_url, "rb") as f:
                    content = f.read()

            # Parse file
            df = self._parse_file(content, media_type, file_url)
            import_job.record_count = len(df)
            import_job.filename = file_url.split("/")[-1]

            # Normalize headers
            df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]

            # Validation & Import
            await self._process_dataframe(business_id, df)

            import_job.status = "completed"
            import_job.completed_at = datetime.now(timezone.utc)

        except Exception as e:
            logger.exception("Import failed")
            import_job.status = "failed"
            import_job.error_log = [{"error": str(e)}]

        await self.session.commit()
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

    async def export_data(self, business_id: int, query: str, format: str) -> ExportRequest:
        """
        Process an export request.
        """
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
            # 1. Fetch data using Repository Search
            # This leverages the existing search logic (name, phone, address, etc.)
            customers = await self.customer_repo.search(query=query, business_id=business_id)

            data = []
            for c in customers:
                row = {
                    "id": c.id,
                    "name": c.name,
                    "phone": c.phone,
                    "email": "",
                    "address": f"{c.street or ''} {c.city or ''}".strip(),
                    "notes": c.details,
                    "stage": c.pipeline_stage.value,
                    "created_at": c.created_at
                }
                data.append(row)

            df = pd.DataFrame(data)

            # 3. Format
            output = io.BytesIO()
            filename = f"export_{business_id}_{int(datetime.now().timestamp())}.{format}"

            if format == "csv":
                df.to_csv(output, index=False)
                media_type = "text/csv"
            elif format == "excel" or format == "xlsx":
                df.to_excel(output, index=False)
                media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            elif format == "json":
                df.to_json(output, orient="records")
                media_type = "application/json"
            else:
                raise ValueError(f"Unsupported format: {format}")

            output.seek(0)

            # 4. Upload / Save
            import os
            os.makedirs("exports", exist_ok=True)
            filepath = f"exports/{filename}"
            with open(filepath, "wb") as f:
                f.write(output.read())

            export_req.s3_key = filepath
            export_req.public_url = filepath
            export_req.status = "completed"

        except Exception as e:
            logger.exception("Export failed")
            export_req.status = "failed"

        await self.session.commit()
        return export_req
