"""merge_heads

Revision ID: f4d1f1ffa7ec
Revises: 4a2fe5d1fdc7, b68725d2ef2b
Create Date: 2026-01-19 17:12:15.030041

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4d1f1ffa7ec'
down_revision: Union[str, Sequence[str], None] = 'b68725d2ef2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
