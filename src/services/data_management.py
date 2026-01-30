import logging
import pandas as pd
import io
import httpx
import zipfile
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models import (
    Customer,
    Job,
    ImportJob,
    ExportRequest,
    PipelineStage,
    Expense,
    LedgerEntry,
    Quote,
    Request,
    ExportStatus,
    JobStatus,
    ExportFormat,
    EntityType,
    ImportStatus,
    User,
    QuoteStatus,
    ExpenseCategory,
)
from src.repositories import BusinessRepository, CustomerRepository, JobRepository
from src.services.storage import storage_service

logger = logging.getLogger(__name__)


class DataManagementService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.customer_repo = CustomerRepository(session)
        self.job_repo = JobRepository(session)
        self.business_repo = BusinessRepository(session)

    async def import_data(
        self,
        business_id: int,
        file_url: str,
        media_type: str,
        entity_type: EntityType = EntityType.CUSTOMER,
    ) -> ImportJob:
        """
        Orchestrates the data import process.
        """
        import_job = ImportJob(
            business_id=business_id,
            status=ImportStatus.PROCESSING,
            file_url=file_url,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(import_job)
        await self.session.commit()
        await self.session.refresh(import_job)

        try:
            import os

            allow_local = (
                os.environ.get("ALLOW_LOCAL_IMPORT", "false").lower() == "true"
            )

            if file_url.startswith(("http://", "https://")):
                async with httpx.AsyncClient() as client:
                    response = await client.get(file_url)
                    response.raise_for_status()
                    content = response.content
            elif allow_local:
                logger.warning(
                    f"Local file import attempted and allowed for: {file_url}"
                )
                with open(file_url, "rb") as f:
                    content = f.read()
            else:
                raise ValueError(
                    "Local file import is disabled or scheme is unsupported. Use a valid http/https URL."
                )

            df = self._parse_file(content, media_type, file_url)
            import_job.record_count = len(df)
            import_job.filename = file_url.split("/")[-1]
            df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]

            async with self.session.begin_nested():
                await self._process_dataframe(business_id, df, entity_type)

            import_job.status = ImportStatus.COMPLETED
            import_job.completed_at = datetime.now(timezone.utc)

        except Exception as e:
            logger.exception("Import failed")
            import_job.status = ImportStatus.FAILED
            import_job.error_log = [{"error": str(e)}]

        await self.session.commit()
        await self.session.refresh(import_job)
        return import_job

    def _parse_file(
        self, content: bytes, media_type: str, filename: str
    ) -> pd.DataFrame:
        if "csv" in media_type or filename.endswith(".csv"):
            return pd.read_csv(io.BytesIO(content))
        elif (
            "excel" in media_type
            or "spreadsheet" in media_type
            or filename.endswith(".xlsx")
        ):
            return pd.read_excel(io.BytesIO(content))
        elif "json" in media_type or filename.endswith(".json"):
            return pd.read_json(io.BytesIO(content))
        else:
            raise ValueError(f"Unsupported file format: {media_type}")

    async def _process_dataframe(
        self, business_id: int, df: pd.DataFrame, entity_type: EntityType
    ):
        if entity_type == EntityType.CUSTOMER:
            await self._process_customers_df(business_id, df)
        elif entity_type == EntityType.JOB:
            await self._process_jobs_df(business_id, df)
        elif entity_type == EntityType.QUOTE:
            await self._process_quotes_df(business_id, df)
        elif entity_type == EntityType.REQUEST:
            await self._process_requests_df(business_id, df)
        elif entity_type == EntityType.EXPENSE:
            await self._process_expenses_df(business_id, df)
        elif entity_type == EntityType.INVOICE:
            await self._process_invoices_df(business_id, df)
        else:
            # Fallback to the old logic if type is unknown or generic
            for index, row in df.iterrows():
                await self._process_generic_row(business_id, row)

    async def _process_customers_df(self, business_id: int, df: pd.DataFrame):
        for _, row in df.iterrows():
            await self._process_customer_row(business_id, row)

    async def _process_jobs_df(self, business_id: int, df: pd.DataFrame):
        for _, row in df.iterrows():
            customer = await self._get_or_create_customer_from_row(business_id, row)
            if not customer:
                continue
            job = Job(
                business_id=business_id,
                customer_id=customer.id,
                description=row.get("description") or row.get("job_description"),
                value=float(row.get("value") or row.get("job_price") or 0),
                status=JobStatus.PENDING,
                location=row.get("address") or customer.street,
            )
            self.session.add(job)

    async def _process_quotes_df(self, business_id: int, df: pd.DataFrame):
        for _, row in df.iterrows():
            customer = await self._get_or_create_customer_from_row(business_id, row)
            if not customer:
                continue
            quote = Quote(
                business_id=business_id,
                customer_id=customer.id,
                description=row.get("description") or row.get("quote_description"),
                total_amount=float(row.get("total_price") or row.get("amount") or 0),
                status=QuoteStatus.DRAFT,
                external_token=str(uuid.uuid4()),
            )
            self.session.add(quote)

    async def _process_requests_df(self, business_id: int, df: pd.DataFrame):
        for _, row in df.iterrows():
            customer = await self._get_or_create_customer_from_row(business_id, row)
            request = Request(
                business_id=business_id,
                customer_id=customer.id if customer else None,
                description=row.get("description") or row.get("details"),
                status="PENDING",
            )
            self.session.add(request)

    async def _process_expenses_df(self, business_id: int, df: pd.DataFrame):
        # We need an employee_id for Expense. We'll try to find one.
        stmt = select(User).where(User.business_id == business_id).limit(1)
        res = await self.session.execute(stmt)
        default_user = res.scalars().first()

        for _, row in df.iterrows():
            cat_raw = row.get("category") or "General"
            try:
                category = ExpenseCategory(str(cat_raw).upper())
            except ValueError:
                category = ExpenseCategory.OTHER

            expense = Expense(
                business_id=business_id,
                amount=float(row.get("amount") or row.get("total") or 0),
                description=row.get("description") or row.get("vendor"),
                category=category,
                employee_id=default_user.id if default_user else None,
            )
            self.session.add(expense)

    async def _process_invoices_df(self, business_id: int, df: pd.DataFrame):
        # Invoices usually need a job. This is a bit complex for a simple CSV import
        # but we'll try to find a job or just create a record if possible.
        # For now, let's keep it simple.
        for index, row in df.iterrows():
            logger.warning(f"Invoice import not fully implemented for row {index}")

    async def _get_or_create_customer_from_row(self, business_id: int, row: pd.Series):
        name = row.get("name") or row.get("client_name") or row.get("customer_name")
        if not name or pd.isna(name):
            return None

        phone_val = row.get("phone")
        phone = str(phone_val) if not pd.isna(phone_val) else None
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
                pipeline_stage=PipelineStage.NOT_CONTACTED,
                street=row.get("address")
                or row.get("street")
                or row.get("address_line_1"),
                city=row.get("city"),
                details=row.get("notes") or row.get("details"),
            )
            self.session.add(customer)
            await self.session.flush()

        return customer

    async def _process_customer_row(self, business_id: int, row: pd.Series):
        await self._get_or_create_customer_from_row(business_id, row)

    async def _process_generic_row(self, business_id: int, row: pd.Series):
        # Legacy behavior: Customer + Job
        customer = await self._get_or_create_customer_from_row(business_id, row)
        if not customer:
            return

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
                value=float(row.get("job_price", 0))
                if not pd.isna(row.get("job_price"))
                else None,
                status=job_status,
                location=row.get("address") or customer.street,
            )
            self.session.add(job)

    async def _get_export_data(
        self,
        business_id: int,
        entity_type: Optional[EntityType],
        query: str,
        filters: Optional[Dict[str, Any]],
    ) -> Tuple[pd.DataFrame, str]:
        min_date = None
        max_date = None
        filters = filters or {}

        if filters.get("min_date"):
            try:
                min_date = datetime.fromisoformat(
                    filters["min_date"].replace("Z", "+00:00")
                )
            except ValueError:
                pass
        if filters.get("max_date"):
            try:
                max_date = datetime.fromisoformat(
                    filters["max_date"].replace("Z", "+00:00")
                )
            except ValueError:
                pass

        if not entity_type:
            entity_type = EntityType.CUSTOMER

        data = []
        if entity_type == EntityType.JOB:
            headers = [
                "id",
                "customer",
                "description",
                "status",
                "value",
                "scheduled_at",
                "location",
                "created_at",
            ]
            jobs = await self.job_repo.search(
                query=query,
                business_id=business_id,
                status=filters.get("status"),
                min_date=min_date,
                max_date=max_date,
                query_type="ADDED",
            )
            for j in jobs:
                data.append(
                    {
                        "id": j.id,
                        "customer": j.customer.name if j.customer else "",
                        "description": j.description,
                        "status": j.status,
                        "value": j.value,
                        "scheduled_at": j.scheduled_at,
                        "location": j.location
                        or (j.customer.street if j.customer else ""),
                        "created_at": j.created_at,
                    }
                )
            return pd.DataFrame(data, columns=headers), "jobs"

        elif entity_type == EntityType.REQUEST:
            headers = [
                "id",
                "customer",
                "description",
                "status",
                "urgency",
                "expected_value",
                "created_at",
            ]
            from src.repositories import RequestRepository

            req_repo = RequestRepository(self.session)
            requests = await req_repo.search(
                query=query,
                business_id=business_id,
                status=filters.get("status"),
                min_date=min_date,
                max_date=max_date,
            )
            for r in requests:
                data.append(
                    {
                        "id": r.id,
                        "customer": r.customer.name
                        if r.customer
                        else (
                            r.customer_details.get("name") if r.customer_details else ""
                        ),
                        "description": r.description,
                        "status": r.status,
                        "urgency": r.urgency,
                        "expected_value": r.expected_value,
                        "created_at": r.created_at,
                    }
                )
            return pd.DataFrame(data, columns=headers), "requests"

        elif entity_type == EntityType.EXPENSE:
            headers = ["date", "amount", "category", "description", "job_id"]
            stmt = select(Expense).where(Expense.business_id == business_id)
            if min_date:
                stmt = stmt.where(Expense.created_at >= min_date)
            if max_date:
                stmt = stmt.where(Expense.created_at <= max_date)
            result = await self.session.execute(stmt)
            for e in result.scalars().all():
                data.append(
                    {
                        "date": e.created_at,
                        "amount": e.amount,
                        "category": e.category,
                        "description": e.description,
                        "job_id": e.job_id,
                    }
                )
            return pd.DataFrame(data, columns=headers), "expenses"

        elif entity_type == EntityType.LEDGER:
            headers = ["date", "employee_id", "amount", "type", "description"]
            stmt = select(LedgerEntry).where(LedgerEntry.business_id == business_id)
            if min_date:
                stmt = stmt.where(LedgerEntry.created_at >= min_date)
            if max_date:
                stmt = stmt.where(LedgerEntry.created_at <= max_date)
            result = await self.session.execute(stmt)
            for le in result.scalars().all():
                data.append(
                    {
                        "date": le.created_at,
                        "employee_id": le.employee_id,
                        "amount": le.amount,
                        "type": le.entry_type,
                        "description": le.description,
                    }
                )
            return pd.DataFrame(data, columns=headers), "ledger"

        else:  # customer
            headers = ["id", "name", "phone", "email", "address", "stage", "created_at"]
            # Fallback to customer if entity_type is None or something else
            e_type = entity_type.value if entity_type else "customer"
            customers = await self.customer_repo.search(
                query=query,
                business_id=business_id,
                entity_type=e_type,
                pipeline_stage=filters.get("status"),
                min_date=min_date,
                max_date=max_date,
                query_type="ADDED",
            )
            for c in customers:
                data.append(
                    {
                        "id": c.id,
                        "name": c.name,
                        "phone": c.phone,
                        "email": c.email,
                        "address": f"{c.street or ''} {c.city or ''}".strip(),
                        "stage": c.pipeline_stage.value,
                        "created_at": c.created_at,
                    }
                )
            return pd.DataFrame(data, columns=headers), "customers"

    async def export_data(
        self,
        business_id: int,
        query: str,
        format: ExportFormat,
        filters: Optional[Dict[str, Any]] = None,
    ) -> ExportRequest:
        query = query or ""
        filters = filters or {}

        export_req = ExportRequest(
            business_id=business_id,
            query=query or "",
            format=format,  # Store as enum member
            status=ExportStatus.PROCESSING,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(export_req)
        await self.session.commit()  # Commit early so we have the record
        await self.session.refresh(export_req)

        try:
            filters = filters or {}
            entity_type_raw = filters.get("entity_type")
            if entity_type_raw:
                try:
                    # RobustEnum handles casing via _missing_
                    entity_type = EntityType(entity_type_raw)
                except ValueError:
                    entity_type = EntityType.CUSTOMER
            else:
                entity_type = None

            # Decide if we are doing a single file or a ZIP
            if (
                format == ExportFormat.ZIP
                or entity_type == EntityType.ALL
                or (query.lower() == "all" and not entity_type)
            ):
                # Export EVERYTHING
                entities = [
                    EntityType.CUSTOMER,
                    EntityType.JOB,
                    EntityType.REQUEST,
                    EntityType.EXPENSE,
                    EntityType.LEDGER,
                ]
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(
                    zip_buffer, "a", zipfile.ZIP_DEFLATED, False
                ) as zip_file:
                    for ent in entities:
                        df, name = await self._get_export_data(
                            business_id, ent, query, filters
                        )
                        if not df.empty:
                            csv_buffer = io.BytesIO()
                            df.to_csv(csv_buffer, index=False)
                            zip_file.writestr(f"{name}.csv", csv_buffer.getvalue())

                zip_buffer.seek(0)
                file_bytes = zip_buffer.read()
                content_type = "application/zip"
                filename = (
                    f"export_all_{business_id}_{int(datetime.now().timestamp())}.zip"
                )
                export_req.format = ExportFormat.ZIP
            else:
                # Single file export
                df, name = await self._get_export_data(
                    business_id, entity_type, query, filters
                )
                output = io.BytesIO()

                if format == ExportFormat.EXCEL:
                    ext = "xlsx"
                    for col in df.columns:
                        if pd.api.types.is_datetime64_any_dtype(df[col]):
                            df[col] = df[col].dt.tz_localize(None)
                    df.to_excel(output, index=False)
                    content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                elif format == ExportFormat.JSON:
                    ext = "json"
                    df.to_json(output, orient="records", date_format="iso")
                    content_type = "application/json"
                else:
                    ext = "csv"
                    df.to_csv(output, index=False)
                    content_type = "text/csv"

                filename = f"export_{name}_{business_id}_{int(datetime.now().timestamp())}.{ext}"
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

    async def backup_db(self) -> str:
        """
        Creates a backup of the SQLite database and uploads it to S3.
        Using sqlite3's backup method for safety.
        """
        import sqlite3
        import os
        from src.database import DATABASE_URL

        # Extract file path from URL
        db_path = DATABASE_URL.split("///")[-1]
        if ":memory:" in db_path:
            raise ValueError("Cannot backup in-memory database")

        backup_path = f"{db_path}.backup"

        # SQLite backup using standard library
        try:
            # We connect to the source DB file
            src = sqlite3.connect(db_path)
            # Create a backup DB file
            dst = sqlite3.connect(backup_path)
            with dst:
                src.backup(dst)
            dst.close()
            src.close()

            # Read the backup file
            with open(backup_path, "rb") as f:
                content = f.read()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            s3_key = f"backups/crm_db_{timestamp}.sqlite"

            # Upload to S3
            public_url = storage_service.upload_file(
                content, s3_key, "application/x-sqlite3"
            )

            # Clean up local backup file
            os.remove(backup_path)

            return public_url

        except Exception as e:
            if os.path.exists(backup_path):
                os.remove(backup_path)
            logger.exception("Database backup failed")
            raise e
