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
