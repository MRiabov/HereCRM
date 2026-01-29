import os
import sys


# Add src to path
sys.path.append(os.getcwd())

from src.database import Base
from src.models import *


def init_db():
    # Sync engine (force it to be sync for this script)
    from sqlalchemy import create_engine

    sync_engine = create_engine("sqlite:///./crm.db")
    Base.metadata.create_all(sync_engine)
    print("Database initialized from models.")


if __name__ == "__main__":
    init_db()
