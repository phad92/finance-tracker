import uuid
from datetime import date, datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class EconomicIndicatorResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    country_code: str
    category: str
    unit: str
    source: str
    source_url: Optional[str] = None
    acquisition_method: str = "BASELINE_SEED"
    update_cadence: Optional[str] = None
    explainer: Optional[str] = None
    latest_value: Optional[float] = None
    latest_date: Optional[date] = None

    class Config:
        from_attributes = True


class NewsArticleResponse(BaseModel):
    id: uuid.UUID
    title: str
    url: str
    publisher: str
    published_at: datetime
    summary: Optional[str] = None
    related_symbols: Optional[str] = None
    country_code: str

    class Config:
        from_attributes = True


class FactorScoreDetail(BaseModel):
    factor: str
    weight: float
    raw_score: float
    weighted_score: float
    rationale: str


class OpportunityScoreResponse(BaseModel):
    instrument_id: uuid.UUID
    symbol: str
    name: str
    total_score: float = Field(..., ge=0.0, le=100.0)
    rating: str  # STRONG_BUY, ACCUMULATE, HOLD, CAUTION
    factors: List[FactorScoreDetail]
    data_quality: str
    calculated_at: datetime


class ResearchReportRequest(BaseModel):
    instrument_id: uuid.UUID
    focus_question: Optional[str] = None


class ResearchReportContent(BaseModel):
    executive_summary: str
    investment_thesis: str
    market_overview: str
    company_financial_analysis: str
    valuation: str
    growth_catalysts: List[str]
    competitive_position: str
    key_risks: List[str]
    scenarios: Dict[str, str]  # bear, base, bull
    data_sources_and_dates: List[str]
    confidence_and_data_completeness: str
    thesis_invalidation_conditions: List[str]


class ResearchReportResponse(BaseModel):
    id: uuid.UUID
    instrument_id: uuid.UUID
    symbol: str
    title: str
    opportunity_score: float
    report_data: ResearchReportContent
    model_used: str
    data_quality_summary: str
    created_at: datetime

    class Config:
        from_attributes = True


class AssistantChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: Optional[uuid.UUID] = None


class AssistantChatResponse(BaseModel):
    conversation_id: uuid.UUID
    reply: str
    tools_invoked: List[str] = []
    model_used: str

