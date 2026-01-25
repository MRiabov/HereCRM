"""add_clerk_ids

Revision ID: 29f6693c5a19
Revises: b95d17b4d850
Create Date: 2026-01-24 21:15:23.785180

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '29f6693c5a19'
down_revision: Union[str, Sequence[str], None] = 'b95d17b4d850'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('businesses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('clerk_org_id', sa.String(), nullable=True))
        batch_op.create_unique_constraint('uq_businesses_clerk_org_id', ['clerk_org_id'])

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('clerk_id', sa.String(), nullable=True))
        batch_op.create_unique_constraint('uq_users_clerk_id', ['clerk_id'])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint('uq_users_clerk_id', type_='unique')
        batch_op.drop_column('clerk_id')

    with op.batch_alter_table('businesses', schema=None) as batch_op:
        batch_op.drop_constraint('uq_businesses_clerk_org_id', type_='unique')
        batch_op.drop_column('clerk_org_id')
