"""merge heads

Revision ID: 2f48f87d4800
Revises: 29d4b35bbedf, d4289d247dac
Create Date: 2026-01-21 16:29:37.434831

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2f48f87d4800'
down_revision: Union[str, Sequence[str], None] = ('29d4b35bbedf', 'd4289d247dac')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
