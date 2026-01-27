"""Add indexes to Foreign Keys

Revision ID: a1b2c3d4e5f6
Revises: fef129c9fe6f
Create Date: 2026-01-27 17:12:36.986436

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'fef129c9fe6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('expenses', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_expenses_job_id'), ['job_id'], unique=False)

    with op.batch_alter_table('ledger_entries', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_ledger_entries_job_id'), ['job_id'], unique=False)

    with op.batch_alter_table('line_items', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_line_items_service_id'), ['service_id'], unique=False)

    with op.batch_alter_table('quote_line_items', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_quote_line_items_service_id'), ['service_id'], unique=False)

    with op.batch_alter_table('import_jobs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_import_jobs_business_id'), ['business_id'], unique=False)

    with op.batch_alter_table('export_requests', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_export_requests_business_id'), ['business_id'], unique=False)

    with op.batch_alter_table('invitations', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_invitations_inviter_id'), ['inviter_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('invitations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_invitations_inviter_id'))

    with op.batch_alter_table('export_requests', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_export_requests_business_id'))

    with op.batch_alter_table('import_jobs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_import_jobs_business_id'))

    with op.batch_alter_table('quote_line_items', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_quote_line_items_service_id'))

    with op.batch_alter_table('line_items', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_line_items_service_id'))

    with op.batch_alter_table('ledger_entries', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_ledger_entries_job_id'))

    with op.batch_alter_table('expenses', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_expenses_job_id'))
