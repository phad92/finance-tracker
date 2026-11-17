import uuid
from typing import Dict, List, Optional
from pydantic import BaseModel


class StressTestScenario(BaseModel):
    scenario_name: str
    shock_description: str
    estimated_portfolio_value: float
    estimated_pnl_impact: float
    estimated_impact_pct: float


class ConcentrationMetric(BaseModel):
    label: str
    value: float
    weight_pct: float


class PortfolioRiskResponse(BaseModel):
    portfolio_id: uuid.UUID
    reporting_currency: str
    total_market_value: float
    annualized_volatility_pct: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    var_95_daily_amount: Optional[float] = None
    cvar_95_daily_amount: Optional[float] = None
    portfolio_beta: Optional[float] = None
    concentration_hhi: float
    sector_exposure: List[ConcentrationMetric]
    currency_exposure: List[ConcentrationMetric]
    stress_tests: List[StressTestScenario]
    data_completeness_note: str
    estimation_status: str  # OBSERVED_HISTORY or PARAMETRIC_ESTIMATE

