"""add invitation model and employee_management state

Revision ID: ad818d00657c
Revises: 88899353ad93
Create Date: 2026-01-22 19:54:26.739118

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ad818d00657c"
down_revision: Union[str, Sequence[str], None] = "88899353ad93"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
