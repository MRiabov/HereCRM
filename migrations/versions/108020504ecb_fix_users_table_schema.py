"""fix_users_table_schema

Revision ID: 108020504ecb
Revises: 271d1fde1f13
Create Date: 2026-01-29 12:11:23.981282

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '108020504ecb'
down_revision: Union[str, Sequence[str], None] = '271d1fde1f13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    if 'id' not in columns:
        # 1. Create a temporary table with the correct current schema
        op.create_table('users_fix',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(), nullable=True),
            sa.Column('phone_number', sa.String(), unique=True, nullable=True),
            sa.Column('email', sa.String(), unique=True, nullable=True),
            sa.Column('business_id', sa.Integer(), sa.ForeignKey('businesses.id'), nullable=False),
            sa.Column('role', sa.String(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('preferred_channel', sa.String(), nullable=False, server_default='WHATSAPP'),
            sa.Column('preferences', sa.JSON(), nullable=False),
            sa.Column('timezone', sa.String(), nullable=False, server_default='UTC'),
            sa.Column('default_start_location_lat', sa.Float(), nullable=True),
            sa.Column('default_start_location_lng', sa.Float(), nullable=True),
            sa.Column('google_calendar_credentials', sa.JSON(), nullable=True),
            sa.Column('google_calendar_sync_enabled', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('clerk_id', sa.String(), unique=True, nullable=True),
            sa.Column('current_latitude', sa.Float(), nullable=True),
            sa.Column('current_longitude', sa.Float(), nullable=True),
            sa.Column('location_updated_at', sa.DateTime(), nullable=True),
            sa.Column('current_shift_start', sa.DateTime(), nullable=True),
            sa.Column('geocoding_count', sa.Integer(), nullable=False, server_default='0'),
        )
        
        # 2. Copy data from old users table to users_fix
        # We map columns that we know exist in the old schema
        old_cols = [c for c in columns if c in [
            'name', 'phone_number', 'email', 'business_id', 'role', 'created_at', 
            'preferred_channel', 'preferences', 'timezone', 'default_start_location_lat', 
            'default_start_location_lng', 'google_calendar_credentials', 
            'google_calendar_sync_enabled', 'clerk_id', 'current_latitude', 
            'current_longitude', 'location_updated_at', 'current_shift_start', 'geocoding_count'
        ]]
        col_list = ", ".join(old_cols)
        op.execute(f"INSERT INTO users_fix ({col_list}) SELECT {col_list} FROM users")
        
        # 3. Swap tables
        op.drop_table('users')
        op.rename_table('users_fix', 'users')
        
        # 4. Re-create indexes
        op.create_index(op.f('ix_users_business_id'), 'users', ['business_id'], unique=False)

        # 5. Fix messages table if it has user_id but it's null/incorrect
        msg_cols = [col['name'] for col in inspector.get_columns('messages')]
        if 'user_id' in msg_cols:
            op.execute("""
                UPDATE messages
                SET user_id = (SELECT u.id FROM users u WHERE u.phone_number = messages.from_number)
                WHERE role = 'USER' AND user_id IS NULL
            """)
            op.execute("""
                UPDATE messages
                SET user_id = (SELECT u.id FROM users u WHERE u.phone_number = messages.to_number)
                WHERE role = 'ASSISTANT' AND user_id IS NULL
            """)
        
        # 6. Fix conversation_states table if it uses phone_number instead of user_id
        cs_cols = [col['name'] for col in inspector.get_columns('conversation_states')]
        if 'user_id' not in cs_cols and 'phone_number' in cs_cols:
             op.create_table('cs_fix',
                sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), primary_key=True),
                sa.Column('state', sa.String(), nullable=False),
                sa.Column('draft_data', sa.JSON(), nullable=True),
                sa.Column('last_action_metadata', sa.JSON(), nullable=True),
                sa.Column('last_updated', sa.DateTime(), nullable=False),
                sa.Column('pending_action_timestamp', sa.DateTime(), nullable=True),
                sa.Column('pending_action_payload', sa.JSON(), nullable=True),
                sa.Column('active_channel', sa.String(), nullable=False, server_default='WHATSAPP'),
            )
             op.execute("""
                INSERT INTO cs_fix (user_id, state, draft_data, last_action_metadata, last_updated)
                SELECT u.id, cs.state, cs.draft_data, cs.last_action_metadata, cs.last_updated
                FROM conversation_states cs
                JOIN users u ON cs.phone_number = u.phone_number
            """)
             op.drop_table('conversation_states')
             op.rename_table('cs_fix', 'conversation_states')
    
    # Also check if expenses needs fixing due to previous broken states
    if 'expenses' in inspector.get_table_names():
        pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
