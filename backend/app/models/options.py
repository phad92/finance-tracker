import uuid
from datetime import date, datetime
from typing import Optional
from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OptionPosition(Base):
    __tablename__ = "option_positions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    portfolio_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    underlying_instrument_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("instruments.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    underlying_symbol: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    option_symbol: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # e.g. AAPL261218C00220000
    option_type: Mapped[str] = mapped_column(String(10), nullable=False)  # CALL, PUT
    side: Mapped[str] = mapped_column(String(10), nullable=False)  # LONG, SHORT
    strategy_tag: Mapped[str] = mapped_column(String(40), default="SINGLE_LEG", nullable=False)  # COVERED_CALL, CASH_SECURED_PUT, etc.
    exercise_style: Mapped[str] = mapped_column(String(15), default="AMERICAN", nullable=False)  # AMERICAN, EUROPEAN
    strike_price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    expiration_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    contract_multiplier: Mapped[int] = mapped_column(Integer, default=100, nullable=False)  # Never hardcode 100 in calculations
    contracts: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_premium: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)  # Per-share premium
    fees: Mapped[float] = mapped_column(Numeric(18, 4), default=0.0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), default="USD", nullable=False)
    assumed_volatility: Mapped[float] = mapped_column(Numeric(6, 4), default=0.30, nullable=False)  # User/model IV input
    status: Mapped[str] = mapped_column(String(20), default="OPEN", nullable=False)  # OPEN, CLOSED, EXPIRED, EXERCISED, ASSIGNED
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    transactions: Mapped[list["OptionTransaction"]] = relationship(
        "OptionTransaction", back_populates="position", cascade="all, delete-orphan"
    )


class OptionTransaction(Base):
    __tablename__ = "option_transactions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    position_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("option_positions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # OPEN, CLOSE, EXPIRE, EXERCISE, ASSIGN
    trade_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    contracts: Mapped[int] = mapped_column(Integer, nullable=False)
    premium_per_share: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    fees: Mapped[float] = mapped_column(Numeric(18, 4), default=0.0, nullable=False)
    net_cash_flow: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), default="USD", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    position: Mapped["OptionPosition"] = relationship("OptionPosition", back_populates="transactions")

