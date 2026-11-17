import uuid
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ExchangeResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    country_code: str
    currency_code: str

    class Config:
        from_attributes = True


class InstrumentCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=30)
    name: str = Field(..., min_length=2, max_length=255)
    exchange_code: str = Field(..., description="e.g. GSE, NYSE, NASDAQ")
    instrument_type: str = Field(default="EQUITY", description="EQUITY, ETF, BOND, T_BILL")
    currency_code: str = Field(default="GHS", min_length=3, max_length=3)
    sector: Optional[str] = None
    isin: Optional[str] = None


class InstrumentPriceResponse(BaseModel):
    id: uuid.UUID
    instrument_id: uuid.UUID
    price_date: date
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: float
    volume: Optional[float] = None
    source: str
    data_quality: str

    class Config:
        from_attributes = True


class InstrumentResponse(BaseModel):
    id: uuid.UUID
    symbol: str
    name: str
    exchange_id: uuid.UUID
    exchange_code: Optional[str] = None
    instrument_type: str
    currency_code: str
    sector: Optional[str] = None
    latest_price: Optional[float] = None
    latest_price_date: Optional[date] = None
    data_source: Optional[str] = None

    class Config:
        from_attributes = True


class MarketSyncResult(BaseModel):
    synced_count: int
    failed_symbols: List[str] = []
    source: str
    message: str

