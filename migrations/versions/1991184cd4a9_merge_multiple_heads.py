"""merge multiple heads

Revision ID: 1991184cd4a9
Revises: 10459a154086, a1b2c3d4e5f6
Create Date: 2026-01-27 18:59:23.476184

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1991184cd4a9'
down_revision: Union[str, Sequence[str], None] = ('10459a154086', 'a1b2c3d4e5f6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
