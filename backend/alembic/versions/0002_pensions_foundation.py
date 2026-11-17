"""Add Ghana 3-tier pension foundation tables.

Revision ID: 0002_pensions_foundation
Revises: 0001_initial_schema
Create Date: 2026-11-17 23:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_pensions_foundation"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pension_schemes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("tier", sa.String(length=10), nullable=False),
        sa.Column("scheme_type", sa.String(length=50), nullable=False),
        sa.Column("trustee_provider", sa.String(length=255), nullable=True),
        sa.Column("npra_reg_ref", sa.String(length=100), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("is_custom", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pension_schemes_tier", "pension_schemes", ["tier"])

    op.create_table(
        "pension_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scheme_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tier", sa.String(length=10), nullable=False),
        sa.Column("account_name", sa.String(length=255), nullable=False),
        sa.Column("member_reference", sa.String(length=100), nullable=True),
        sa.Column("employer_name", sa.String(length=255), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="GHS"),
        sa.Column("membership_start_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scheme_id"], ["pension_schemes.id"]),
        sa.ForeignKeyConstraint(["currency"], ["currencies.code"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pension_accounts_user_id", "pension_accounts", ["user_id"])
    op.create_index("ix_pension_accounts_scheme_id", "pension_accounts", ["scheme_id"])
    op.create_index("ix_pension_accounts_tier", "pension_accounts", ["tier"])

    op.create_table(
        "pension_contributions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pay_period", sa.String(length=20), nullable=False),
        sa.Column("contribution_date", sa.Date(), nullable=False),
        sa.Column("employee_amount", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("employer_amount", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("voluntary_amount", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("expected_amount", sa.Numeric(18, 4), nullable=True),
        sa.Column("actual_credited_amount", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("source", sa.String(length=50), nullable=False, server_default="MANUAL"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["pension_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pension_contributions_user_id", "pension_contributions", ["user_id"])
    op.create_index("ix_pension_contributions_account_id", "pension_contributions", ["account_id"])
    op.create_index("ix_pension_contributions_contribution_date", "pension_contributions", ["contribution_date"])

    op.create_table(
        "pension_valuations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("valuation_date", sa.Date(), nullable=False),
        sa.Column("statement_balance", sa.Numeric(18, 4), nullable=False),
        sa.Column("units", sa.Numeric(18, 6), nullable=True),
        sa.Column("unit_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("source_document_ref", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["pension_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pension_valuations_user_id", "pension_valuations", ["user_id"])
    op.create_index("ix_pension_valuations_account_id", "pension_valuations", ["account_id"])
    op.create_index("ix_pension_valuations_valuation_date", "pension_valuations", ["valuation_date"])

    op.create_table(
        "pension_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tx_date", sa.Date(), nullable=False),
        sa.Column("tx_type", sa.String(length=30), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["pension_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pension_transactions_user_id", "pension_transactions", ["user_id"])
    op.create_index("ix_pension_transactions_account_id", "pension_transactions", ["account_id"])
    op.create_index("ix_pension_transactions_tx_date", "pension_transactions", ["tx_date"])

    op.create_table(
        "pension_employment_periods",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employer_name", sa.String(length=255), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("pensionable_salary", sa.Numeric(18, 4), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="GHS"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["currency"], ["currencies.code"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pension_employment_periods_user_id", "pension_employment_periods", ["user_id"])

    op.create_table(
        "ssnit_membership",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ssnit_number_masked", sa.String(length=50), nullable=True),
        sa.Column("membership_start_date", sa.Date(), nullable=True),
        sa.Column("total_contribution_months", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_statement_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_ssnit_membership_user_id"),
    )
    op.create_index("ix_ssnit_membership_user_id", "ssnit_membership", ["user_id"])


def downgrade() -> None:
    op.drop_table("ssnit_membership")
    op.drop_table("pension_employment_periods")
    op.drop_table("pension_transactions")
    op.drop_table("pension_valuations")
    op.drop_table("pension_contributions")
    op.drop_table("pension_accounts")
    op.drop_table("pension_schemes")
