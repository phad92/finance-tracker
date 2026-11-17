import uuid
from datetime import date, datetime
from typing import Optional
from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PensionScheme(Base):
    __tablename__ = "pension_schemes"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tier: Mapped[str] = mapped_column(String(10), index=True, nullable=False)  # TIER_1, TIER_2, TIER_3
    scheme_type: Mapped[str] = mapped_column(String(50), nullable=False)
    trustee_provider: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    npra_reg_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    effective_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    accounts: Mapped[list["PensionAccount"]] = relationship("PensionAccount", back_populates="scheme")


class PensionAccount(Base):
    __tablename__ = "pension_accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    scheme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pension_schemes.id"),
        index=True,
        nullable=False,
    )
    tier: Mapped[str] = mapped_column(String(10), index=True, nullable=False)  # TIER_1, TIER_2, TIER_3
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    member_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    employer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), default="GHS", nullable=False)
    membership_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)  # ACTIVE, DORMANT, CLOSED
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    scheme: Mapped["PensionScheme"] = relationship("PensionScheme", back_populates="accounts")
    contributions: Mapped[list["PensionContribution"]] = relationship(
        "PensionContribution",
        back_populates="account",
        cascade="all, delete-orphan",
        order_by="desc(PensionContribution.contribution_date)",
    )
    valuations: Mapped[list["PensionValuation"]] = relationship(
        "PensionValuation",
        back_populates="account",
        cascade="all, delete-orphan",
        order_by="desc(PensionValuation.valuation_date)",
    )
    transactions: Mapped[list["PensionTransaction"]] = relationship(
        "PensionTransaction",
        back_populates="account",
        cascade="all, delete-orphan",
        order_by="desc(PensionTransaction.tx_date)",
    )


class PensionContribution(Base):
    __tablename__ = "pension_contributions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pension_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    pay_period: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. 2026-11
    contribution_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    employee_amount: Mapped[float] = mapped_column(Numeric(18, 4), default=0.0, nullable=False)
    employer_amount: Mapped[float] = mapped_column(Numeric(18, 4), default=0.0, nullable=False)
    voluntary_amount: Mapped[float] = mapped_column(Numeric(18, 4), default=0.0, nullable=False)
    expected_amount: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    actual_credited_amount: Mapped[float] = mapped_column(Numeric(18, 4), default=0.0, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="MANUAL", nullable=False)  # PAYSLIP, TRUSTEE_STATEMENT, MANUAL
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    account: Mapped["PensionAccount"] = relationship("PensionAccount", back_populates="contributions")


class PensionValuation(Base):
    __tablename__ = "pension_valuations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pension_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    valuation_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    statement_balance: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    units: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    unit_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    source_document_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    account: Mapped["PensionAccount"] = relationship("PensionAccount", back_populates="valuations")


class PensionTransaction(Base):
    __tablename__ = "pension_transactions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pension_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    tx_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    tx_type: Mapped[str] = mapped_column(String(30), nullable=False)  # CONTRIBUTION, FEE, RETURN, WITHDRAWAL, TRANSFER, CORRECTION
    amount: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    account: Mapped["PensionAccount"] = relationship("PensionAccount", back_populates="transactions")


class PensionEmploymentPeriod(Base):
    __tablename__ = "pension_employment_periods"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    employer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    pensionable_salary: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), default="GHS", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class SSNITMembership(Base):
    __tablename__ = "ssnit_membership"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    ssnit_number_masked: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    membership_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    total_contribution_months: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_statement_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class SSNITBenefitEstimate(Base):
    __tablename__ = "ssnit_benefit_estimates"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    estimate_date: Mapped[date] = mapped_column(Date, nullable=False)
    target_retirement_age: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), default="STATEMENT_DERIVED", nullable=False)
    methodology_version: Mapped[str] = mapped_column(String(50), default="manual-statement-v1", nullable=False)
    estimated_monthly_pension: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), default="GHS", nullable=False)
    data_completeness_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class PensionForecastAssumptions(Base):
    __tablename__ = "pension_forecast_assumptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    current_age: Mapped[int] = mapped_column(Integer, nullable=False)
    retirement_age: Mapped[int] = mapped_column(Integer, nullable=False)
    pensionable_salary: Mapped[float] = mapped_column(Numeric(18, 4), default=0.0, nullable=False)
    salary_growth_pct: Mapped[float] = mapped_column(Numeric(6, 3), default=5.0, nullable=False)
    tier2_rate_pct: Mapped[float] = mapped_column(Numeric(6, 3), default=5.0, nullable=False)
    tier3_monthly: Mapped[float] = mapped_column(Numeric(18, 4), default=0.0, nullable=False)
    employer_match_pct: Mapped[float] = mapped_column(Numeric(6, 3), default=0.0, nullable=False)
    expected_return_pct: Mapped[float] = mapped_column(Numeric(6, 3), default=12.0, nullable=False)
    inflation_pct: Mapped[float] = mapped_column(Numeric(6, 3), default=8.0, nullable=False)
    annual_fee_pct: Mapped[float] = mapped_column(Numeric(6, 3), default=1.5, nullable=False)
    drawdown_years: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), default="gh-pension-proj-v1", nullable=False)
    projected_funded_nominal: Mapped[float] = mapped_column(Numeric(18, 4), default=0.0, nullable=False)
    projected_funded_real: Mapped[float] = mapped_column(Numeric(18, 4), default=0.0, nullable=False)
