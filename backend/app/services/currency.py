from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional, Tuple
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.markets import ExchangeRate


class ExchangeRateUnavailableError(ValueError):
    """Raised when no valid exchange rate exists for a requested currency pair."""


@dataclass(frozen=True)
class ExchangeRateQuote:
    from_currency: str
    to_currency: str
    rate: Optional[float]
    source: str
    effective_date: date
    retrieved_at: datetime
    quality_status: str  # OFFICIAL, PROVIDER, CALCULATED_CROSS_RATE, MANUAL, STALE, UNAVAILABLE
    is_stale: bool = False


def _classify_source_quality(source: str) -> str:
    src = source.upper().strip()
    if src == "MANUAL":
        return "MANUAL"
    if "CALCULATED" in src or "CROSS" in src:
        return "CALCULATED_CROSS_RATE"
    if "OFFICIAL" in src or src in {"BOG_PUBLISHED", "ECB"}:
        return "OFFICIAL"
    return "PROVIDER"


async def get_exchange_rate_quote(
    db: AsyncSession,
    from_currency: str,
    to_currency: str,
    rate_date: Optional[date] = None,
    max_age_days: int = 7,
) -> ExchangeRateQuote:
    """
    Retrieve an exchange rate quote from `from_currency` to `to_currency` on or immediately
    preceding `rate_date`, including provenance, effective date, and freshness status.
    Never returns silent hardcoded or 1.0 fallback rates for missing pairs.
    """
    from_curr = from_currency.upper().strip()
    to_curr = to_currency.upper().strip()
    target_date = rate_date or date.today()
    now_utc = datetime.now(timezone.utc)

    if from_curr == to_curr:
        return ExchangeRateQuote(
            from_currency=from_curr,
            to_currency=to_curr,
            rate=1.0,
            source="IDENTITY",
            effective_date=target_date,
            retrieved_at=now_utc,
            quality_status="OFFICIAL",
            is_stale=False,
        )

    # 1. Direct query: from_curr -> to_curr
    stmt = (
        select(ExchangeRate)
        .where(
            ExchangeRate.from_currency == from_curr,
            ExchangeRate.to_currency == to_curr,
            ExchangeRate.rate_date <= target_date,
        )
        .order_by(desc(ExchangeRate.rate_date))
        .limit(1)
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is not None and float(row.rate) > 0:
        age_days = (target_date - row.rate_date).days
        is_stale = age_days > max_age_days
        base_quality = _classify_source_quality(row.source)
        quality = "STALE" if (is_stale and base_quality != "MANUAL") else base_quality
        return ExchangeRateQuote(
            from_currency=from_curr,
            to_currency=to_curr,
            rate=float(row.rate),
            source=row.source,
            effective_date=row.rate_date,
            retrieved_at=getattr(row, "updated_at", None) or getattr(row, "created_at", None) or now_utc,
            quality_status=quality,
            is_stale=is_stale,
        )

    # 2. Inverse query: to_curr -> from_curr
    inv_stmt = (
        select(ExchangeRate)
        .where(
            ExchangeRate.from_currency == to_curr,
            ExchangeRate.to_currency == from_curr,
            ExchangeRate.rate_date <= target_date,
        )
        .order_by(desc(ExchangeRate.rate_date))
        .limit(1)
    )
    inv_row = (await db.execute(inv_stmt)).scalar_one_or_none()
    if inv_row is not None and float(inv_row.rate) > 0:
        age_days = (target_date - inv_row.rate_date).days
        is_stale = age_days > max_age_days
        base_quality = _classify_source_quality(inv_row.source)
        quality = "STALE" if (is_stale and base_quality != "MANUAL") else base_quality
        return ExchangeRateQuote(
            from_currency=from_curr,
            to_currency=to_curr,
            rate=1.0 / float(inv_row.rate),
            source=f"INVERSE:{inv_row.source}",
            effective_date=inv_row.rate_date,
            retrieved_at=getattr(inv_row, "updated_at", None) or getattr(inv_row, "created_at", None) or now_utc,
            quality_status=quality,
            is_stale=is_stale,
        )

    # 3. Explicit unavailable result (no silent hardcoded or 1.0 fallback)
    return ExchangeRateQuote(
        from_currency=from_curr,
        to_currency=to_curr,
        rate=None,
        source="NONE",
        effective_date=target_date,
        retrieved_at=now_utc,
        quality_status="UNAVAILABLE",
        is_stale=True,
    )


async def get_exchange_rate(
    db: AsyncSession,
    from_currency: str,
    to_currency: str,
    rate_date: Optional[date] = None,
) -> float:
    """
    Retrieve the exchange rate from `from_currency` to `to_currency` on or immediately preceding `rate_date`.
    Raises ExchangeRateUnavailableError if no valid rate exists.
    """
    quote = await get_exchange_rate_quote(db, from_currency, to_currency, rate_date)
    if quote.rate is None or quote.quality_status == "UNAVAILABLE":
        raise ExchangeRateUnavailableError(
            f"No exchange rate available for {quote.from_currency}/{quote.to_currency} on or before {quote.effective_date}."
        )
    return quote.rate


async def convert_amount(
    db: AsyncSession,
    amount: float,
    from_currency: str,
    to_currency: str,
    rate_date: Optional[date] = None,
) -> Tuple[float, float]:
    """
    Convert an amount from one currency to another.
    Returns a tuple of (converted_amount, applied_exchange_rate).
    Raises ExchangeRateUnavailableError if no valid rate exists.
    """
    rate = await get_exchange_rate(db, from_currency, to_currency, rate_date)
    converted = round(amount * rate, 4)
    return converted, rate
