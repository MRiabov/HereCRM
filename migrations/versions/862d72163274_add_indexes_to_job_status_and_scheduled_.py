"""Add indexes to Job status and scheduled_at

Revision ID: 862d72163274
Revises: 41fcf56c35b7
Create Date: 2026-02-01 17:25:49.353206

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '862d72163274'
down_revision: Union[str, Sequence[str], None] = '41fcf56c35b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_jobs_status"), ["status"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_jobs_scheduled_at"), ["scheduled_at"], unique=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_jobs_scheduled_at"))
        batch_op.drop_index(batch_op.f("ix_jobs_status"))
