from datetime import date
from typing import Optional, Tuple
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.markets import ExchangeRate


async def get_exchange_rate(
    db: AsyncSession,
    from_currency: str,
    to_currency: str,
    rate_date: Optional[date] = None,
) -> float:
    """
    Retrieve the exchange rate from `from_currency` to `to_currency` on or immediately preceding `rate_date`.
    Returns 1.0 if both currencies are identical.
    """
    from_curr = from_currency.upper().strip()
    to_curr = to_currency.upper().strip()

    if from_curr == to_curr:
        return 1.0

    target_date = rate_date or date.today()

    # 1. Direct query: from_curr -> to_curr
    stmt = (
        select(ExchangeRate.rate)
        .where(
            ExchangeRate.from_currency == from_curr,
            ExchangeRate.to_currency == to_curr,
            ExchangeRate.rate_date <= target_date,
        )
        .order_by(desc(ExchangeRate.rate_date))
        .limit(1)
    )
    result = await db.execute(stmt)
    rate = result.scalar_one_or_none()
    if rate is not None:
        return float(rate)

    # 2. Inverse query: to_curr -> from_curr
    inv_stmt = (
        select(ExchangeRate.rate)
        .where(
            ExchangeRate.from_currency == to_curr,
            ExchangeRate.to_currency == from_curr,
            ExchangeRate.rate_date <= target_date,
        )
        .order_by(desc(ExchangeRate.rate_date))
        .limit(1)
    )
    inv_result = await db.execute(inv_stmt)
    inv_rate = inv_result.scalar_one_or_none()
    if inv_rate is not None and float(inv_rate) > 0:
        return float(1.0 / float(inv_rate))

    # 3. Known baseline default fallbacks if no rate has been ingested yet (to ensure non-blocking UX)
    fallback_rates = {
        ("USD", "GHS"): 15.50,
        ("GHS", "USD"): 1.0 / 15.50,
        ("EUR", "GHS"): 16.80,
        ("GHS", "EUR"): 1.0 / 16.80,
        ("GBP", "GHS"): 19.80,
        ("GHS", "GBP"): 1.0 / 19.80,
    }

    return fallback_rates.get((from_curr, to_curr), 1.0)


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
    """
    rate = await get_exchange_rate(db, from_currency, to_currency, rate_date)
    converted = round(amount * rate, 4)
    return converted, rate
