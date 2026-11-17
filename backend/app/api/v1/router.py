from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.forecasting import router as forecasting_router
from app.api.v1.intelligence import router as intelligence_router
from app.api.v1.markets import router as markets_router
from app.api.v1.options import router as options_router
from app.api.v1.portfolios import router as portfolios_router
from app.api.v1.risk import router as risk_router
from app.api.v1.wealth import router as wealth_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(wealth_router)
api_router.include_router(portfolios_router)
api_router.include_router(markets_router)
api_router.include_router(forecasting_router)
api_router.include_router(intelligence_router)
api_router.include_router(options_router)
api_router.include_router(risk_router)
