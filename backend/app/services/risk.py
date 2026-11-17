import uuid
from collections import defaultdict
from datetime import date
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.investments import Portfolio, PortfolioHolding
from app.models.markets import Instrument
from app.schemas.risk import ConcentrationMetric, PortfolioRiskResponse, StressTestScenario
from app.services.currency import get_exchange_rate_quote


# FIN-07: Versioned parametric risk assumptions by reporting currency
RISK_ASSUMPTIONS_VERSION = "2026.11-v1"
RISK_ASSUMPTIONS_BY_CURRENCY: Dict[str, Dict[str, Any]] = {
    "USD": {
        "version": RISK_ASSUMPTIONS_VERSION,
        "effective_date": "2026-11-01",
        "source": "US Treasury 3M + Historical Equity Benchmark",
        "risk_free_rate": 0.045,
        "assumed_annual_return": 0.14,
        "base_volatility": 0.16,
        "hhi_volatility_slope": 0.12,
        "sortino_multiplier": 1.35,
        "drawdown_multiplier": 1.65,
    },
    "GHS": {
        "version": RISK_ASSUMPTIONS_VERSION,
        "effective_date": "2026-11-01",
        "source": "Bank of Ghana 91D T-Bill Benchmark + GSE Equity Risk Premium",
        "risk_free_rate": 0.18,
        "assumed_annual_return": 0.22,
        "base_volatility": 0.16,
        "hhi_volatility_slope": 0.12,
        "sortino_multiplier": 1.35,
        "drawdown_multiplier": 1.65,
    },
}


def get_risk_assumptions(reporting_currency: str) -> Dict[str, Any]:
    """Return versioned risk assumptions for a reporting currency (defaults to GHS profile)."""
    curr = reporting_currency.upper().strip()
    return dict(RISK_ASSUMPTIONS_BY_CURRENCY.get(curr, RISK_ASSUMPTIONS_BY_CURRENCY["GHS"]))


