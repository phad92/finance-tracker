import uuid
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class OptionGreeks(BaseModel):
    delta: float
    gamma: float
    theta_daily: float
    vega_per_pct: float
    rho_per_pct: float


class OptionAnalyticsResult(BaseModel):
    theoretical_price: float
    intrinsic_value: float
    extrinsic_value: float
    break_even_price: float
    max_profit: Optional[float] = Field(default=None, description="None denotes theoretically unlimited")
    max_loss: Optional[float] = Field(default=None, description="None denotes theoretically unlimited")
    prob_itm_pct: float
    greeks: OptionGreeks
    pricing_model: str  # BLACK_SCHOLES or BINOMIAL_CRR
    valuation_label: str = "MODEL_ESTIMATED"
    underlying_spot_price: float
    underlying_price_date: Optional[date] = None


class OptionAnalyzeRequest(BaseModel):
    spot_price: float = Field(..., gt=0)
    strike_price: float = Field(..., gt=0)
    days_to_expiry: int = Field(..., ge=0, le=1825)
    volatility: float = Field(default=0.30, gt=0.001, le=5.0, description="Annualized IV e.g. 0.30 for 30%")
    risk_free_rate: float = Field(default=0.045, ge=0.0, le=0.50)
    option_type: str = Field(default="CALL", description="CALL or PUT")
    side: str = Field(default="LONG", description="LONG or SHORT")
    exercise_style: str = Field(default="AMERICAN", description="AMERICAN or EUROPEAN")
    contract_multiplier: int = Field(default=100, ge=1)
    contracts: int = Field(default=1, ge=1)
    entry_premium: Optional[float] = Field(default=None, ge=0)


class OptionLegInput(BaseModel):
    option_type: str = Field(..., description="CALL, PUT, or STOCK")
    side: str = Field(..., description="LONG or SHORT")
    strike_price: float = Field(..., ge=0)
    premium: float = Field(..., ge=0)
    contracts: int = Field(default=1, ge=1)
    contract_multiplier: int = Field(default=100, ge=1)


class StrategyPayoffRequest(BaseModel):
    underlying_spot: float = Field(..., gt=0)
    legs: List[OptionLegInput]
    price_range_pct: float = Field(default=0.35, gt=0.05, le=0.90)


class PayoffPoint(BaseModel):
    underlying_price: float
    pnl: float


class StrategyPayoffResponse(BaseModel):
    underlying_spot: float
    net_entry_cash_flow: float
    max_profit: Optional[float] = None
    max_loss: Optional[float] = None
    break_even_prices: List[float]
    curve: List[PayoffPoint]


class OptionPositionCreate(BaseModel):
    portfolio_id: Optional[uuid.UUID] = None
    underlying_symbol: str = Field(..., min_length=1, max_length=30)
    option_symbol: Optional[str] = None
    option_type: str = Field(..., description="CALL or PUT")
    side: str = Field(..., description="LONG or SHORT")
    strategy_tag: str = Field(default="SINGLE_LEG")
    exercise_style: str = Field(default="AMERICAN")
    strike_price: float = Field(..., gt=0)
    expiration_date: date
    contract_multiplier: int = Field(default=100, ge=1)
    contracts: int = Field(..., ge=1)
    entry_premium: float = Field(..., ge=0)
    fees: float = Field(default=0.0, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    assumed_volatility: float = Field(default=0.30, gt=0.01, le=3.0)
    notes: Optional[str] = None


class OptionPositionCloseRequest(BaseModel):
    action: str = Field(..., description="CLOSE, EXPIRE, EXERCISE, or ASSIGN")
    closing_premium: float = Field(default=0.0, ge=0)
    fees: float = Field(default=0.0, ge=0)
    trade_date: date = Field(default_factory=date.today)
    notes: Optional[str] = None


class OptionPositionResponse(BaseModel):
    id: uuid.UUID
    underlying_symbol: str
    option_symbol: Optional[str] = None
    option_type: str
    side: str
    strategy_tag: str
    exercise_style: str
    strike_price: float
    expiration_date: date
    contract_multiplier: int
    contracts: int
    notional_exposure: float
    entry_premium: float
    fees: float
    currency: str
    assumed_volatility: float
    status: str
    analytics: Optional[OptionAnalyticsResult] = None
    estimated_unrealized_pnl: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True

