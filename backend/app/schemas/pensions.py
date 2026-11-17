import uuid
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PensionSchemeCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    tier: str = Field(..., pattern="^(TIER_1|TIER_2|TIER_3)$")
    scheme_type: str = Field(..., min_length=2, max_length=50)
    trustee_provider: Optional[str] = None
    npra_reg_ref: Optional[str] = None
    source_url: Optional[str] = None


class PensionSchemeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    tier: str
    scheme_type: str
    trustee_provider: Optional[str] = None
    npra_reg_ref: Optional[str] = None
    source_url: Optional[str] = None
    is_custom: bool
    is_active: bool
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None


class PensionAccountCreate(BaseModel):
    scheme_id: uuid.UUID
    account_name: str = Field(..., min_length=2, max_length=255)
    member_reference: Optional[str] = Field(default=None, max_length=100)
    employer_name: Optional[str] = Field(default=None, max_length=255)
    currency: str = Field(default="GHS", min_length=3, max_length=3)
    membership_start_date: Optional[date] = None
    notes: Optional[str] = None


class PensionAccountResponse(BaseModel):
    id: uuid.UUID
    scheme_id: uuid.UUID
    scheme_name: Optional[str] = None
    trustee_provider: Optional[str] = None
    tier: str
    account_name: str
    member_reference_masked: Optional[str] = None
    employer_name: Optional[str] = None
    currency: str
    membership_start_date: Optional[date] = None
    status: str
    latest_balance: float = 0.0
    last_valuation_date: Optional[date] = None
    notes: Optional[str] = None
    created_at: datetime


class PensionContributionCreate(BaseModel):
    pay_period: str = Field(..., min_length=4, max_length=20)
    contribution_date: date = Field(default_factory=date.today)
    employee_amount: float = Field(default=0.0, ge=0)
    employer_amount: float = Field(default=0.0, ge=0)
    voluntary_amount: float = Field(default=0.0, ge=0)
    expected_amount: Optional[float] = Field(default=None, ge=0)
    actual_credited_amount: float = Field(..., ge=0)
    source: str = Field(default="MANUAL", max_length=50)
    notes: Optional[str] = None


class PensionContributionResponse(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    pay_period: str
    contribution_date: date
    employee_amount: float
    employer_amount: float
    voluntary_amount: float
    expected_amount: Optional[float] = None
    actual_credited_amount: float
    reconciliation_variance: Optional[float] = None
    source: str
    notes: Optional[str] = None
    created_at: datetime


class PensionValuationCreate(BaseModel):
    valuation_date: date = Field(default_factory=date.today)
    statement_balance: float = Field(..., ge=0)
    units: Optional[float] = Field(default=None, ge=0)
    unit_price: Optional[float] = Field(default=None, ge=0)
    source_document_ref: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = None


class PensionValuationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    valuation_date: date
    statement_balance: float
    units: Optional[float] = None
    unit_price: Optional[float] = None
    source_document_ref: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime


class SSNITProfileUpsert(BaseModel):
    ssnit_number: Optional[str] = Field(default=None, max_length=50)
    membership_start_date: Optional[date] = None
    total_contribution_months: int = Field(default=0, ge=0, le=720)
    last_statement_date: Optional[date] = None
    notes: Optional[str] = None


class SSNITProfileResponse(BaseModel):
    ssnit_number_masked: Optional[str] = None
    membership_start_date: Optional[date] = None
    total_contribution_months: int
    last_statement_date: Optional[date] = None
    notes: Optional[str] = None


class PensionEmploymentPeriodCreate(BaseModel):
    employer_name: str = Field(..., min_length=2, max_length=255)
    start_date: date
    end_date: Optional[date] = None
    pensionable_salary: Optional[float] = Field(default=None, ge=0)
    currency: str = Field(default="GHS", min_length=3, max_length=3)
    notes: Optional[str] = None


class PensionEmploymentPeriodResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employer_name: str
    start_date: date
    end_date: Optional[date] = None
    pensionable_salary: Optional[float] = None
    currency: str
    notes: Optional[str] = None


class SSNITHistoryResponse(BaseModel):
    profile: Optional[SSNITProfileResponse] = None
    employment_periods: List[PensionEmploymentPeriodResponse]


class PensionSummaryResponse(BaseModel):
    reporting_currency: str
    funded_tier2_balance: float
    funded_tier3_balance: float
    total_funded_retirement_balance: float
    tier2_expected_contributions: float
    tier2_actual_credited: float
    tier2_reconciliation_variance: float
    ssnit_contribution_months: int
    ssnit_last_statement_date: Optional[date] = None
    last_statement_date: Optional[date] = None
    active_accounts_count: int
    payroll_framework_note: str
    fx_warning: Optional[str] = None


class SSNITBenefitEstimateCreate(BaseModel):
    estimate_date: date = Field(default_factory=date.today)
    target_retirement_age: int = Field(default=60, ge=50, le=75)
    source_type: str = Field(default="STATEMENT_DERIVED", pattern="^(STATEMENT_DERIVED|USER_ENTERED)$")
    estimated_monthly_pension: float = Field(..., ge=0)
    currency: str = Field(default="GHS", min_length=3, max_length=3)
    data_completeness_note: Optional[str] = None


class SSNITBenefitEstimateResponse(BaseModel):
    id: uuid.UUID
    estimate_date: date
    target_retirement_age: int
    source_type: str
    methodology_version: str
    estimated_monthly_pension: float
    currency: str
    data_completeness_note: Optional[str] = None
    disclaimer: str


class PensionForecastRequest(BaseModel):
    current_age: int = Field(..., ge=18, le=75)
    retirement_age: int = Field(..., ge=40, le=80)
    pensionable_salary: float = Field(default=0.0, ge=0)
    salary_growth_pct: float = Field(default=5.0, ge=0, le=30)
    tier2_rate_pct: float = Field(default=5.0, ge=0, le=30)
    tier3_monthly: float = Field(default=0.0, ge=0)
    employer_match_pct: float = Field(default=0.0, ge=0, le=100)
    expected_return_pct: float = Field(default=12.0, ge=-10, le=40)
    inflation_pct: float = Field(default=8.0, ge=0, le=40)
    annual_fee_pct: float = Field(default=1.5, ge=0, le=10)
    drawdown_years: int = Field(default=20, ge=5, le=40)
    include_ssnit_estimate: bool = True


class PensionForecastPoint(BaseModel):
    age: int
    year: int
    tier2_nominal: float
    tier3_nominal: float
    total_funded_nominal: float
    total_funded_real: float
    cumulative_contributions: float
    cumulative_growth: float


class PensionSensitivityScenario(BaseModel):
    scenario_name: str
    projected_funded_nominal: float
    projected_funded_real: float
    estimated_monthly_funded_income_real: float


class PensionForecastResponse(BaseModel):
    forecast_id: Optional[uuid.UUID] = None
    reporting_currency: str
    starting_tier2_balance: float
    starting_tier3_balance: float
    projected_tier2_nominal: float
    projected_tier3_nominal: float
    projected_funded_nominal: float
    projected_funded_real: float
    total_contributions_projected: float
    total_investment_growth_nominal: float
    estimated_monthly_funded_income_nominal: float
    estimated_monthly_funded_income_real: float
    ssnit_estimated_monthly_pension: Optional[float] = None
    combined_estimated_monthly_income_nominal: float
    trajectory: List[PensionForecastPoint]
    sensitivity: List[PensionSensitivityScenario]
    model_version: str
    disclaimer: str
