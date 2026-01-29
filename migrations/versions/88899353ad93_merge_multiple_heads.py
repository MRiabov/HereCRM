"""merge multiple heads

Revision ID: 88899353ad93
Revises: 1ea69c57842f, 4585b682f5c3, e6aaeed9435c
Create Date: 2026-01-22 19:53:46.807853

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "88899353ad93"
down_revision: Union[str, Sequence[str], None] = (
    "1ea69c57842f",
    "4585b682f5c3",
    "e6aaeed9435c",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
