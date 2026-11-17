import uuid
from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional, Tuple
from scipy import optimize
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.investments import Dividend, InvestmentTransaction, Portfolio, PortfolioHolding
from app.models.markets import Instrument, InstrumentPrice
from app.schemas.portfolio import PortfolioPerformanceResponse
from app.services.currency import ExchangeRateUnavailableError, get_exchange_rate


def calculate_xirr(cash_flows: List[Tuple[date, float]]) -> Optional[float]:
    """
    Calculate the annualized Internal Rate of Return (XIRR) from a series of dated cash flows.
    Sign convention: negative for capital inflows (buys), positive for distributions (sells/dividends)
    and terminal portfolio value.
    Same-day cash flows are consolidated before solving.
    """
    if len(cash_flows) < 2:
        return None

    # Consolidate same-day flows to avoid redundant terms and improve numerical stability
    consolidated: Dict[date, float] = defaultdict(float)
    for dt, amt in cash_flows:
        consolidated[dt] += amt

    flows = sorted((dt, amt) for dt, amt in consolidated.items() if abs(amt) > 1e-9)
    if len(flows) < 2:
        return None

    # Check for sign change
    amounts = [cf[1] for cf in flows]
    if all(a >= 0 for a in amounts) or all(a <= 0 for a in amounts):
        return None

    start_date = flows[0][0]

    def xnpv(rate: float) -> float:
        if rate <= -0.9999:
            return float("inf")
        val = 0.0
        for dt, amt in flows:
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


def calculate_twr_from_subperiods(
    events: List[Tuple[date, float, float]],
    terminal_value: float,
) -> Optional[float]:
    """
    Calculate cumulative Time-Weighted Return (TWR %) by geometrically linking sub-period
    returns around external cash flows.

    Args:
        events: Chronologically ordered list of (event_date, pre_flow_market_value, net_external_flow).
                External inflows (e.g., BUY) are positive; outflows/cash dividends are negative.
        terminal_value: Ending portfolio market value at valuation date.

    Returns:
        Cumulative TWR percentage rounded to 2 decimal places, or None if no valid invested periods exist.
    """
    if not events:
        return None

    sorted_events = sorted(events, key=lambda e: e[0])
    growth_factor = 1.0
    prev_post_value: Optional[float] = None

    for _, pre_val, ext_flow in sorted_events:
        if prev_post_value is not None and prev_post_value > 0:
            sub_return = (pre_val / prev_post_value) - 1.0
            growth_factor *= (1.0 + sub_return)

        post_val = pre_val + ext_flow
        prev_post_value = post_val if post_val > 0 else None

    if prev_post_value is not None and prev_post_value > 0:
        final_sub_return = (terminal_value / prev_post_value) - 1.0
        growth_factor *= (1.0 + final_sub_return)

    return round((growth_factor - 1.0) * 100.0, 2)


def _lookup_price_on_or_before(
    price_series: List[Tuple[date, float]],
    target_date: date,
) -> Optional[float]:
    """Return the latest close price on or before target_date from a date-sorted series."""
    latest: Optional[float] = None
    for p_date, close in price_series:
        if p_date <= target_date:
            latest = close
        else:
            break
    return latest


