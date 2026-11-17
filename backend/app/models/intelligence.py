import uuid
from datetime import date, datetime, timezone
from typing import Optional
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EconomicIndicator(Base):
    __tablename__ = "economic_indicators"

    code: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)  # e.g. GHA_POLICY_RATE, GHA_INFLATION, US_CPI
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country_code: Mapped[str] = mapped_column(String(3), index=True, nullable=False)  # GHA, USA, GLO
    category: Mapped[str] = mapped_column(String(60), nullable=False)  # INTEREST_RATE, INFLATION, GDP, FX_RESERVES, YIELD
    unit: Mapped[str] = mapped_column(String(30), default="%", nullable=False)  # %, USD, GHS
    source: Mapped[str] = mapped_column(String(100), nullable=False)  # World Bank, BoG, FRED
    latest_value: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    latest_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    observations: Mapped[list["EconomicObservation"]] = relationship(
        "EconomicObservation", back_populates="indicator", cascade="all, delete-orphan"
    )


class EconomicObservation(Base):
    __tablename__ = "economic_observations"

    indicator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("economic_indicators.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    observation_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    value: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    data_quality: Mapped[str] = mapped_column(String(30), default="VERIFIED", nullable=False)

    indicator: Mapped["EconomicIndicator"] = relationship("EconomicIndicator", back_populates="observations")

    __table_args__ = (
        UniqueConstraint("indicator_id", "observation_date", name="uq_indicator_obs_date"),
    )


class NewsArticle(Base):
    __tablename__ = "news_articles"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), unique=True, nullable=False)
    publisher: Mapped[str] = mapped_column(String(150), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    related_symbols: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Comma-separated tickers e.g. MTNGH,AAPL
    country_code: Mapped[str] = mapped_column(String(3), default="GLO", nullable=False)


class ResearchReport(Base):
    __tablename__ = "research_reports"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("instruments.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    opportunity_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    report_data: Mapped[dict] = mapped_column(JSON, nullable=False)  # 12-section structured JSON report
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    data_quality_summary: Mapped[str] = mapped_column(String(255), default="PROVIDER_SOURCED", nullable=False)


class AIConversation(Base):
    __tablename__ = "ai_conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), default="Financial Intelligence Chat", nullable=False)

    messages: Mapped[list["AIMessage"]] = relationship(
        "AIMessage", back_populates="conversation", cascade="all, delete-orphan", order_by="AIMessage.created_at"
    )


class AIMessage(Base):
    __tablename__ = "ai_messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant, system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tools_invoked: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    conversation: Mapped["AIConversation"] = relationship("AIConversation", back_populates="messages")

