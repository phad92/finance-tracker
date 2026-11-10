import uuid
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class PortfolioCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    reporting_currency: str = Field(default="GHS", min_length=3, max_length=3)


class PortfolioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    reporting_currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    is_active: Optional[bool] = None


class PortfolioHoldingResponse(BaseModel):
    id: uuid.UUID
    portfolio_id: uuid.UUID
    instrument_id: uuid.UUID
    symbol: str
    instrument_name: str
    instrument_type: str
    quantity: float
    average_cost_per_share: float
    total_cost_basis: float
    current_price: float
    current_market_value: float
    currency: str
    unrealized_pnl: float
    realized_pnl: float

    class Config:
        from_attributes = True


class PortfolioResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    reporting_currency: str
    is_active: bool
    total_value_reporting: Optional[float] = 0.0
    total_cost_basis_reporting: Optional[float] = 0.0
    total_unrealized_pnl_reporting: Optional[float] = 0.0
    total_realized_pnl_reporting: Optional[float] = 0.0
    holdings_count: Optional[int] = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InvestmentTransactionCreate(BaseModel):
    instrument_id: uuid.UUID
    transaction_type: str = Field(..., description="BUY, SELL, SPLIT, BONUS")
    trade_date: date = Field(default_factory=date.today)
    settlement_date: Optional[date] = None
    quantity: float = Field(..., gt=0)
    price_per_share: float = Field(..., ge=0)
    fees: float = Field(default=0.0, ge=0)
    taxes: float = Field(default=0.0, ge=0)
    currency: str = Field(..., min_length=3, max_length=3)
    exchange_rate_to_reporting: Optional[float] = Field(default=None, description="Auto-resolved if omitted")
    notes: Optional[str] = None


class InvestmentTransactionResponse(BaseModel):
    id: uuid.UUID
    portfolio_id: uuid.UUID
    instrument_id: uuid.UUID
    symbol: Optional[str] = None
    transaction_type: str
    trade_date: date
    settlement_date: Optional[date] = None
    quantity: float
    price_per_share: float
    gross_amount: float
    fees: float
    taxes: float
    net_amount: float
    currency: str
    exchange_rate_to_reporting: float
    net_amount_reporting: float
    cost_basis_allocated: Optional[float] = None
    realized_gain_loss: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

