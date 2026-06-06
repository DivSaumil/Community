"""rename_phone_to_email_and_extend

Revision ID: 0cd1d369dc66
Revises: accf39263f38
Create Date: 2026-06-06 00:09:10.409138

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0cd1d369dc66'
down_revision: Union[str, Sequence[str], None] = 'accf39263f38'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rename column phone to email and alter column type to String(150)
    op.alter_column('users', 'phone', new_column_name='email', type_=sa.String(length=150), existing_type=sa.String(length=20))
    # Update index
    op.drop_index('ix_users_phone', table_name='users')
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Rename column email to phone and alter column type back to String(20)
    op.alter_column('users', 'email', new_column_name='phone', type_=sa.String(length=20), existing_type=sa.String(length=150))
    # Update index
    op.drop_index('ix_users_email', table_name='users')
    op.create_index(op.f('ix_users_phone'), 'users', ['phone'], unique=True)
