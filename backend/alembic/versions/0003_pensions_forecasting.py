"""Add SSNIT benefit estimates and pension forecast assumptions tables.

Revision ID: 0003_pensions_forecasting
Revises: 0002_pensions_foundation
Create Date: 2026-11-17 23:20:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_pensions_forecasting"
down_revision: Union[str, None] = "0002_pensions_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ssnit_benefit_estimates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("estimate_date", sa.Date(), nullable=False),
        sa.Column("target_retirement_age", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("source_type", sa.String(length=40), nullable=False, server_default="STATEMENT_DERIVED"),
        sa.Column("methodology_version", sa.String(length=50), nullable=False, server_default="manual-statement-v1"),
        sa.Column("estimated_monthly_pension", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="GHS"),
        sa.Column("data_completeness_note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["currency"], ["currencies.code"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ssnit_benefit_estimates_user_id", "ssnit_benefit_estimates", ["user_id"])

    op.create_table(
        "pension_forecast_assumptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_age", sa.Integer(), nullable=False),
        sa.Column("retirement_age", sa.Integer(), nullable=False),
        sa.Column("pensionable_salary", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("salary_growth_pct", sa.Numeric(6, 3), nullable=False, server_default="5.0"),
        sa.Column("tier2_rate_pct", sa.Numeric(6, 3), nullable=False, server_default="5.0"),
        sa.Column("tier3_monthly", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("employer_match_pct", sa.Numeric(6, 3), nullable=False, server_default="0"),
        sa.Column("expected_return_pct", sa.Numeric(6, 3), nullable=False, server_default="12.0"),
        sa.Column("inflation_pct", sa.Numeric(6, 3), nullable=False, server_default="8.0"),
        sa.Column("annual_fee_pct", sa.Numeric(6, 3), nullable=False, server_default="1.5"),
        sa.Column("drawdown_years", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("model_version", sa.String(length=50), nullable=False, server_default="gh-pension-proj-v1"),
        sa.Column("projected_funded_nominal", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("projected_funded_real", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pension_forecast_assumptions_user_id", "pension_forecast_assumptions", ["user_id"])


def downgrade() -> None:
    op.drop_table("pension_forecast_assumptions")
    op.drop_table("ssnit_benefit_estimates")
