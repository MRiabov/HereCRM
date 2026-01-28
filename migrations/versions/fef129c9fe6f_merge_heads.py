"""merge_heads

Revision ID: fef129c9fe6f
Revises: 29d4b35bbedf, d4289d247dac
Create Date: 2026-01-21 16:38:32.133382

"""
from typing import Sequence, Union



# revision identifiers, used by Alembic.
revision: str = 'fef129c9fe6f'
down_revision: Union[str, Sequence[str], None] = ('29d4b35bbedf', 'd4289d247dac')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
