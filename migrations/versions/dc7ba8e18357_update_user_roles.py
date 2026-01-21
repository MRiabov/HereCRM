"""update_user_roles

Revision ID: dc7ba8e18357
Revises: fef129c9fe6f
Create Date: 2026-01-21 16:38:40.484607

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc7ba8e18357'
down_revision: Union[str, Sequence[str], None] = 'fef129c9fe6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Commit required for ALTER TYPE in some PG versions/configurations if inside transaction block,
    # but Alembic usually handles it. However, ALTER TYPE ADD VALUE cannot run inside a transaction block 
    # unless it's the only statement or similar, actually "ALTER TYPE ... ADD VALUE cannot run inside a transaction block" 
    # is a restriction for some older PG versions or specific cases.
    # Actually, "ALTER TYPE ... ADD VALUE" CANNOT be run in a transaction block prior to Postgres 12.
    # Assuming PG 12+.
    # But to be safe, we can use `op.execute` with `execution_options={"isolation_level": "AUTOCOMMIT"}` if needed.
    # But usually simple op.execute works if PG is modern.
    
    # Rename member to employee
    op.execute("ALTER TYPE userrole RENAME VALUE 'member' TO 'employee'")
    # Add manager
    op.execute("ALTER TYPE userrole ADD VALUE 'manager'")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TYPE userrole RENAME VALUE 'employee' TO 'member'")
    # Cannot remove 'manager'

