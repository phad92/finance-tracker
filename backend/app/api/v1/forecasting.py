from fastapi import APIRouter, Depends, status

from app.core.deps import get_current_user
from app.models.identity import User
from app.schemas.forecasting import (
    GoalRequiredSavingsRequest,
    GoalRequiredSavingsResponse,
    MonteCarloRequest,
    MonteCarloResponse,
    ProjectionRequest,
    ProjectionResponse,
)
from app.services.forecasting import (
    calculate_monte_carlo_simulation,
    calculate_required_monthly_savings,
    calculate_wealth_projection,
)

router = APIRouter(prefix="/forecasting", tags=["Forecasting & Goal Planning"])


@router.post("/simulate", response_model=ProjectionResponse, status_code=status.HTTP_200_OK)
async def simulate_compound_growth(
    request: ProjectionRequest,
    current_user: User = Depends(get_current_user),
) -> ProjectionResponse:
    """
    Project month-by-month compound wealth growth, total contributions,
    and inflation-adjusted purchasing power over custom time horizons.
    """
    return calculate_wealth_projection(request)


@router.post("/goal-savings", response_model=GoalRequiredSavingsResponse, status_code=status.HTTP_200_OK)
async def calculate_goal_savings(
    request: GoalRequiredSavingsRequest,
    current_user: User = Depends(get_current_user),
) -> GoalRequiredSavingsResponse:
    """
    Calculate the exact monthly contribution required to reach a specific financial target
    given current principal, target horizon, expected return, and inflation.
    """
    return calculate_required_monthly_savings(request)


@router.post("/monte-carlo", response_model=MonteCarloResponse, status_code=status.HTTP_200_OK)
async def run_monte_carlo_simulation(
    request: MonteCarloRequest,
    current_user: User = Depends(get_current_user),
) -> MonteCarloResponse:
    """
    Execute vectorized Monte Carlo simulations to model probabilistic wealth outcomes,
    percentile cones (5th, 25th, 50th, 75th, 95th), and goal completion probability under market volatility.
    """
    return calculate_monte_carlo_simulation(request)


