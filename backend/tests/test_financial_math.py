import math
import uuid
from datetime import date, timedelta
from types import SimpleNamespace
import pytest

from app.schemas.forecasting import (
    GoalRequiredSavingsRequest,
    MonteCarloRequest,
    ProjectionRequest,
)
from app.schemas.options import OptionAnalyzeRequest, OptionLegInput, StrategyPayoffRequest
from app.services.forecasting import (
    calculate_monte_carlo_simulation,
    calculate_required_monthly_savings,
    calculate_wealth_projection,
)
from app.services.macro import build_indicator_response
from app.services.options_engine import calculate_option_analytics, compute_strategy_payoff
from app.services.performance import calculate_xirr
from app.services.risk import calculate_portfolio_risk


class _FakeScalarResult:
    def __init__(self, obj):
        self._obj = obj

    def scalar_one_or_none(self):
        return self._obj


class _FakeAsyncSession:
    def __init__(self, obj):
        self._obj = obj

    async def execute(self, stmt):
        return _FakeScalarResult(self._obj)


def test_black_scholes_put_call_parity_and_greeks():
    """Verify Put-Call Parity C - P = S - K * exp(-r*T) and Greek sign conventions."""
    S, K, days, r, vol = 200.0, 210.0, 90, 0.05, 0.25
    call_res = calculate_option_analytics(
        OptionAnalyzeRequest(
            spot_price=S,
            strike_price=K,
            days_to_expiry=days,
            volatility=vol,
            risk_free_rate=r,
            option_type="CALL",
            side="LONG",
            exercise_style="EUROPEAN",
        )
    )
    put_res = calculate_option_analytics(
        OptionAnalyzeRequest(
            spot_price=S,
            strike_price=K,
            days_to_expiry=days,
            volatility=vol,
            risk_free_rate=r,
            option_type="PUT",
            side="LONG",
            exercise_style="EUROPEAN",
        )
    )

    T = days / 365.0
    rhs = S - K * math.exp(-r * T)
    lhs = call_res.theoretical_price - put_res.theoretical_price
    assert lhs == pytest.approx(rhs, abs=1e-2)
    assert call_res.valuation_label == "MODEL_ESTIMATED"
    assert 0.0 < call_res.greeks.delta < 1.0
    assert -1.0 < put_res.greeks.delta < 0.0
    assert call_res.greeks.gamma > 0
    assert call_res.greeks.vega_per_pct > 0


def test_american_binomial_and_variable_multiplier():
    """Verify American CRR put >= European put and variable contract_multiplier scaling."""
    eu_put = calculate_option_analytics(
        OptionAnalyzeRequest(
            spot_price=90.0,
            strike_price=100.0,
            days_to_expiry=180,
            volatility=0.30,
            risk_free_rate=0.06,
            option_type="PUT",
            side="LONG",
            exercise_style="EUROPEAN",
            contract_multiplier=10,
            entry_premium=12.0,
        )
    )
    am_put = calculate_option_analytics(
        OptionAnalyzeRequest(
            spot_price=90.0,
            strike_price=100.0,
            days_to_expiry=180,
            volatility=0.30,
            risk_free_rate=0.06,
            option_type="PUT",
            side="LONG",
            exercise_style="AMERICAN",
            contract_multiplier=100,
            entry_premium=12.0,
        )
    )
    assert am_put.theoretical_price >= eu_put.theoretical_price - 1e-3
    assert eu_put.max_loss == pytest.approx(120.0, abs=0.01)
    assert am_put.max_loss == pytest.approx(1200.0, abs=0.01)


def test_strategy_payoff_bull_call_spread():
    """Verify bounded max profit/loss and break-even for a vertical Bull Call Spread."""
    res = compute_strategy_payoff(
        StrategyPayoffRequest(
            underlying_spot=105.0,
            price_range_pct=0.30,
            legs=[
                OptionLegInput(option_type="CALL", side="LONG", strike_price=100.0, premium=8.0, contracts=1, contract_multiplier=100),
                OptionLegInput(option_type="CALL", side="SHORT", strike_price=120.0, premium=2.0, contracts=1, contract_multiplier=100),
            ],
        )
    )
    # Net debit = (8 - 2) * 100 = -600; Max profit = (20 - 6) * 100 = 1400
    assert res.net_entry_cash_flow == pytest.approx(-600.0, abs=0.01)
    assert res.max_loss == pytest.approx(-600.0, abs=0.01)
    assert res.max_profit == pytest.approx(1400.0, abs=0.01)
    assert len(res.break_even_prices) == 1
    assert res.break_even_prices[0] == pytest.approx(106.0, abs=1.0)


def test_xirr_calculation_and_invalid_signs():
    """Verify XIRR solves exact annualized IRR and rejects single-sign sequences."""
    cfs = [
        (date(2025, 1, 1), -1000.0),
        (date(2026, 1, 1), 1100.0),
    ]
    irr = calculate_xirr(cfs)
    assert irr is not None
    assert irr == pytest.approx(10.0, abs=0.1)

    assert calculate_xirr([(date(2025, 1, 1), -100.0), (date(2026, 1, 1), -200.0)]) is None


