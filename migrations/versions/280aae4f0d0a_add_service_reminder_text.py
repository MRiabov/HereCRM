"""add_service_reminder_text

Revision ID: 280aae4f0d0a
Revises: 2f48f87d4800
Create Date: 2026-01-21 16:29:47.949744

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '280aae4f0d0a'
down_revision: Union[str, Sequence[str], None] = '2f48f87d4800'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('services', sa.Column('reminder_text', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('services', 'reminder_text')
