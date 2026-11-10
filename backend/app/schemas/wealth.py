import uuid
from datetime import date, datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class AssetCategoryResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: Optional[str] = None
    is_liquid: bool

    class Config:
        from_attributes = True


class AssetValuationCreate(BaseModel):
    valuation_date: date = Field(default_factory=date.today)
    value_original_currency: float = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)
    exchange_rate_to_reporting: Optional[float] = Field(default=None, description="Auto-fetched if omitted")
    valuation_method: str = Field(default="MANUAL", description="MANUAL, APPRAISAL, MARKET, COST")
    notes: Optional[str] = None


class AssetValuationResponse(BaseModel):
    id: uuid.UUID
    asset_id: uuid.UUID
    valuation_date: date
    value_original_currency: float
    currency: str
    exchange_rate_to_reporting: float
    value_reporting_currency: float
    valuation_method: str
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AssetCreate(BaseModel):
    category_id: uuid.UUID
    name: str = Field(..., min_length=2, max_length=255)
    institution: Optional[str] = None
    currency: str = Field(default="GHS", min_length=3, max_length=3)
    ownership_percentage: float = Field(default=100.0, ge=0.0, le=100.0)
    initial_valuation: Optional[AssetValuationCreate] = None
    notes: Optional[str] = None


class AssetUpdate(BaseModel):
    name: Optional[str] = None
    institution: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    ownership_percentage: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class AssetResponse(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    category_name: Optional[str] = None
    name: str
    institution: Optional[str] = None
    currency: str
    ownership_percentage: float
    is_active: bool
    latest_valuation: Optional[AssetValuationResponse] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LiabilityCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    institution: Optional[str] = None
    category: str = Field(default="PERSONAL_LOAN", description="MORTGAGE, PERSONAL_LOAN, CREDIT_CARD, BUSINESS_LOAN")
    currency: str = Field(default="GHS", min_length=3, max_length=3)
    original_balance: float = Field(..., ge=0)
    current_balance: float = Field(..., ge=0)
    interest_rate: Optional[float] = Field(default=None, description="e.g. 0.22 for 22%")
    monthly_payment: Optional[float] = None
    start_date: Optional[date] = None
    maturity_date: Optional[date] = None
    notes: Optional[str] = None


class LiabilityUpdate(BaseModel):
    name: Optional[str] = None
    institution: Optional[str] = None
    category: Optional[str] = None
    current_balance: Optional[float] = Field(default=None, ge=0)
    interest_rate: Optional[float] = None
    monthly_payment: Optional[float] = None
    maturity_date: Optional[date] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class LiabilityResponse(BaseModel):
    id: uuid.UUID
    name: str
    institution: Optional[str] = None
    category: str
    currency: str
    original_balance: float
    current_balance: float
    interest_rate: Optional[float] = None
    monthly_payment: Optional[float] = None
    start_date: Optional[date] = None
    maturity_date: Optional[date] = None
    is_active: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NetWorthSummary(BaseModel):
    reporting_currency: str
    total_assets: float
    total_liabilities: float
    net_worth: float
    assets_by_category: Dict[str, float]
    currency_exposure: Dict[str, float]
    as_of_date: date
