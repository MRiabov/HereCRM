from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Text, DateTime, Integer, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import StaticPool
import os
import logging

# Try to import pysqlcipher3, but handle gracefully if not available
try:
    import pysqlcipher3.dbapi2 as sqlite
    PYSQLCIPHER_AVAILABLE = True
except ImportError:
    PYSQLCIPHER_AVAILABLE = False
    logging.warning("pysqlcipher3 not available - QuickBooks credentials encryption disabled")


class CredentialsBase(DeclarativeBase):
    pass


class QuickBooksCredential(CredentialsBase):
    __tablename__ = "quickbooks_credentials"
    
    # Primary key is business_id (one-to-one with Business in main DB)
    business_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # QuickBooks OAuth data
    realm_id: Mapped[str] = mapped_column(String(50), nullable=False)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    token_expiry: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Metadata
    connected_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )


# Only create credentials engine if pysqlcipher3 is available
credentials_engine = None
CredentialsSessionLocal = None

if PYSQLCIPHER_AVAILABLE:
    CREDENTIALS_DB_KEY = os.getenv("CREDENTIALS_DB_KEY")
    if not CREDENTIALS_DB_KEY:
        logging.warning("CREDENTIALS_DB_KEY environment variable is required for QuickBooks integration")
    else:
        try:
            credentials_engine = create_engine(
                f"sqlite+pysqlcipher://:{CREDENTIALS_DB_KEY}@/credentials.db?cipher=aes-256-cfb&kdf_iter=64000",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool
            )
            
            # Create tables
            CredentialsBase.metadata.create_all(credentials_engine)
            logging.info("Credentials database configured successfully")
            
        except Exception as e:
            logging.error(f"Failed to configure credentials database: {e}")
            credentials_engine = None
else:
    logging.info("QuickBooks credentials encryption disabled - install sqlcipher system libraries")
