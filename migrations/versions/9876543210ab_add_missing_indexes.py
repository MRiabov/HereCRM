"""Add missing indexes

Revision ID: 9876543210ab
Revises: 3af1e8570676
Create Date: 2026-02-18 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9876543210ab'
down_revision: Union[str, Sequence[str], None] = '3af1e8570676'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ImportJobs
    with op.batch_alter_table('import_jobs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_import_jobs_business_id'), ['business_id'], unique=False)

    # ExportRequests
    with op.batch_alter_table('export_requests', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_export_requests_business_id'), ['business_id'], unique=False)

    # LineItems
    with op.batch_alter_table('line_items', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_line_items_service_id'), ['service_id'], unique=False)

    # Quotes
    with op.batch_alter_table('quotes', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_quotes_job_id'), ['job_id'], unique=False)

    # QuoteLineItems
    with op.batch_alter_table('quote_line_items', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_quote_line_items_service_id'), ['service_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('quote_line_items', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_quote_line_items_service_id'))

    with op.batch_alter_table('quotes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_quotes_job_id'))

    with op.batch_alter_table('line_items', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_line_items_service_id'))

    with op.batch_alter_table('export_requests', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_export_requests_business_id'))

    with op.batch_alter_table('import_jobs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_import_jobs_business_id'))
