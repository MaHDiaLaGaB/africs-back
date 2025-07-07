'''
init migrations

Revision ID: 86c40ade1616
Revises: 
Create Date: 2025-06-01 00:41:13.738316

'''
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '86c40ade1616'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    meta = sa.MetaData()

    # countries table
    countries = sa.Table(
        'countries', meta,
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('code', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )
    countries.create(bind, checkfirst=True)
    sa.Index(op.f('ix_countries_id'), countries.c.id).create(bind, checkfirst=True)

    # country_balances table
    country_balances = sa.Table(
        'country_balances', meta,
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('country', sa.String(), nullable=True),
        sa.Column('balance', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('country'),
    )
    country_balances.create(bind, checkfirst=True)

    # currencies table
    currencies = sa.Table(
        'currencies', meta,
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('exchange_rate', sa.Float(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('cost_per_unit', sa.Float(), nullable=False),
        sa.Column('stock', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    currencies.create(bind, checkfirst=True)

    # customers table
    customers = sa.Table(
        'customers', meta,
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('phone', sa.String(), nullable=False),
        sa.Column('city', sa.String(), nullable=True),
        sa.Column('balance_due', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    customers.create(bind, checkfirst=True)
    sa.Index(op.f('ix_customers_id'), customers.c.id).create(bind, checkfirst=True)

    # users table
    users = sa.Table(
        'users', meta,
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=True),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('hashed_password', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_admin', sa.Boolean(), nullable=True),
        sa.Column('role', sa.Enum('admin', 'employee', name='role'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    users.create(bind, checkfirst=True)
    sa.Index(op.f('ix_users_id'), users.c.id).create(bind, checkfirst=True)
    sa.Index(op.f('ix_users_username'), users.c.username, unique=True).create(bind, checkfirst=True)

    # receipt_orders table
    receipt_orders = sa.Table(
        'receipt_orders', meta,
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('customer_id', sa.Integer(), nullable=True),
        sa.Column('employee_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id']),
        sa.ForeignKeyConstraint(['employee_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    receipt_orders.create(bind, checkfirst=True)
    sa.Index(op.f('ix_receipt_orders_id'), receipt_orders.c.id).create(bind, checkfirst=True)

    # services table
    services = sa.Table(
        'services', meta,
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('image_url', sa.String(), nullable=True),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('operation', sa.Enum('multiply', 'divide', 'pluse', name='operationtype'), nullable=False),
        sa.Column('currency_id', sa.Integer(), nullable=True),
        sa.Column('country_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['country_id'], ['countries.id']),
        sa.ForeignKeyConstraint(['currency_id'], ['currencies.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    services.create(bind, checkfirst=True)

    # treasuries table
    treasuries = sa.Table(
        'treasuries', meta,
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('balance', sa.Float(), nullable=True),
        sa.Column('employee_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['employee_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_id'),
    )
    treasuries.create(bind, checkfirst=True)
    sa.Index(op.f('ix_treasuries_id'), treasuries.c.id).create(bind, checkfirst=True)

    # treasury_transfers table
    treasury_transfers = sa.Table(
        'treasury_transfers', meta,
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('from_employee_id', sa.Integer(), nullable=True),
        sa.Column('to_employee_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['from_employee_id'], ['users.id']),
        sa.ForeignKeyConstraint(['to_employee_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    treasury_transfers.create(bind, checkfirst=True)
    sa.Index(op.f('ix_treasury_transfers_id'), treasury_transfers.c.id).create(bind, checkfirst=True)

    # transactions table
    transactions = sa.Table(
        'transactions', meta,
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('reference', sa.String(), nullable=True),
        sa.Column('customer_name', sa.String(), nullable=True),
        sa.Column('to', sa.String(), nullable=True),
        sa.Column('number', sa.String(), nullable=True),
        sa.Column('amount_foreign', sa.Float(), nullable=False),
        sa.Column('amount_lyd', sa.Float(), nullable=False),
        sa.Column('payment_type', sa.Enum('cash', 'credit', name='paymenttype'), nullable=True),
        sa.Column('status', sa.Enum('pending', 'completed', 'cancelled', name='transactionstatus'), nullable=True),
        sa.Column('status_reason', sa.String(), nullable=True),
        sa.Column('profit', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=True),
        sa.Column('service_id', sa.Integer(), nullable=True),
        sa.Column('currency_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['currency_id'], ['currencies.id']),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id']),
        sa.ForeignKeyConstraint(['employee_id'], ['users.id']),
        sa.ForeignKeyConstraint(['service_id'], ['services.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    transactions.create(bind, checkfirst=True)
    sa.Index(op.f('ix_transactions_id'), transactions.c.id).create(bind, checkfirst=True)
    sa.Index(op.f('ix_transactions_reference'), transactions.c.reference, unique=True).create(bind, checkfirst=True)

    # transaction_audits table
    transaction_audits = sa.Table(
        'transaction_audits', meta,
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.Integer(), nullable=True),
        sa.Column('old_status', sa.String(), nullable=True),
        sa.Column('new_status', sa.String(), nullable=True),
        sa.Column('reason', sa.String(), nullable=True),
        sa.Column('modified_by', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('changes', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['modified_by'], ['users.id']),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    transaction_audits.create(bind, checkfirst=True)

    # transaction_status_logs table
    transaction_status_logs = sa.Table(
        'transaction_status_logs', meta,
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.Integer(), nullable=False),
        sa.Column('previous_status', sa.Enum('pending', 'completed', 'cancelled', name='transactionstatus'), nullable=False),
        sa.Column('new_status', sa.Enum('pending', 'completed', 'cancelled', name='transactionstatus'), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('changed_by', sa.Integer(), nullable=False),
        sa.Column('changed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id']),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    transaction_status_logs.create(bind, checkfirst=True)


def downgrade() -> None:
    # standard drop order
    op.drop_table('transaction_status_logs')
    op.drop_table('transaction_audits')
    op.drop_index(op.f('ix_transactions_reference'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_id'), table_name='transactions')
    op.drop_table('transactions')
    op.drop_index(op.f('ix_treasury_transfers_id'), table_name='treasury_transfers')
    op.drop_table('treasury_transfers')
    op.drop_index(op.f('ix_treasuries_id'), table_name='treasuries')
    op.drop_table('treasuries')
    op.drop_table('services')
    op.drop_index(op.f('ix_receipt_orders_id'), table_name='receipt_orders')
    op.drop_table('receipt_orders')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_customers_id'), table_name='customers')
    op.drop_table('customers')
    op.drop_table('currencies')
    op.drop_table('country_balances')
    op.drop_index(op.f('ix_countries_id'), table_name='countries')
    op.drop_table('countries')
