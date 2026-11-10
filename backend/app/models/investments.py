import uuid
from datetime import date, datetime, timezone
from typing import Optional
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Portfolio(Base):
    __tablename__ = "portfolios"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g. "GSE Dividend Portfolio", "US Tech Growth"
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reporting_currency: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), default="GHS", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="portfolios")
    holdings: Mapped[list["PortfolioHolding"]] = relationship("PortfolioHolding", back_populates="portfolio", cascade="all, delete-orphan")
    transactions: Mapped[list["InvestmentTransaction"]] = relationship("InvestmentTransaction", back_populates="portfolio", cascade="all, delete-orphan")
    dividends: Mapped[list["Dividend"]] = relationship("Dividend", back_populates="portfolio", cascade="all, delete-orphan")


class PortfolioHolding(Base):
    __tablename__ = "portfolio_holdings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("instruments.id"),
        index=True,
        nullable=False,
    )
    quantity: Mapped[float] = mapped_column(Numeric(18, 6), default=0.0, nullable=False)
    average_cost_per_share: Mapped[float] = mapped_column(Numeric(18, 4), default=0.0, nullable=False)
    total_cost_basis: Mapped[float] = mapped_column(Numeric(18, 4), default=0.0, nullable=False)
    current_price: Mapped[float] = mapped_column(Numeric(18, 4), default=0.0, nullable=False)
    current_market_value: Mapped[float] = mapped_column(Numeric(18, 4), default=0.0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    unrealized_pnl: Mapped[float] = mapped_column(Numeric(18, 4), default=0.0, nullable=False)
    realized_pnl: Mapped[float] = mapped_column(Numeric(18, 4), default=0.0, nullable=False)

    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="holdings")
    instrument: Mapped["Instrument"] = relationship("Instrument")

    __table_args__ = (
        UniqueConstraint("portfolio_id", "instrument_id", name="uq_portfolio_instrument"),
    )


class InvestmentTransaction(Base):
    __tablename__ = "investment_transactions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("instruments.id"),
        index=True,
        nullable=False,
    )
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)  # BUY, SELL, SPLIT, BONUS, TRANSFER_IN, TRANSFER_OUT
    trade_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    settlement_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    quantity: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    price_per_share: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    gross_amount: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    fees: Mapped[float] = mapped_column(Numeric(18, 4), default=0.0, nullable=False)
    taxes: Mapped[float] = mapped_column(Numeric(18, 4), default=0.0, nullable=False)
    net_amount: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)  # BUY: gross + fees + taxes; SELL: gross - fees - taxes
    currency: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    exchange_rate_to_reporting: Mapped[float] = mapped_column(Numeric(18, 6), default=1.0, nullable=False)
    net_amount_reporting: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    cost_basis_allocated: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)  # For SELL transactions (FIFO allocation)
    realized_gain_loss: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)  # For SELL transactions
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="transactions")
    instrument: Mapped["Instrument"] = relationship("Instrument")


class Dividend(Base):
    __tablename__ = "dividends"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("instruments.id"),
        index=True,
        nullable=False,
    )
    ex_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    record_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    payable_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    gross_amount: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    withholding_tax: Mapped[float] = mapped_column(Numeric(18, 4), default=0.0, nullable=False)
    net_amount: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    exchange_rate_to_reporting: Mapped[float] = mapped_column(Numeric(18, 6), default=1.0, nullable=False)
    net_amount_reporting: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    is_reinvested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="dividends")
    instrument: Mapped["Instrument"] = relationship("Instrument")