async def _compute_portfolio_twr(
    db: AsyncSession,
    portfolio: Portfolio,
    total_market_val: float,
) -> Tuple[Optional[float], str]:
    """
    Reconstruct pre-flow valuations on each external cash-flow date using historical EOD prices
    and compute genuine sub-period TWR. Returns (twr_pct, status_note).
    """
    if not portfolio.transactions:
        return None, "TWR unavailable: no investment transactions recorded."

    # Group transactions and non-reinvested dividends by date
    tx_by_date: Dict[date, List[InvestmentTransaction]] = defaultdict(list)
    inst_ids = set()
    for tx in portfolio.transactions:
        tx_by_date[tx.trade_date].append(tx)
        inst_ids.add(tx.instrument_id)

    div_by_date: Dict[date, float] = defaultdict(float)
    for div in portfolio.dividends:
        if not div.is_reinvested:
            div_by_date[div.payable_date] += float(div.net_amount_reporting)

    all_dates = sorted(set(tx_by_date.keys()) | set(div_by_date.keys()))
    if not all_dates:
        return None, "TWR unavailable: no external cash flows."

    # Load historical prices for all traded instruments
    price_stmt = (
        select(InstrumentPrice)
        .where(InstrumentPrice.instrument_id.in_(list(inst_ids)))
        .order_by(InstrumentPrice.price_date)
    )
    price_rows = (await db.execute(price_stmt)).scalars().all()
    prices_by_inst: Dict[uuid.UUID, List[Tuple[date, float]]] = defaultdict(list)
    for pr in price_rows:
        prices_by_inst[pr.instrument_id].append((pr.price_date, float(pr.close)))

    # Map instrument currency
    inst_currency: Dict[uuid.UUID, str] = {}
    for h in portfolio.holdings:
        if h.instrument:
            inst_currency[h.instrument_id] = h.instrument.currency_code
    for tx in portfolio.transactions:
        if tx.instrument_id not in inst_currency:
            inst_currency[tx.instrument_id] = tx.currency

    holdings_qty: Dict[uuid.UUID, float] = defaultdict(float)
    events: List[Tuple[date, float, float]] = []

    for d in all_dates:
        # 1. Value portfolio immediately BEFORE date d's external cash flows
        pre_val = 0.0
        for iid, qty in holdings_qty.items():
            if qty <= 1e-9:
                continue
            price = _lookup_price_on_or_before(prices_by_inst.get(iid, []), d)
            if price is None:
                return None, f"TWR unavailable: missing EOD price history on {d.isoformat()}."
            curr = inst_currency.get(iid, portfolio.reporting_currency)
            try:
                fx_rate = await get_exchange_rate(db, curr, portfolio.reporting_currency, d)
            except ExchangeRateUnavailableError:
                return None, f"TWR unavailable: missing FX rate {curr}/{portfolio.reporting_currency} on {d.isoformat()}."
            pre_val += qty * price * fx_rate

        # 2. Apply date d's transactions and cash dividends to holdings and net external flow
        ext_flow = 0.0
        for tx in tx_by_date.get(d, []):
            ttype = tx.transaction_type.upper()
            qty = float(tx.quantity)
            amt_rep = float(tx.net_amount_reporting)
            if ttype in {"BUY", "TRANSFER_IN"}:
                holdings_qty[tx.instrument_id] += qty
                ext_flow += amt_rep
            elif ttype in {"SELL", "TRANSFER_OUT"}:
                holdings_qty[tx.instrument_id] = max(0.0, holdings_qty[tx.instrument_id] - qty)
                ext_flow -= amt_rep
            elif ttype in {"SPLIT", "BONUS"}:
                holdings_qty[tx.instrument_id] += qty

        if d in div_by_date:
            # Cash dividend distributed out of portfolio
            ext_flow -= div_by_date[d]

        events.append((d, pre_val, ext_flow))

    twr_val = calculate_twr_from_subperiods(events, total_market_val)
    if twr_val is None:
        return None, "TWR unavailable: insufficient sub-period valuation data."
    return twr_val, "TWR computed via geometric sub-period linking around external cash flows."


async def calculate_portfolio_performance(
    db: AsyncSession,
    portfolio_id: uuid.UUID,
    user_id: uuid.UUID,
) -> PortfolioPerformanceResponse:
    """
    Calculate comprehensive institutional portfolio return metrics, including
    XIRR, genuine sub-period TWR, total return, realized gains, and net dividend contributions.
    """
    p_stmt = (
        select(Portfolio)
        .where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
        .options(
            selectinload(Portfolio.holdings).selectinload(PortfolioHolding.instrument),
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

    # FIN-05: Fall back to total historical invested capital if all positions are closed (cost_basis == 0)
    total_invested_capital = sum(
        float(tx.net_amount_reporting)
        for tx in portfolio.transactions
        if tx.transaction_type.upper() in {"BUY", "TRANSFER_IN"}
    )
    return_denom = total_cost_basis if total_cost_basis > 0 else total_invested_capital
    total_return_pct = (total_return_amount / return_denom * 100.0) if return_denom > 0 else 0.0

    # Build cash flows for XIRR
    dated_cash_flows: List[Tuple[date, float]] = []

    for tx in portfolio.transactions:
        ttype = tx.transaction_type.upper()
        # BUY / TRANSFER_IN: Capital outflow from investor's perspective (negative)
        if ttype in {"BUY", "TRANSFER_IN"}:
            dated_cash_flows.append((tx.trade_date, -float(tx.net_amount_reporting)))
        # SELL / TRANSFER_OUT: Capital inflow returned to investor (positive)
        elif ttype in {"SELL", "TRANSFER_OUT"}:
            dated_cash_flows.append((tx.trade_date, float(tx.net_amount_reporting)))

    for div in portfolio.dividends:
        if not div.is_reinvested:
            dated_cash_flows.append((div.payable_date, float(div.net_amount_reporting)))

    # Terminal valuation: Today's current portfolio market value as a positive liquidation inflow
    if total_market_val > 0:
        dated_cash_flows.append((date.today(), total_market_val))

    # Calculate XIRR
    xirr_val = calculate_xirr(dated_cash_flows)

    # FIN-01: Genuine sub-period TWR (returns None if price/FX history is incomplete)
    twr_val, twr_note = await _compute_portfolio_twr(db, portfolio, total_market_val)

    methodology = (
        f"XIRR solved using consolidated dated cash flows and current liquidation value via Scipy BrentQ. "
        f"{twr_note} "
        f"Cost basis includes capitalized buy-side fees and excludes sell fees (Section 16.4)."
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
