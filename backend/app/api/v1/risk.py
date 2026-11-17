import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.identity import User
from app.schemas.risk import PortfolioRiskResponse
from app.services.risk import calculate_portfolio_risk

router = APIRouter(prefix="/risk", tags=["Portfolio Risk & Stress Testing"])


@router.get("/portfolio/{portfolio_id}", response_model=PortfolioRiskResponse)
async def get_portfolio_risk_metrics(
    portfolio_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortfolioRiskResponse:
    """
    Compute VaR (95%), CVaR, Sharpe/Sortino ratios, HHI concentration,
    and market stress-test scenarios for a user's portfolio.
    """
    try:
        return await calculate_portfolio_risk(db, portfolio_id, current_user.id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

