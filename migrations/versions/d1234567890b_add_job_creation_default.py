"""add_job_creation_default

Revision ID: d1234567890b
Revises: 3af1e8570676
Create Date: 2026-01-25 21:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1234567890b'
down_revision: Union[str, Sequence[str], None] = '3af1e8570676'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('businesses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('workflow_job_creation_default', sa.Enum('MARK_DONE', 'UNSCHEDULED', 'AUTO_SCHEDULE', name='jobcreationdefault'), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('businesses', schema=None) as batch_op:
        batch_op.drop_column('workflow_job_creation_default')
