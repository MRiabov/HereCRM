"""add_billing_fields_to_business

Revision ID: 69f121de1709
Revises: 5badbf80194d
Create Date: 2026-01-20 15:36:54.328757

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '69f121de1709'
down_revision: Union[str, Sequence[str], None] = '5badbf80194d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('businesses', sa.Column('stripe_customer_id', sa.String(), nullable=True))
    op.add_column('businesses', sa.Column('stripe_subscription_id', sa.String(), nullable=True))
    op.add_column('businesses', sa.Column('subscription_status', sa.String(), nullable=False, server_default='free'))
    op.add_column('businesses', sa.Column('seat_limit', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('businesses', sa.Column('active_addons', sa.JSON(), nullable=False, server_default='[]'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('businesses', 'active_addons')
    op.drop_column('businesses', 'seat_limit')
    op.drop_column('businesses', 'subscription_status')
    op.drop_column('businesses', 'stripe_subscription_id')
    op.drop_column('businesses', 'stripe_customer_id')
