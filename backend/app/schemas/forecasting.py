from typing import List, Optional
from pydantic import BaseModel, Field


class ProjectionRequest(BaseModel):
    initial_amount: float = Field(default=0.0, ge=0.0)
    monthly_contribution: float = Field(default=500.0, ge=0.0)
    annual_return_rate: float = Field(default=0.15, description="Expected return, e.g. 0.15 for 15%")
    investment_years: int = Field(default=10, ge=1, le=50)
    inflation_rate: float = Field(default=0.10, ge=0.0, description="Annual inflation rate, e.g. 0.10 for 10%")
    contribution_growth_rate: float = Field(default=0.05, ge=0.0, description="Annual increase in contributions, e.g. 0.05 for 5%")


class YearlyProjectionPoint(BaseModel):
    year: int
    nominal_wealth: float
    real_wealth_inflation_adjusted: float
    total_contributions: float
    total_investment_gains: float


class ProjectionResponse(BaseModel):
    initial_amount: float
    final_nominal_wealth: float
    final_real_wealth: float
    total_contributions: float
    total_investment_gains: float
    yearly_trajectory: List[YearlyProjectionPoint]


class GoalRequiredSavingsRequest(BaseModel):
    target_amount: float = Field(..., gt=0.0)
    current_amount: float = Field(default=0.0, ge=0.0)
    target_years: float = Field(..., gt=0.0, le=50.0)
    expected_annual_return: float = Field(default=0.15, ge=0.0)
    inflation_rate: float = Field(default=0.10, ge=0.0)


class GoalRequiredSavingsResponse(BaseModel):
    target_amount: float
    current_amount: float
    target_years: float
    required_monthly_savings_nominal: float
    required_monthly_savings_inflation_adjusted: float
    projected_total_contributed: float
    projected_total_growth: float


class MonteCarloRequest(BaseModel):
    initial_amount: float = Field(default=10000.0, ge=0.0)
    monthly_contribution: float = Field(default=1000.0, ge=0.0)
    expected_annual_return: float = Field(default=0.15, description="Expected average return, e.g. 0.15 for 15%")
    annual_volatility: float = Field(default=0.18, ge=0.01, le=1.0, description="Annual return standard deviation, e.g. 0.18 for 18%")
    investment_years: int = Field(default=10, ge=1, le=40)
    num_simulations: int = Field(default=1000, ge=100, le=5000)
    inflation_rate: float = Field(default=0.10, ge=0.0)
    target_wealth_goal: Optional[float] = Field(default=None, gt=0.0)


class MonteCarloPercentiles(BaseModel):
    p5: float = Field(description="5th percentile (Bear Scenario)")
    p25: float = Field(description="25th percentile (Below Average)")
    p50: float = Field(description="50th percentile (Median)")
    p75: float = Field(description="75th percentile (Above Average)")
    p95: float = Field(description="95th percentile (Bull Scenario)")


class MonteCarloYearPoint(BaseModel):
    year: int
    percentiles: MonteCarloPercentiles
    total_contributions: float


class MonteCarloResponse(BaseModel):
    investment_years: int
    num_simulations: int
    expected_annual_return: float
    annual_volatility: float
    trajectory: List[MonteCarloYearPoint]
    probability_of_reaching_goal: Optional[float] = None
    target_wealth_goal: Optional[float] = None


