"""merge quote restoration

Revision ID: 2e4dc444ed6e
Revises: 4224dc58bdff, 69f121de1709
Create Date: 2026-01-21 07:04:57.210145

"""
from typing import Sequence, Union



# revision identifiers, used by Alembic.
revision: str = '2e4dc444ed6e'
down_revision: Union[str, Sequence[str], None] = ('4224dc58bdff', '69f121de1709')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