def test_forecasting_compound_goal_and_monte_carlo():
    """Verify deterministic growth, zero-rate savings math, and Monte Carlo quantile order."""
    proj = calculate_wealth_projection(
        ProjectionRequest(
            initial_amount=10000.0,
            monthly_contribution=500.0,
            annual_return_rate=0.12,
            investment_years=5,
            inflation_rate=0.08,
            contribution_growth_rate=0.0,
        )
    )
    assert proj.final_nominal_wealth > proj.total_contributions
    assert proj.final_real_wealth < proj.final_nominal_wealth

    goal = calculate_required_monthly_savings(
        GoalRequiredSavingsRequest(
            target_amount=12000.0,
            current_amount=0.0,
            target_years=1.0,
            expected_annual_return=0.0,
            inflation_rate=0.0,
        )
    )
    assert goal.required_monthly_savings_nominal == pytest.approx(1000.0, abs=0.01)

    mc = calculate_monte_carlo_simulation(
        MonteCarloRequest(
            initial_amount=10000.0,
            monthly_contribution=500.0,
            expected_annual_return=0.15,
            annual_volatility=0.18,
            investment_years=5,
            num_simulations=200,
        )
    )
    last_p = mc.trajectory[-1].percentiles
    assert last_p.p5 <= last_p.p25 <= last_p.p50 <= last_p.p75 <= last_p.p95


@pytest.mark.asyncio
async def test_portfolio_risk_hhi_and_estimation_disclosure():
    """Verify HHI calculation, stress tests, and OBSERVED_HISTORY vs PARAMETRIC_ESTIMATE disclosure."""
    pid = uuid.uuid4()
    uid = uuid.uuid4()

    # Case 1: Single holding with sparse price history -> HHI = 10000, PARAMETRIC_ESTIMATE
    holding_sparse = SimpleNamespace(
        quantity=10.0,
        current_market_value=1000.0,
        currency="USD",
        instrument=SimpleNamespace(symbol="AAPL", sector="Technology", prices=[]),
    )
    portfolio_sparse = SimpleNamespace(id=pid, reporting_currency="USD", holdings=[holding_sparse])
    risk_param = await calculate_portfolio_risk(_FakeAsyncSession(portfolio_sparse), pid, uid)
    assert risk_param.concentration_hhi == pytest.approx(10000.0, abs=0.1)
    assert risk_param.estimation_status == "PARAMETRIC_ESTIMATE"
    assert len(risk_param.stress_tests) == 4

    # Case 2: Equal 2-stock portfolio with 20 daily closes -> HHI = 5000, OBSERVED_HISTORY
    base_day = date(2026, 1, 1)
    prices = [
        SimpleNamespace(price_date=base_day + timedelta(days=i), close=100.0 + (i * 0.5) + ((-1) ** i) * 0.8)
        for i in range(20)
    ]
    h1 = SimpleNamespace(
        quantity=10.0,
        current_market_value=5000.0,
        currency="USD",
        instrument=SimpleNamespace(symbol="MSFT", sector="Technology", prices=prices),
    )
    h2 = SimpleNamespace(
        quantity=50.0,
        current_market_value=5000.0,
        currency="GHS",
        instrument=SimpleNamespace(symbol="MTNGH", sector="Telecom", prices=prices),
    )
    portfolio_obs = SimpleNamespace(id=pid, reporting_currency="GHS", holdings=[h1, h2])
    risk_obs = await calculate_portfolio_risk(_FakeAsyncSession(portfolio_obs), pid, uid)
    assert risk_obs.concentration_hhi == pytest.approx(5000.0, abs=0.1)
    assert risk_obs.estimation_status == "OBSERVED_HISTORY"


def test_macro_indicator_provenance_and_explainers():
    """Verify live World Bank indicators vs baseline reference seeds attach URL, cadence, and explainer."""
    live_ind = SimpleNamespace(
        id=uuid.uuid4(),
        code="GHA_GDP_GROWTH",
        name="Ghana Annual GDP Growth Rate",
        country_code="GHA",
        category="GDP",
        unit="%",
        source="World Bank API",
        latest_value=5.9544,
        latest_date=date(2025, 12, 31),
    )
    live_resp = build_indicator_response(live_ind)
    assert live_resp.acquisition_method == "LIVE_API"
    assert live_resp.source_url == "https://data.worldbank.org/indicator/NY.GDP.MKTP.KD.ZG?locations=GH"
    assert live_resp.update_cadence == "Annual"
    assert "Gross Domestic Product" in (live_resp.explainer or "")

    seed_ind = SimpleNamespace(
        id=uuid.uuid4(),
        code="GHA_TBILL_91D",
        name="Ghana 91-Day Treasury Bill Yield",
        country_code="GHA",
        category="YIELD",
        unit="%",
        source="Bank of Ghana",
        latest_value=25.45,
        latest_date=date(2026, 10, 31),
    )
    seed_resp = build_indicator_response(seed_ind)
    assert seed_resp.acquisition_method == "BASELINE_SEED"
    assert seed_resp.source_url == "https://www.bog.gov.gh/treasury-and-the-markets/treasury-bill-rates/"
    assert seed_resp.update_cadence == "Weekly tender"
    assert "91-day Government of Ghana" in (seed_resp.explainer or "")


