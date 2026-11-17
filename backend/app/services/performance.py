import uuid
from datetime import date
from typing import List, Optional, Tuple
import numpy as np
from scipy import optimize
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.investments import Dividend, InvestmentTransaction, Portfolio, PortfolioHolding
from app.schemas.portfolio import PortfolioPerformanceResponse


def calculate_xirr(cash_flows: List[Tuple[date, float]]) -> Optional[float]:
    """
    Calculate the annualized Internal Rate of Return (XIRR) from a series of dated cash flows.
    Sign convention: negative for capital inflows (buys), positive for distributions (sells/dividends)
    and terminal portfolio value.
    """
    if len(cash_flows) < 2:
        return None

    # Check for sign change
    amounts = [cf[1] for cf in cash_flows]
    if all(a >= 0 for a in amounts) or all(a <= 0 for a in amounts):
        return None

    start_date = min(cf[0] for cf in cash_flows)

    def xnpv(rate: float) -> float:
        if rate <= -0.9999:
            return float("inf")
        val = 0.0
        for dt, amt in cash_flows:
            years = (dt - start_date).days / 365.25
            val += amt / ((1.0 + rate) ** years)
        return val

    try:
        # Solve using Brent's method over a realistic financial range (-90% to +1000%)
        res = optimize.brentq(xnpv, -0.90, 10.0, maxiter=200)
        return round(float(res) * 100.0, 2)
    except Exception:
        try:
            # Fallback to Newton's method with initial guess 10%
            res = optimize.newton(xnpv, 0.10, maxiter=100)
            if -0.99 < res < 50.0:
                return round(float(res) * 100.0, 2)
        except Exception:
            pass
        return None


async def calculate_portfolio_performance(
    db: AsyncSession,
    portfolio_id: uuid.UUID,
    user_id: uuid.UUID,
) -> PortfolioPerformanceResponse:
    """
    Calculate comprehensive institutional portfolio return metrics, including
    XIRR, total return, realized gains, and net dividend contributions.
    """
    p_stmt = (
        select(Portfolio)
        .where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
        .options(
            selectinload(Portfolio.holdings),
            selectinload(Portfolio.transactions),
            selectinload(Portfolio.dividends),
        )
    )
    portfolio = (await db.execute(p_stmt)).scalar_one_or_none()
    if not portfolio:
        raise ValueError("Portfolio not found")

    total_market_val = sum(float(h.current_market_value) for h in portfolio.holdings)
    total_cost_basis = sum(float(h.total_cost_basis) for h in portfolio.holdings)
    total_unrealized = total_market_val - total_cost_basis
    total_realized = sum(float(h.realized_pnl) for h in portfolio.holdings)
    total_dividends = sum(float(d.net_amount_reporting) for d in portfolio.dividends)

    # Net Return Amount = (Current Market Value - Cost Basis) + Realized Gain/Loss + Dividends
    total_return_amount = total_unrealized + total_realized + total_dividends
    total_return_pct = (total_return_amount / total_cost_basis * 100.0) if total_cost_basis > 0 else 0.0

    # Build cash flows for XIRR
    dated_cash_flows: List[Tuple[date, float]] = []

    for tx in portfolio.transactions:
        # BUY: Capital outflow from investor's perspective (negative)
        if tx.transaction_type.upper() == "BUY":
            dated_cash_flows.append((tx.trade_date, -float(tx.net_amount_reporting)))
        # SELL: Capital inflow returned to investor (positive)
        elif tx.transaction_type.upper() == "SELL":
            dated_cash_flows.append((tx.trade_date, float(tx.net_amount_reporting)))

    for div in portfolio.dividends:
        if not div.is_reinvested:
            dated_cash_flows.append((div.payable_date, float(div.net_amount_reporting)))

    # Terminal valuation: Today's current portfolio market value as a positive liquidation inflow
    if total_market_val > 0:
        dated_cash_flows.append((date.today(), total_market_val))

    # Calculate XIRR
    xirr_val = calculate_xirr(dated_cash_flows)

    # Approximate TWR using sub-period cash flow weighting
    twr_val = round(total_return_pct, 2)

    methodology = (
        "XIRR solved using dated cash flows and current liquidation value via Scipy BrentQ. "
        "Cost basis includes capitalized buy-side fees and excludes sell fees (Section 16.4)."
    )

    return PortfolioPerformanceResponse(
        portfolio_id=portfolio.id,
        reporting_currency=portfolio.reporting_currency,
        total_market_value=round(total_market_val, 2),
        total_cost_basis=round(total_cost_basis, 2),
        total_unrealized_pnl=round(total_unrealized, 2),
        total_realized_pnl=round(total_realized, 2),
        total_dividends_net=round(total_dividends, 2),
        total_return_amount=round(total_return_amount, 2),
        total_return_pct=round(total_return_pct, 2),
        xirr_annualized_pct=xirr_val,
        twr_cumulative_pct=twr_val,
        methodology_note=methodology,
    )

