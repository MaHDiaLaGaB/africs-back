'''
add FIFO

Revision ID: cd2566f417bf
Revises: 86c40ade1616
Create Date: 2025-06-20 22:29:14.404493

'''
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'cd2566f417bf'
down_revision = '86c40ade1616'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    meta = sa.MetaData()
    meta.reflect(bind=bind)

    # currency_lots table
    currency_lots = sa.Table(
        'currency_lots', meta,
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('currency_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('remaining_quantity', sa.Float(), nullable=False),
        sa.Column('cost_per_unit', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['currency_id'], ['currencies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    currency_lots.create(bind, checkfirst=True)

    # transaction_currency_lots table
    transaction_currency_lots = sa.Table(
        'transaction_currency_lots', meta,
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.Integer(), nullable=False),
        sa.Column('lot_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('cost_per_unit', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['lot_id'], ['currency_lots.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    transaction_currency_lots.create(bind, checkfirst=True)

    # drop old columns from currencies if they exist
    if inspector.has_table('currencies'):
        cols = {col['name'] for col in inspector.get_columns('currencies')}
        if 'cost_per_unit' in cols:
            op.drop_column('currencies', 'cost_per_unit')
        if 'exchange_rate' in cols:
            op.drop_column('currencies', 'exchange_rate')
        if 'stock' in cols:
            op.drop_column('currencies', 'stock')


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    # re-add columns to currencies if missing
    if inspector.has_table('currencies'):
        cols = {col['name'] for col in inspector.get_columns('currencies')}
        if 'stock' not in cols:
            op.add_column('currencies', sa.Column('stock', sa.Float(), nullable=True))
        if 'exchange_rate' not in cols:
            op.add_column('currencies', sa.Column('exchange_rate', sa.Float(), nullable=False))
        if 'cost_per_unit' not in cols:
            op.add_column('currencies', sa.Column('cost_per_unit', sa.Float(), nullable=False))

    # drop new tables
    op.drop_table('transaction_currency_lots')
    op.drop_table('currency_lots')
