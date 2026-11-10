import uuid
from datetime import date, datetime, timezone
from typing import Optional
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Currency(Base):
    __tablename__ = "currencies"

    code: Mapped[str] = mapped_column(String(3), unique=True, index=True, nullable=False)  # ISO 4217, e.g. GHS, USD
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)  # e.g. GH₵, $, £
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    from_currency: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), index=True, nullable=False)
    to_currency: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), index=True, nullable=False)
    rate: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    rate_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(100), default="Frankfurter", nullable=False)

    __table_args__ = (
        UniqueConstraint("from_currency", "to_currency", "rate_date", "source", name="uq_fx_rate_date_source"),
    )


class Exchange(Base):
    __tablename__ = "exchanges"

    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)  # e.g. GSE, NYSE, NASDAQ
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), default="GH", nullable=False)  # ISO 3166-1 alpha-2
    currency_code: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)

    instruments: Mapped[list["Instrument"]] = relationship("Instrument", back_populates="exchange")


class Instrument(Base):
    __tablename__ = "instruments"

    symbol: Mapped[str] = mapped_column(String(30), index=True, nullable=False)  # e.g. MTNGH, AAPL, SPY
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    exchange_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exchanges.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    instrument_type: Mapped[str] = mapped_column(String(30), default="EQUITY", nullable=False)  # EQUITY, ETF, BOND, T_BILL
    currency_code: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    isin: Mapped[Optional[str]] = mapped_column(String(12), unique=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    exchange: Mapped["Exchange"] = relationship("Exchange", back_populates="instruments")
    prices: Mapped[list["InstrumentPrice"]] = relationship("InstrumentPrice", back_populates="instrument", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("exchange_id", "symbol", name="uq_exchange_symbol"),
    )


class InstrumentPrice(Base):
    __tablename__ = "instrument_prices"

    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("instruments.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    price_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    open: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    high: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    low: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    close: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    volume: Mapped[Optional[int]] = mapped_column(Numeric(20, 0), nullable=True)
    source: Mapped[str] = mapped_column(String(100), default="MANUAL", nullable=False)
    data_quality: Mapped[str] = mapped_column(String(30), default="VERIFIED", nullable=False)  # VERIFIED, ESTIMATED, MANUAL

    instrument: Mapped["Instrument"] = relationship("Instrument", back_populates="prices")

    __table_args__ = (
        UniqueConstraint("instrument_id", "price_date", "source", name="uq_instrument_price_date_source"),
    )

