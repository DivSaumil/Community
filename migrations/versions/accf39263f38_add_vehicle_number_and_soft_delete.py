"""add_vehicle_number_and_soft_delete

Revision ID: accf39263f38
Revises: a7cc161cde72
Create Date: 2026-05-20 03:28:55.049525

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'accf39263f38'
down_revision: Union[str, Sequence[str], None] = 'a7cc161cde72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('invoices', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('invoices', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('payments', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('payments', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('vehicle_number', sa.String(length=100), nullable=True))
    
    op.create_check_constraint(
        "check_valid_roles",
        "users",
        "role IN ('admin', 'resident', 'tenant', 'security', 'staff')"
    )

    # Set server defaults for existing tables
    op.alter_column('users', 'created_at', server_default=sa.func.now())
    op.alter_column('users', 'updated_at', server_default=sa.func.now())
    op.alter_column('flats', 'created_at', server_default=sa.func.now())
    op.alter_column('flats', 'updated_at', server_default=sa.func.now())
    op.alter_column('notices', 'created_at', server_default=sa.func.now())
    op.alter_column('notices', 'updated_at', server_default=sa.func.now())
    op.alter_column('complaints', 'created_at', server_default=sa.func.now())
    op.alter_column('complaints', 'updated_at', server_default=sa.func.now())
    op.alter_column('complaint_comments', 'created_at', server_default=sa.func.now())
    op.alter_column('invoices', 'created_at', server_default=sa.func.now())
    op.alter_column('invoices', 'updated_at', server_default=sa.func.now())
    op.alter_column('payments', 'created_at', server_default=sa.func.now())
    op.alter_column('visitor_passes', 'created_at', server_default=sa.func.now())
    op.alter_column('visitor_logs', 'created_at', server_default=sa.func.now())
    op.alter_column('visitor_logs', 'entry_time', server_default=sa.func.now())
    op.alter_column('daily_helps', 'created_at', server_default=sa.func.now())
    op.alter_column('expenses', 'created_at', server_default=sa.func.now())
    op.alter_column('budgets', 'created_at', server_default=sa.func.now())
    op.alter_column('poll_votes', 'created_at', server_default=sa.func.now())


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('poll_votes', 'created_at', server_default=None)
    op.alter_column('budgets', 'created_at', server_default=None)
    op.alter_column('expenses', 'created_at', server_default=None)
    op.alter_column('daily_helps', 'created_at', server_default=None)
    op.alter_column('visitor_logs', 'entry_time', server_default=None)
    op.alter_column('visitor_logs', 'created_at', server_default=None)
    op.alter_column('visitor_passes', 'created_at', server_default=None)
    op.alter_column('payments', 'created_at', server_default=None)
    op.alter_column('invoices', 'updated_at', server_default=None)
    op.alter_column('invoices', 'created_at', server_default=None)
    op.alter_column('complaint_comments', 'created_at', server_default=None)
    op.alter_column('complaints', 'updated_at', server_default=None)
    op.alter_column('complaints', 'created_at', server_default=None)
    op.alter_column('notices', 'updated_at', server_default=None)
    op.alter_column('notices', 'created_at', server_default=None)
    op.alter_column('flats', 'updated_at', server_default=None)
    op.alter_column('flats', 'created_at', server_default=None)
    op.alter_column('users', 'updated_at', server_default=None)
    op.alter_column('users', 'created_at', server_default=None)

    op.drop_constraint('check_valid_roles', 'users')
    op.drop_column('users', 'vehicle_number')
    op.drop_column('payments', 'deleted_at')
    op.drop_column('payments', 'is_deleted')
    op.drop_column('invoices', 'deleted_at')
    op.drop_column('invoices', 'is_deleted')
