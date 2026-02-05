"""Add index to Quote.job_id

Revision ID: a41c9c13cfb2
Revises: 41fcf56c35b7
Create Date: 2024-05-22 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a41c9c13cfb2'
down_revision: Union[str, None] = '41fcf56c35b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if index exists before creating to be safe (idempotent)
    # Using specific name 'ix_quotes_job_id'
    op.create_index(op.f('ix_quotes_job_id'), 'quotes', ['job_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_quotes_job_id'), table_name='quotes')
