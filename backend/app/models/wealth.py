import uuid
from datetime import date, datetime, timezone
from typing import Optional
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AssetCategory(Base):
    __tablename__ = "asset_categories"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_liquid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    assets: Mapped[list["Asset"]] = relationship("Asset", back_populates="category")


class Asset(Base):
    __tablename__ = "assets"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asset_categories.id"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    institution: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # e.g. Stanbic, MTN MoMo, Land Registry
    currency: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), default="GHS", nullable=False)
    ownership_percentage: Mapped[float] = mapped_column(Numeric(5, 2), default=100.00, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="assets")
    category: Mapped["AssetCategory"] = relationship("AssetCategory", back_populates="assets")
    valuations: Mapped[list["AssetValuation"]] = relationship("AssetValuation", back_populates="asset", cascade="all, delete-orphan", order_by="desc(AssetValuation.valuation_date)")


class AssetValuation(Base):
    __tablename__ = "asset_valuations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    valuation_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    value_original_currency: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    exchange_rate_to_reporting: Mapped[float] = mapped_column(Numeric(18, 6), default=1.0, nullable=False)
    value_reporting_currency: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    valuation_method: Mapped[str] = mapped_column(String(50), default="MANUAL", nullable=False)  # MANUAL, APPRAISAL, MARKET, COST
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    asset: Mapped["Asset"] = relationship("Asset", back_populates="valuations")


class Liability(Base):
    __tablename__ = "liabilities"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g. Home Mortgage, Auto Loan, Credit Card
    institution: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Lender
    category: Mapped[str] = mapped_column(String(50), default="LOAN", nullable=False)  # MORTGAGE, PERSONAL_LOAN, CREDIT_CARD, BUSINESS_LOAN
    currency: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), default="GHS", nullable=False)
    original_balance: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    current_balance: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    interest_rate: Mapped[Optional[float]] = mapped_column(Numeric(6, 4), nullable=True)  # Annual interest rate, e.g. 0.2200 for 22%
    monthly_payment: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    maturity_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="liabilities")


class FinancialAccount(Base):
    __tablename__ = "financial_accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g. Stanbic Checking, MTN Mobile Money
    account_type: Mapped[str] = mapped_column(String(50), default="BANK", nullable=False)  # BANK, MOBILE_MONEY, CASH, BROKERAGE_CASH
    institution: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    account_number_mask: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)  # e.g. ****1234
    currency: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), default="GHS", nullable=False)
    current_balance: Mapped[float] = mapped_column(Numeric(18, 4), default=0.0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    transactions: Mapped[list["FinancialTransaction"]] = relationship("FinancialTransaction", back_populates="account", cascade="all, delete-orphan")


class FinancialTransaction(Base):
    __tablename__ = "financial_transactions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("financial_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    transaction_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)  # positive for deposit/income, negative for expense/withdrawal
    currency: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    exchange_rate_to_reporting: Mapped[float] = mapped_column(Numeric(18, 6), default=1.0, nullable=False)
    amount_reporting_currency: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(50), default="EXPENSE", nullable=False)  # INCOME, EXPENSE, TRANSFER
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # e.g. Salary, Groceries, Utilities, Investment
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_reconciled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    account: Mapped["FinancialAccount"] = relationship("FinancialAccount", back_populates="transactions")
