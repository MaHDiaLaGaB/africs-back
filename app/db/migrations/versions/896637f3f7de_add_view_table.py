"""
add view table

Revision ID: 896637f3f7de
Revises: cd2566f417bf
Create Date: 2025-07-05 12:57:55.781842

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "896637f3f7de"
down_revision = "cd2566f417bf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create or replace view; idempotent on definition
    op.execute(
        """
    CREATE OR REPLACE VIEW transaction_reports AS
    SELECT
      t.id                  AS transaction_id,
      t.reference           AS reference,
      t.created_at          AS created_at,
      t.status              AS status,
      t.status_reason       AS status_reason,
      t.amount_foreign      AS amount_foreign,
      t.amount_lyd          AS amount_lyd,
      t.profit              AS profit,

      c.id                  AS customer_id,
      c.name                AS customer_name,
      c.phone               AS customer_phone,
      c.city                AS customer_city,

      u.id                  AS employee_id,
      u.username            AS employee_username,
      u.full_name           AS employee_full_name,

      s.id                  AS service_id,
      s.name                AS service_name,
      s.price               AS service_price,
      s.operation           AS service_operation,

      cur.id                AS currency_id,
      cur.name              AS currency_name,
      cur.symbol            AS currency_symbol

    FROM transactions t
    LEFT JOIN customers c  ON c.id = t.customer_id
    LEFT JOIN users u      ON u.id = t.employee_id
    LEFT JOIN services s   ON s.id = t.service_id
    LEFT JOIN currencies cur ON cur.id = t.currency_id;
    """
    )


def downgrade() -> None:
    # Drop view if exists; safe to run even if missing
    op.execute("DROP VIEW IF EXISTS transaction_reports;")
