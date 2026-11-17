import uuid
from collections import defaultdict
from typing import Dict, List
import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.investments import Portfolio, PortfolioHolding
from app.models.markets import Instrument
from app.schemas.risk import ConcentrationMetric, PortfolioRiskResponse, StressTestScenario


async def calculate_portfolio_risk(
    db: AsyncSession,
    portfolio_id: uuid.UUID,
    user_id: uuid.UUID,
) -> PortfolioRiskResponse:
    """
    Compute institutional portfolio risk metrics (Volatility, Sharpe, Sortino, Max Drawdown,
    95% VaR, 95% CVaR, Concentration HHI) and run stress test simulations (Module 9).
    Explicitly discloses whether metrics are derived from observed price series or parametric estimates.
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

    # Herfindahl-Hirschman Index (0 to 10,000 scale; >2,500 indicates high concentration)
    hhi = round(sum((w * 100.0) ** 2 for w in weights), 1)

    sector_exposure = [
        ConcentrationMetric(label=k, value=round(v, 2), weight_pct=round(v / total_val * 100.0, 1))
        for k, v in sorted(sector_totals.items(), key=lambda x: x[1], reverse=True)
    ]
    currency_exposure = [
        ConcentrationMetric(label=k, value=round(v, 2), weight_pct=round(v / total_val * 100.0, 1))
        for k, v in sorted(currency_totals.items(), key=lambda x: x[1], reverse=True)
    ]

    # 2. Historical Return Series vs Parametric Estimate
    # Check if instruments have >= 15 historical price points
    observed_returns_list = []
    missing_history_symbols = []

    for h in holdings:
        prices = sorted(h.instrument.prices, key=lambda p: p.price_date) if h.instrument else []
        if len(prices) >= 15:
            closes = np.array([float(p.close) for p in prices], dtype=float)
            daily_rets = np.diff(closes) / closes[:-1]
            observed_returns_list.append((float(h.current_market_value) / total_val, daily_rets))
        else:
            missing_history_symbols.append(h.instrument.symbol if h.instrument else "UNKNOWN")

    if len(observed_returns_list) == len(holdings) and len(observed_returns_list) > 0:
        # Align lengths to minimum common history length
        min_len = min(len(r[1]) for r in observed_returns_list)
        port_daily_rets = np.zeros(min_len)
        for w, rets in observed_returns_list:
            port_daily_rets += w * rets[-min_len:]

        daily_vol = float(np.std(port_daily_rets, ddof=1))
        ann_vol = daily_vol * np.sqrt(252.0)
        ann_ret = float(np.mean(port_daily_rets)) * 252.0

        rf = 0.045 if portfolio.reporting_currency == "USD" else 0.18
        sharpe = (ann_ret - rf) / ann_vol if ann_vol > 0 else 0.0

        downside_rets = port_daily_rets[port_daily_rets < 0]
        downside_vol = float(np.std(downside_rets, ddof=1)) * np.sqrt(252.0) if len(downside_rets) > 1 else ann_vol
        sortino = (ann_ret - rf) / downside_vol if downside_vol > 0 else 0.0

        # Cumulative equity curve for Max Drawdown
        cum_curve = np.cumprod(1.0 + port_daily_rets)
        running_max = np.maximum.accumulate(cum_curve)
        drawdowns = (cum_curve - running_max) / running_max
        max_dd = float(np.min(drawdowns)) * 100.0

        # Historical 95% VaR & CVaR (1-day)
        var_pct = float(np.percentile(port_daily_rets, 5))
        tail_rets = port_daily_rets[port_daily_rets <= var_pct]
        cvar_pct = float(np.mean(tail_rets)) if len(tail_rets) > 0 else var_pct

        var_95_amt = abs(var_pct) * total_val
        cvar_95_amt = abs(cvar_pct) * total_val
        beta_est = 1.0
        estimation_status = "OBSERVED_HISTORY"
        completeness_note = f"Computed from {min_len} overlapping historical trading sessions."
    else:
        # Parametric baseline estimate when EOD history is incomplete
        # Single-stock concentrated portfolios carry higher idiosyncratic volatility (~22-28%)
        base_ann_vol = 0.16 + (0.12 * (hhi / 10000.0))
        daily_vol = base_ann_vol / np.sqrt(252.0)
        ann_vol = base_ann_vol
        assumed_ret = 0.14 if portfolio.reporting_currency == "USD" else 0.22
        rf = 0.045 if portfolio.reporting_currency == "USD" else 0.18

        sharpe = (assumed_ret - rf) / ann_vol
        sortino = sharpe * 1.35
        max_dd = -round(ann_vol * 1.65 * 100.0, 2)

        # Normal parametric 95% VaR (z = 1.645) and CVaR (2.063)
        var_95_amt = total_val * (1.645 * daily_vol)
        cvar_95_amt = total_val * (2.063 * daily_vol)
        beta_est = 1.05
        estimation_status = "PARAMETRIC_ESTIMATE"
        completeness_note = (
            f"Parametric volatility estimate applied because sufficient 15+ day price history is missing for: "
            f"{', '.join(missing_history_symbols)}."
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
    )

