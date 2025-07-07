'''
add notes field

Revision ID: 2f1cb861c503
Revises: 896637f3f7de
Create Date: 2025-07-05 18:53:34.529471

'''
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '2f1cb861c503'
down_revision = '896637f3f7de'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    # Add 'notes' column only if the transactions table exists and column is missing
    if inspector.has_table('transactions'):
        existing_cols = {col['name'] for col in inspector.get_columns('transactions')}
        if 'notes' not in existing_cols:
            op.add_column('transactions', sa.Column('notes', sa.String(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    # Drop 'notes' column only if the transactions table exists and column is present
    if inspector.has_table('transactions'):
        existing_cols = {col['name'] for col in inspector.get_columns('transactions')}
        if 'notes' in existing_cols:
            op.drop_column('transactions', 'notes')
