"""fix_users_table_schema

Revision ID: 108020504ecb
Revises: 271d1fde1f13
Create Date: 2026-01-29 12:11:23.981282

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '108020504ecb'
down_revision: Union[str, Sequence[str], None] = '271d1fde1f13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
