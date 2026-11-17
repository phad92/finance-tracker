from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api.v1.router import api_router
from app.config import settings
from app.core.middleware import RateLimitMiddleware, SecurityHeadersMiddleware
from app.database import AsyncSessionLocal, async_engine, Base
import app.models  # noqa: F401
from app.models.markets import Currency
from app.models.wealth import AssetCategory
from app.services.macro import seed_macro_indicators
from app.services.market_data import seed_market_master_data


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle handler."""
    # 0. Enforce production security configuration invariants
    settings.validate_production_security()

    # 1. Create database schema tables on startup if they don't exist
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. Seed baseline currencies and asset categories
    async with AsyncSessionLocal() as session:
        # Seed ISO currencies
        curr_stmt = select(Currency)
        curr_res = await session.execute(curr_stmt)
        if not curr_res.first():
            currencies = [
                Currency(code="GHS", name="Ghana Cedi", symbol="GH₵", is_active=True),
                Currency(code="USD", name="US Dollar", symbol="$", is_active=True),
                Currency(code="GBP", name="British Pound", symbol="£", is_active=True),
                Currency(code="EUR", name="Euro", symbol="€", is_active=True),
            ]
            session.add_all(currencies)

        # Seed initial asset categories
        cat_stmt = select(AssetCategory)
        cat_res = await session.execute(cat_stmt)
        if not cat_res.first():
            categories = [
                AssetCategory(code="CASH", name="Cash & Equivalents", description="Physical cash, petty cash", is_liquid=True),
                AssetCategory(code="MOBILE_MONEY", name="Mobile Money", description="MTN MoMo, Telecel Cash, AT Money", is_liquid=True),
                AssetCategory(code="BANK_ACCOUNT", name="Bank Account", description="Checking, savings, call accounts", is_liquid=True),
                AssetCategory(code="STOCKS_ETF", name="Listed Equities & ETFs", description="GSE, US, and international stocks", is_liquid=True),
                AssetCategory(code="GOVT_SECURITIES", name="Treasury Bills & Bonds", description="Government of Ghana T-Bills, Notes", is_liquid=False),
                AssetCategory(code="REAL_ESTATE", name="Real Estate & Land", description="Residential, commercial properties, plots", is_liquid=False),
                AssetCategory(code="VEHICLES", name="Vehicles", description="Automobiles and transport equipment", is_liquid=False),
                AssetCategory(code="PRIVATE_BUSINESS", name="Private Business Equity", description="Privately held business interests", is_liquid=False),
            ]
            session.add_all(categories)

        await session.commit()
        await seed_market_master_data(session)
        await seed_macro_indicators(session)

    yield

    # Shutdown
    await async_engine.dispose()


_docs_active = settings.DOCS_ENABLED and settings.ENVIRONMENT.lower() != "production"

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Investment & Wealth Intelligence Platform - Personal-first, multi-tenant capable API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if _docs_active else None,
    docs_url=f"{settings.API_V1_STR}/docs" if _docs_active else None,
    redoc_url=f"{settings.API_V1_STR}/redoc" if _docs_active else None,
    lifespan=lifespan,
)

# Defensive HTTP headers & endpoint rate limiting
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

# Configure CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
async def health_check():
    """System health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "reporting_currency": settings.DEFAULT_REPORTING_CURRENCY,
    }


# Mount API v1 Router
app.include_router(api_router, prefix=settings.API_V1_STR)

