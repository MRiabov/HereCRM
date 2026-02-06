"""Add Stripe fields

Revision ID: a1b2c3d4e5f6
Revises: 0d406bfab98f
Create Date: 2026-01-17 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "0d406bfab98f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Business fields
    op.add_column("businesses", sa.Column("stripe_account_id", sa.String(), nullable=True))
    op.add_column("businesses", sa.Column("legal_name", sa.String(), nullable=True))
    op.add_column("businesses", sa.Column("legal_address", sa.JSON(), nullable=True))
    op.add_column("businesses", sa.Column("tax_id", sa.String(), nullable=True))

    # Invoice fields
    op.add_column("invoices", sa.Column("stripe_session_id", sa.String(), nullable=True))
    op.add_column("invoices", sa.Column("payment_date", sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Invoice fields
    op.drop_column("invoices", "payment_date")
    op.drop_column("invoices", "stripe_session_id")

    # Business fields
    op.drop_column("businesses", "tax_id")
    op.drop_column("businesses", "legal_address")
    op.drop_column("businesses", "legal_name")
    op.drop_column("businesses", "stripe_account_id")