async def calculate_portfolio_risk(
    db: AsyncSession,
    portfolio_id: uuid.UUID,
    user_id: uuid.UUID,
) -> PortfolioRiskResponse:
    """
    Compute portfolio risk metrics (Volatility, Sharpe, Sortino, Max Drawdown,
    95% VaR, 95% CVaR, Concentration HHI) and run stress test simulations (Module 9).
    Aligns observed price series by actual trading dates, applies FX conversion to reporting
    currency when available, and discloses versioned assumptions.
    """
    stmt = (
        select(Portfolio)
        .where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
        .options(
            selectinload(Portfolio.holdings)
            .selectinload(PortfolioHolding.instrument)
            .selectinload(Instrument.prices)
        )
    )
    portfolio = (await db.execute(stmt)).scalar_one_or_none()
    if not portfolio:
        raise ValueError("Portfolio not found")

    assumptions = get_risk_assumptions(portfolio.reporting_currency)
    holdings = [h for h in portfolio.holdings if float(h.quantity) > 0]
    total_val = sum(float(h.current_market_value) for h in holdings)

    if total_val <= 0 or not holdings:
        return PortfolioRiskResponse(
            portfolio_id=portfolio.id,
            reporting_currency=portfolio.reporting_currency,
            total_market_value=0.0,
            concentration_hhi=0.0,
            sector_exposure=[],
            currency_exposure=[],
            stress_tests=[],
            data_completeness_note="Portfolio currently has no active market value.",
            estimation_status="NO_ACTIVE_POSITIONS",
            methodology_note="No active holdings to evaluate.",
            assumptions_used=assumptions,
        )

    # 1. Sector, Currency, and HHI Concentration
    sector_totals: Dict[str, float] = defaultdict(float)
    currency_totals: Dict[str, float] = defaultdict(float)
    weights = []

    for h in holdings:
        mv = float(h.current_market_value)
        w = mv / total_val
        weights.append(w)
        sector_name = (h.instrument.sector if h.instrument and h.instrument.sector else "General")
        sector_totals[sector_name] += mv
        currency_totals[h.currency] += mv

    hhi = round(sum((w * 100.0) ** 2 for w in weights), 1)

    sector_exposure = [
        ConcentrationMetric(label=k, value=round(v, 2), weight_pct=round(v / total_val * 100.0, 1))
        for k, v in sorted(sector_totals.items(), key=lambda x: x[1], reverse=True)
    ]
    currency_exposure = [
        ConcentrationMetric(label=k, value=round(v, 2), weight_pct=round(v / total_val * 100.0, 1))
        for k, v in sorted(currency_totals.items(), key=lambda x: x[1], reverse=True)
    ]

    # 2. Date-Aligned, FX-Aware Historical Return Series vs Parametric Estimate
    holding_dated_returns: List[Tuple[float, Dict[date, float]]] = []
    missing_history_symbols: List[str] = []
    fx_unadjusted_currencies: List[str] = []

    for h in holdings:
        prices = sorted(h.instrument.prices, key=lambda p: p.price_date) if h.instrument else []
        if len(prices) < 15:
            missing_history_symbols.append(h.instrument.symbol if h.instrument else "UNKNOWN")
            continue

        # Convert closes to reporting currency if FX quote is available
        converted_series: List[Tuple[date, float]] = []
        fx_missing_for_holding = False
        for p in prices:
            close_val = float(p.close)
            if h.currency.upper() != portfolio.reporting_currency.upper():
                try:
                    quote = await get_exchange_rate_quote(
                        db, h.currency, portfolio.reporting_currency, p.price_date
                    )
                    if quote.rate is not None and quote.quality_status != "UNAVAILABLE":
                        close_val *= quote.rate
                    else:
                        fx_missing_for_holding = True
                except Exception:
                    fx_missing_for_holding = True
            converted_series.append((p.price_date, close_val))

        if fx_missing_for_holding and h.currency not in fx_unadjusted_currencies:
            fx_unadjusted_currencies.append(h.currency)

        ret_map: Dict[date, float] = {}
        for idx in range(1, len(converted_series)):
            prev_close = converted_series[idx - 1][1]
            curr_date, curr_close = converted_series[idx]
            if prev_close > 0:
                ret_map[curr_date] = (curr_close - prev_close) / prev_close

        holding_dated_returns.append((float(h.current_market_value) / total_val, ret_map))

    # Find common trading dates across all holdings
    common_dates: List[date] = []
    if len(holding_dated_returns) == len(holdings) and len(holding_dated_returns) > 0:
        date_sets = [set(rmap.keys()) for _, rmap in holding_dated_returns]
        common_dates = sorted(set.intersection(*date_sets))

    rf = float(assumptions["risk_free_rate"])

    if len(holding_dated_returns) == len(holdings) and len(common_dates) >= 14:
        port_daily_rets = np.array(
            [sum(w * rmap[d] for w, rmap in holding_dated_returns) for d in common_dates],
            dtype=float,
        )

        daily_vol = float(np.std(port_daily_rets, ddof=1))
        ann_vol = daily_vol * np.sqrt(252.0)
        ann_ret = float(np.mean(port_daily_rets)) * 252.0

        sharpe = (ann_ret - rf) / ann_vol if ann_vol > 0 else 0.0

        downside_rets = port_daily_rets[port_daily_rets < 0]
        downside_vol = float(np.std(downside_rets, ddof=1)) * np.sqrt(252.0) if len(downside_rets) > 1 else ann_vol
        sortino = (ann_ret - rf) / downside_vol if downside_vol > 0 else 0.0

        cum_curve = np.cumprod(1.0 + port_daily_rets)
        running_max = np.maximum.accumulate(cum_curve)
        drawdowns = (cum_curve - running_max) / running_max
        max_dd = float(np.min(drawdowns)) * 100.0

        var_pct = float(np.percentile(port_daily_rets, 5))
        tail_rets = port_daily_rets[port_daily_rets <= var_pct]
        cvar_pct = float(np.mean(tail_rets)) if len(tail_rets) > 0 else var_pct

        var_95_amt = abs(var_pct) * total_val
        cvar_95_amt = abs(cvar_pct) * total_val
        beta_est = 1.0
        estimation_status = "OBSERVED_HISTORY"
        fx_note = (
            f" FX history unavailable for {', '.join(fx_unadjusted_currencies)}; instrument-currency returns used."
            if fx_unadjusted_currencies
            else f" All returns converted to {portfolio.reporting_currency}."
        )
        completeness_note = (
            f"Computed from {len(common_dates)} date-aligned overlapping historical trading sessions.{fx_note}"
        )
        methodology_note = (
            f"Constant-mix historical simulation using current portfolio weights across date-aligned EOD returns "
            f"(assumptions {assumptions['version']})."
        )
    else:
        base_ann_vol = float(assumptions["base_volatility"]) + (
            float(assumptions["hhi_volatility_slope"]) * (hhi / 10000.0)
        )
        daily_vol = base_ann_vol / np.sqrt(252.0)
        ann_vol = base_ann_vol
        assumed_ret = float(assumptions["assumed_annual_return"])

        sharpe = (assumed_ret - rf) / ann_vol
        sortino = sharpe * float(assumptions["sortino_multiplier"])
        max_dd = -round(ann_vol * float(assumptions["drawdown_multiplier"]) * 100.0, 2)

        var_95_amt = total_val * (1.645 * daily_vol)
        cvar_95_amt = total_val * (2.063 * daily_vol)
        beta_est = 1.05
        estimation_status = "PARAMETRIC_ESTIMATE"
        reason = (
            f"sufficient 15+ day price history is missing for: {', '.join(missing_history_symbols)}"
            if missing_history_symbols
            else "fewer than 14 overlapping trading dates exist across holdings"
        )
        completeness_note = f"Parametric volatility estimate applied because {reason}."
        methodology_note = (
            f"Parametric normal approximation using versioned assumptions {assumptions['version']} "
            f"(effective {assumptions['effective_date']})."
        )

    # 3. Stress Test Scenarios
    stress_tests = [
        StressTestScenario(
            scenario_name="10% Market Correction",
            shock_description="Broad -10% equity drawdown across holdings",
            estimated_portfolio_value=round(total_val * 0.90, 2),
            estimated_pnl_impact=round(-total_val * 0.10, 2),
            estimated_impact_pct=-10.0,
        ),
        StressTestScenario(
            scenario_name="20% Bear Market",
            shock_description="Sustained -20% global risk-off contraction",
            estimated_portfolio_value=round(total_val * 0.80, 2),
            estimated_pnl_impact=round(-total_val * 0.20, 2),
            estimated_impact_pct=-20.0,
        ),
        StressTestScenario(
            scenario_name="40% Severe Crash",
            shock_description="Systemic crisis / tail-risk shock (-40%)",
            estimated_portfolio_value=round(total_val * 0.60, 2),
            estimated_pnl_impact=round(-total_val * 0.40, 2),
            estimated_impact_pct=-40.0,
        ),
        StressTestScenario(
            scenario_name="20% Local Currency Depreciation",
            shock_description="FX appreciation benefit on non-GHS foreign holdings (+20% USD/EUR/GBP)",
            estimated_portfolio_value=round(
                total_val + sum(v * 0.20 for k, v in currency_totals.items() if k != "GHS"), 2
            ),
            estimated_pnl_impact=round(sum(v * 0.20 for k, v in currency_totals.items() if k != "GHS"), 2),
            estimated_impact_pct=round(
                (sum(v * 0.20 for k, v in currency_totals.items() if k != "GHS") / total_val * 100.0), 2
            ),
        ),
    ]

    return PortfolioRiskResponse(
        portfolio_id=portfolio.id,
        reporting_currency=portfolio.reporting_currency,
        total_market_value=round(total_val, 2),
        annualized_volatility_pct=round(ann_vol * 100.0, 2),
        sharpe_ratio=round(sharpe, 2),
        sortino_ratio=round(sortino, 2),
        max_drawdown_pct=round(max_dd, 2),
        var_95_daily_amount=round(var_95_amt, 2),
        cvar_95_daily_amount=round(cvar_95_amt, 2),
        portfolio_beta=round(beta_est, 2),
        concentration_hhi=hhi,
        sector_exposure=sector_exposure,
        currency_exposure=currency_exposure,
        stress_tests=stress_tests,
        data_completeness_note=completeness_note,
        estimation_status=estimation_status,
        methodology_note=methodology_note,
        assumptions_used=assumptions,
    )
