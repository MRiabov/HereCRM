"""refactor_user_pk_and_add_email

Revision ID: 5badbf80194d
Revises: f4d1f1ffa7ec
Create Date: 2026-01-19 17:13:05.578912

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5badbf80194d"
down_revision: Union[str, Sequence[str], None] = "f4d1f1ffa7ec"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create new users table
    op.create_table(
        "users_new",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("phone_number", sa.String(), unique=True, nullable=True),
        sa.Column("email", sa.String(), unique=True, nullable=True),
        sa.Column(
            "business_id", sa.Integer(), sa.ForeignKey("businesses.id"), nullable=False
        ),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("preferences", sa.JSON(), nullable=False),
        sa.Column("timezone", sa.String(), nullable=False),
    )

    # Copy data to users_new. SQLite auto-populates 'id'.
    op.execute("""
        INSERT INTO users_new (phone_number, business_id, role, created_at, preferences, timezone)
        SELECT phone_number, business_id, role, created_at, preferences, timezone FROM users
    """)

    # 2. Create new conversation_states table
    op.create_table(
        "conversation_states_new",
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users_new.id"), primary_key=True
        ),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("draft_data", sa.JSON(), nullable=True),
        sa.Column("last_action_metadata", sa.JSON(), nullable=True),
        sa.Column("last_updated", sa.DateTime(), nullable=False),
    )

    # Copy data by joining with users_new
    op.execute("""
        INSERT INTO conversation_states_new (user_id, state, draft_data, last_action_metadata, last_updated)
        SELECT u.id, cs.state, cs.draft_data, cs.last_action_metadata, cs.last_updated
        FROM conversation_states cs
        JOIN users_new u ON cs.phone_number = u.phone_number
    """)

    # 3. Update messages table
    op.add_column("messages", sa.Column("user_id", sa.Integer(), nullable=True))

    # Link messages to user_id
    op.execute("""
        UPDATE messages
        SET user_id = (SELECT u.id FROM users_new u WHERE u.phone_number = messages.from_number)
        WHERE role = 'user'
    """)
    op.execute("""
        UPDATE messages
        SET user_id = (SELECT u.id FROM users_new u WHERE u.phone_number = messages.to_number)
        WHERE role = 'assistant'
    """)

    # 4. Swap tables
    op.drop_table("conversation_states")
    op.rename_table("conversation_states_new", "conversation_states")
    op.drop_table("users")
    op.rename_table("users_new", "users")

    op.create_index(op.f("ix_messages_user_id"), "messages", ["user_id"], unique=False)


def downgrade() -> None:
    # 1. Add phone_number back to conversation_states
    op.add_column(
        "conversation_states", sa.Column("phone_number", sa.String(), nullable=True)
    )
    op.execute("""
        UPDATE conversation_states
        SET phone_number = (SELECT u.phone_number FROM users u WHERE u.id = conversation_states.user_id)
    """)

    # 2. Create old users table
    op.create_table(
        "users_old",
        sa.Column("phone_number", sa.String(), primary_key=True),
        sa.Column(
            "business_id", sa.Integer(), sa.ForeignKey("businesses.id"), nullable=False
        ),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("preferences", sa.JSON(), nullable=False),
        sa.Column("timezone", sa.String(), nullable=False),
    )

    op.execute("""
        INSERT INTO users_old (phone_number, business_id, role, created_at, preferences, timezone)
        SELECT phone_number, business_id, role, created_at, preferences, timezone FROM users
        WHERE phone_number IS NOT NULL
    """)

    # 3. Create old conversation_states
    op.create_table(
        "conversation_states_old",
        sa.Column("phone_number", sa.String(), primary_key=True),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("draft_data", sa.JSON(), nullable=True),
        sa.Column("last_action_metadata", sa.JSON(), nullable=True),
        sa.Column("last_updated", sa.DateTime(), nullable=False),
    )

    op.execute("""
        INSERT INTO conversation_states_old (phone_number, state, draft_data, last_action_metadata, last_updated)
        SELECT phone_number, state, draft_data, last_action_metadata, last_updated
        FROM conversation_states
    """)

    # 4. Finalizing downgrade
    op.drop_index(op.f("ix_messages_user_id"), table_name="messages")
    op.drop_column("messages", "user_id")
    op.drop_table("conversation_states")
    op.rename_table("conversation_states_old", "conversation_states")
    op.drop_table("users")
    op.rename_table("users_old", "users")
