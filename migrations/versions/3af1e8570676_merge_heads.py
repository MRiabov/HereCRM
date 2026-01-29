"""merge heads

Revision ID: 3af1e8570676
Revises: 11815ac16c52, 29f6693c5a19
Create Date: 2026-01-25 16:41:13.314480

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "3af1e8570676"
down_revision: Union[str, Sequence[str], None] = ("11815ac16c52", "29f6693c5a19")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
