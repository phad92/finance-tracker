from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.portfolios import router as portfolios_router
from app.api.v1.wealth import router as wealth_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(wealth_router)
api_router.include_router(portfolios_router)
