"""add_quickbooks_fields

Revision ID: a456cecc438a
Revises: dc7ba8e18357
Create Date: 2026-01-22 07:55:21.756338

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a456cecc438a'
down_revision: Union[str, Sequence[str], None] = '73bf25c2bf72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add fields to Business
    op.add_column('businesses', sa.Column('quickbooks_connected', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('businesses', sa.Column('quickbooks_last_sync', sa.DateTime(), nullable=True))
    
    # Create sync status enum
    sync_status_enum = sa.Enum('pending', 'synced', 'failed', name='qb_sync_status')
    sync_status_enum.create(op.get_bind())
    
    # Add fields to Customer
    op.add_column('customers', sa.Column('quickbooks_id', sa.String(50), nullable=True))
    op.add_column('customers', sa.Column('quickbooks_synced_at', sa.DateTime(), nullable=True))
    op.add_column('customers', sa.Column('quickbooks_sync_status', sync_status_enum, nullable=True))
    op.add_column('customers', sa.Column('quickbooks_sync_error', sa.Text(), nullable=True))
    op.create_index('ix_customers_quickbooks_id', 'customers', ['quickbooks_id'])
    
    # Add fields to Service
    op.add_column('services', sa.Column('quickbooks_id', sa.String(50), nullable=True))
    op.add_column('services', sa.Column('quickbooks_synced_at', sa.DateTime(), nullable=True))
    op.add_column('services', sa.Column('quickbooks_sync_status', sync_status_enum, nullable=True))
    op.add_column('services', sa.Column('quickbooks_sync_error', sa.Text(), nullable=True))
    op.create_index('ix_services_quickbooks_id', 'services', ['quickbooks_id'])
    
    # Add fields to Invoice
    op.add_column('invoices', sa.Column('quickbooks_id', sa.String(50), nullable=True))
    op.add_column('invoices', sa.Column('quickbooks_synced_at', sa.DateTime(), nullable=True))
    op.add_column('invoices', sa.Column('quickbooks_sync_status', sync_status_enum, nullable=True))
    op.add_column('invoices', sa.Column('quickbooks_sync_error', sa.Text(), nullable=True))
    op.create_index('ix_invoices_quickbooks_id', 'invoices', ['quickbooks_id'])
    
    # Add fields to Payment
    op.add_column('payments', sa.Column('quickbooks_id', sa.String(50), nullable=True))
    op.add_column('payments', sa.Column('quickbooks_synced_at', sa.DateTime(), nullable=True))
    op.add_column('payments', sa.Column('quickbooks_sync_status', sync_status_enum, nullable=True))
    op.add_column('payments', sa.Column('quickbooks_sync_error', sa.Text(), nullable=True))
    op.create_index('ix_payments_quickbooks_id', 'payments', ['quickbooks_id'])
    
    # Add fields to Quote
    op.add_column('quotes', sa.Column('quickbooks_id', sa.String(50), nullable=True))
    op.add_column('quotes', sa.Column('quickbooks_synced_at', sa.DateTime(), nullable=True))
    op.add_column('quotes', sa.Column('quickbooks_sync_status', sync_status_enum, nullable=True))
    op.add_column('quotes', sa.Column('quickbooks_sync_error', sa.Text(), nullable=True))
    op.create_index('ix_quotes_quickbooks_id', 'quotes', ['quickbooks_id'])
    
    # Create SyncLog table
    op.create_table(
        'sync_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('business_id', sa.Integer(), nullable=False),
        sa.Column('sync_timestamp', sa.DateTime(), nullable=False),
        sa.Column('sync_type', sa.Enum('scheduled', 'manual', name='sync_type'), nullable=False),
        sa.Column('records_processed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('records_succeeded', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('records_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.Enum('success', 'partial_success', 'failed', name='sync_log_status'), nullable=False),
        sa.Column('error_details', sa.JSON(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sync_logs_business_id', 'sync_logs', ['business_id'])
    op.create_index('ix_sync_logs_business_timestamp', 'sync_logs', ['business_id', 'sync_timestamp'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop SyncLog table
    op.drop_index('ix_sync_logs_business_timestamp', 'sync_logs')
    op.drop_index('ix_sync_logs_business_id', 'sync_logs')
    op.drop_table('sync_logs')
    
    # Remove fields from Quote
    op.drop_index('ix_quotes_quickbooks_id', 'quotes')
    op.drop_column('quotes', 'quickbooks_sync_error')
    op.drop_column('quotes', 'quickbooks_sync_status')
    op.drop_column('quotes', 'quickbooks_synced_at')
    op.drop_column('quotes', 'quickbooks_id')
    
    # Remove fields from Payment
    op.drop_index('ix_payments_quickbooks_id', 'payments')
    op.drop_column('payments', 'quickbooks_sync_error')
    op.drop_column('payments', 'quickbooks_sync_status')
    op.drop_column('payments', 'quickbooks_synced_at')
    op.drop_column('payments', 'quickbooks_id')
    
    # Remove fields from Invoice
    op.drop_index('ix_invoices_quickbooks_id', 'invoices')
    op.drop_column('invoices', 'quickbooks_sync_error')
    op.drop_column('invoices', 'quickbooks_sync_status')
    op.drop_column('invoices', 'quickbooks_synced_at')
    op.drop_column('invoices', 'quickbooks_id')
    
    # Remove fields from Service
    op.drop_index('ix_services_quickbooks_id', 'services')
    op.drop_column('services', 'quickbooks_sync_error')
    op.drop_column('services', 'quickbooks_sync_status')
    op.drop_column('services', 'quickbooks_synced_at')
    op.drop_column('services', 'quickbooks_id')
    
    # Remove fields from Customer
    op.drop_index('ix_customers_quickbooks_id', 'customers')
    op.drop_column('customers', 'quickbooks_sync_error')
    op.drop_column('customers', 'quickbooks_sync_status')
    op.drop_column('customers', 'quickbooks_synced_at')
    op.drop_column('customers', 'quickbooks_id')
    
    # Remove fields from Business
    op.drop_column('businesses', 'quickbooks_last_sync')
    op.drop_column('businesses', 'quickbooks_connected')
    
    # Drop sync status enum
    sa.Enum('pending', 'synced', 'failed', name='qb_sync_status').drop(op.get_bind())
