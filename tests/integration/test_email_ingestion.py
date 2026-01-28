import base64
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.main import app
from src.database import get_db, Base
from src.config import settings
from src.models import Document, Customer, Business, SubscriptionStatus, PipelineStage
from unittest.mock import patch

# In-memory DB for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine_test = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(
    bind=engine_test, class_=AsyncSession, expire_on_commit=False
)

@pytest.fixture
async def db_session():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_postmark_email_ingestion_with_attachments(db_session):
    # Override get_db
    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Setup Auth
    settings.postmark_auth_user = "test_user"
    settings.postmark_auth_pass = "test_pass"
    
    # Create Business and Customer
    async with TestingSessionLocal() as prep_session:
        business = Business(name="Test Biz", subscription_status=SubscriptionStatus.ACTIVE)
        prep_session.add(business)
        await prep_session.flush()
        
        customer_email = "upload@customer.com"
        customer = Customer(
            name="Test Upload Customer",
            business_id=business.id,
            email=customer_email,
            pipeline_stage=PipelineStage.CONTACTED, 
        )
        prep_session.add(customer)
        
        # Create User to ensure business_id match
        from src.models import User, UserRole
        user = User(
            name="Test User",
            email=customer_email,
            phone_number="+15555555555",
            business_id=business.id,
            role=UserRole.EMPLOYEE
        )
        prep_session.add(user)
        
        await prep_session.commit()
        customer_id = customer.id

    # Payload with attachment
    file_content = b"Hello World"
    b64_content = base64.b64encode(file_content).decode('utf-8')
    
    payload = {
        "From": customer_email,
        "Subject": "Invoice Attachment",
        "TextBody": "Please find attached.",
        "MessageID": "msg-12345",
        "Attachments": [
            {
                "Name": "invoice.pdf",
                "Content": b64_content,
                "ContentType": "application/pdf",
                "ContentID": "cid:123"
            }
        ]
    }
    
    with patch("src.services.document_service.storage_service") as mock_storage:
        mock_storage.upload_file.return_value = "https://s3.example.com/invoice.pdf"
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/webhooks/postmark/inbound",
                json=payload,
                auth=("test_user", "test_pass")
            )
            
            assert response.status_code == 200, response.text
            data = response.json()
            assert data["status"] == "SUCCESS"
        
        # Verify Document Created
        async with TestingSessionLocal() as verify_session:
            from sqlalchemy import select
            stmt = select(Document).where(Document.customer_id == customer_id)
            result = await verify_session.execute(stmt)
            docs = result.scalars().all()
            
            assert len(docs) == 1
            assert docs[0].filename == "invoice.pdf"
            assert docs[0].public_url == "https://s3.example.com/invoice.pdf"

@pytest.mark.asyncio
async def test_postmark_email_ingestion_complex_from_header(db_session):
    """
    Verifies that 'From' headers like 'Name <email>' are parsed correctly.
    """
    # Override get_db
    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session
    
    app.dependency_overrides[get_db] = override_get_db
    settings.postmark_auth_user = "test_user"
    settings.postmark_auth_pass = "test_pass"
    
    complex_email = "complex@customer.com"
    full_from = f"Mr. Complex <{complex_email}>"
    
    # Payload
    payload = {
        "From": full_from,
        "Subject": "Hello",
        "TextBody": "Testing complex header.",
        "MessageID": "msg-complex"
    }
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/webhooks/postmark/inbound",
            json=payload,
            auth=("test_user", "test_pass")
        )
        assert response.status_code == 200
        
    # Verify User Created with correct email
    async with TestingSessionLocal() as verify_session:
        from src.repositories import UserRepository
        user_repo = UserRepository(verify_session)
        user = await user_repo.get_by_email(complex_email)
        
        assert user is not None
        assert user.email == complex_email
