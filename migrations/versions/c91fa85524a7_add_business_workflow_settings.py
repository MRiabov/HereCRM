"""add_business_workflow_settings

Revision ID: c91fa85524a7
Revises: a456cecc438a
Create Date: 2026-01-22 10:02:26.255810

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c91fa85524a7"
down_revision: Union[str, Sequence[str], None] = "a456cecc438a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("businesses", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "workflow_invoicing",
                sa.Enum("NEVER", "MANUAL", "AUTOMATIC", name="invoicingworkflow"),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "workflow_quoting",
                sa.Enum("NEVER", "MANUAL", "AUTOMATIC", name="quotingworkflow"),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "workflow_payment_timing",
                sa.Enum(
                    "ALWAYS_PAID_ON_SPOT",
                    "USUALLY_PAID_ON_SPOT",
                    "PAID_LATER",
                    name="paymenttiming",
                ),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column("workflow_tax_inclusive", sa.Boolean(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("workflow_include_payment_terms", sa.Boolean(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("workflow_enable_reminders", sa.Boolean(), nullable=True)
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("businesses", schema=None) as batch_op:
        batch_op.drop_column("workflow_enable_reminders")
        batch_op.drop_column("workflow_include_payment_terms")
        batch_op.drop_column("workflow_tax_inclusive")
        batch_op.drop_column("workflow_payment_timing")
        batch_op.drop_column("workflow_quoting")
        batch_op.drop_column("workflow_invoicing")
