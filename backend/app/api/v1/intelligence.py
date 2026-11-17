import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.identity import User
from app.models.intelligence import EconomicIndicator, NewsArticle, ResearchReport
from app.schemas.intelligence import (
    AssistantChatRequest,
    AssistantChatResponse,
    EconomicIndicatorResponse,
    NewsArticleResponse,
    OpportunityScoreResponse,
    ResearchReportContent,
    ResearchReportRequest,
    ResearchReportResponse,
)
from app.services.ai_intelligence import (
    chat_with_financial_assistant,
    generate_structured_research_report,
)
from app.services.macro import build_indicator_response, sync_rss_news, sync_world_bank_macro
from app.services.scoring import compute_opportunity_score

router = APIRouter(prefix="/intelligence", tags=["AI Intelligence, Macro & Research"])


@router.get("/macro", response_model=List[EconomicIndicatorResponse])
async def list_macro_indicators(
    country_code: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[EconomicIndicatorResponse]:
    """List macroeconomic indicators with source provenance and plain-language explainers."""
    stmt = select(EconomicIndicator).order_by(EconomicIndicator.country_code, EconomicIndicator.name)
    if country_code:
        stmt = stmt.where(EconomicIndicator.country_code == country_code.upper().strip())
    result = await db.execute(stmt)
    return [build_indicator_response(ind) for ind in result.scalars().all()]


@router.post("/macro/sync", status_code=status.HTTP_200_OK)
async def sync_macro_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Synchronize GDP growth and CPI inflation series from the free public World Bank REST API."""
    return await sync_world_bank_macro(db)


@router.get("/news", response_model=List[NewsArticleResponse])
async def list_market_news(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[NewsArticle]:
    """List latest financial news articles and ticker-tagged market events."""
    stmt = select(NewsArticle).order_by(desc(NewsArticle.published_at)).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/news/sync", status_code=status.HTTP_200_OK)
async def sync_market_news(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch and classify latest financial headlines from permitted public RSS feeds."""
    return await sync_rss_news(db)


@router.get("/opportunity-score/{instrument_id}", response_model=OpportunityScoreResponse)
async def get_opportunity_score(
    instrument_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OpportunityScoreResponse:
    """Compute the deterministic multi-factor quantitative opportunity score for an instrument."""
    try:
        return await compute_opportunity_score(db, instrument_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instrument not found")


@router.post("/research-reports", response_model=ResearchReportResponse, status_code=status.HTTP_201_CREATED)
async def create_research_report(
    req: ResearchReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResearchReportResponse:
    """Generate and persist a 12-section structured company research report."""
    try:
        return await generate_structured_research_report(
            db=db,
            user_id=current_user.id,
            instrument_id=req.instrument_id,
            focus_question=req.focus_question,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instrument not found")


@router.get("/research-reports", response_model=List[ResearchReportResponse])
async def list_research_reports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ResearchReportResponse]:
    """Retrieve saved research reports belonging to the authenticated user."""
    stmt = (
        select(ResearchReport)
        .where(ResearchReport.user_id == current_user.id)
        .order_by(desc(ResearchReport.created_at))
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [
        ResearchReportResponse(
            id=r.id,
            instrument_id=r.instrument_id,
            symbol=r.symbol,
            title=r.title,
            opportunity_score=float(r.opportunity_score),
            report_data=ResearchReportContent(**r.report_data),
            model_used=r.model_used,
            data_quality_summary=r.data_quality_summary,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/assistant/chat", response_model=AssistantChatResponse)
async def assistant_chat(
    req: AssistantChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssistantChatResponse:
    """
    Interact conversationally with the AI Financial Assistant.
    Enforces strict tenant isolation via authenticated session context.
    """
    return await chat_with_financial_assistant(
        db=db,
        user_id=current_user.id,
        default_currency=current_user.default_currency,
        message=req.message,
        conversation_id=req.conversation_id,
    )

