import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.identity import User
from app.models.pensions import (
    PensionAccount,
    PensionContribution,
    PensionEmploymentPeriod,
    PensionForecastAssumptions,
    PensionScheme,
    PensionValuation,
    SSNITBenefitEstimate,
    SSNITMembership,
)
from app.schemas.pensions import (
    PensionAccountCreate,
    PensionAccountResponse,
    PensionContributionCreate,
    PensionContributionResponse,
    PensionEmploymentPeriodCreate,
    PensionEmploymentPeriodResponse,
    PensionForecastRequest,
    PensionForecastResponse,
    PensionSchemeCreate,
    PensionSchemeResponse,
    PensionSummaryResponse,
    PensionValuationCreate,
    PensionValuationResponse,
    SSNITBenefitEstimateCreate,
    SSNITBenefitEstimateResponse,
    SSNITHistoryResponse,
    SSNITProfileResponse,
    SSNITProfileUpsert,
)
from app.services.pensions import (
    PENSION_FORECAST_DISCLAIMER,
    calculate_pension_summary,
    compute_pension_projection,
    mask_sensitive_ref,
)

router = APIRouter(prefix="/pensions", tags=["Retirement & Pensions"])


def _to_account_response(acc: PensionAccount) -> PensionAccountResponse:
    latest_val = acc.valuations[0] if acc.valuations else None
    return PensionAccountResponse(
        id=acc.id,
        scheme_id=acc.scheme_id,
        scheme_name=acc.scheme.name if acc.scheme else None,
        trustee_provider=acc.scheme.trustee_provider if acc.scheme else None,
        tier=acc.tier,
        account_name=acc.account_name,
        member_reference_masked=mask_sensitive_ref(acc.member_reference),
        employer_name=acc.employer_name,
        currency=acc.currency,
        membership_start_date=acc.membership_start_date,
        status=acc.status,
        latest_balance=float(latest_val.statement_balance) if latest_val else 0.0,
        last_valuation_date=latest_val.valuation_date if latest_val else None,
        notes=acc.notes,
        created_at=acc.created_at,
    )


def _to_contribution_response(c: PensionContribution) -> PensionContributionResponse:
    expected = float(c.expected_amount) if c.expected_amount is not None else None
    actual = float(c.actual_credited_amount)
    variance = round(actual - expected, 4) if expected is not None else None
    return PensionContributionResponse(
        id=c.id,
        account_id=c.account_id,
        pay_period=c.pay_period,
        contribution_date=c.contribution_date,
        employee_amount=float(c.employee_amount),
        employer_amount=float(c.employer_amount),
        voluntary_amount=float(c.voluntary_amount),
        expected_amount=expected,
        actual_credited_amount=actual,
        reconciliation_variance=variance,
        source=c.source,
        notes=c.notes,
        created_at=c.created_at,
    )


@router.get("/summary", response_model=PensionSummaryResponse)
async def get_pensions_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PensionSummaryResponse:
    """Return consolidated Ghana Tier 1/2/3 pension summary in the user's reporting currency."""
    return await calculate_pension_summary(db, current_user.id, current_user.default_currency)


@router.get("/schemes", response_model=List[PensionSchemeResponse])
async def list_pension_schemes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[PensionScheme]:
    """List available NPRA-aligned and custom pension schemes."""
    stmt = select(PensionScheme).where(PensionScheme.is_active == True).order_by(PensionScheme.tier, PensionScheme.name)
    return list((await db.execute(stmt)).scalars().all())


@router.post("/schemes", response_model=PensionSchemeResponse, status_code=status.HTTP_201_CREATED)
async def create_custom_pension_scheme(
    scheme_in: PensionSchemeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PensionScheme:
    """Add a custom pension scheme to the extensible catalogue."""
    scheme = PensionScheme(
        name=scheme_in.name.strip(),
        tier=scheme_in.tier,
        scheme_type=scheme_in.scheme_type.strip().upper(),
        trustee_provider=scheme_in.trustee_provider,
        npra_reg_ref=scheme_in.npra_reg_ref,
        source_url=scheme_in.source_url,
        is_custom=True,
        is_active=True,
    )
    db.add(scheme)
    await db.flush()
    await db.refresh(scheme)
    return scheme


@router.get("/accounts", response_model=List[PensionAccountResponse])
async def list_pension_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[PensionAccountResponse]:
    """List all pension accounts owned by the authenticated user."""
    stmt = (
        select(PensionAccount)
        .where(PensionAccount.user_id == current_user.id)
        .options(selectinload(PensionAccount.scheme), selectinload(PensionAccount.valuations))
        .order_by(PensionAccount.tier, PensionAccount.account_name)
    )
    accounts = (await db.execute(stmt)).scalars().all()
    return [_to_account_response(acc) for acc in accounts]


@router.post("/accounts", response_model=PensionAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_pension_account(
    acc_in: PensionAccountCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PensionAccountResponse:
    """Create a new Tier 1, Tier 2, or Tier 3 pension account."""
    scheme = await db.get(PensionScheme, acc_in.scheme_id)
    if not scheme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pension scheme not found")

    acc = PensionAccount(
        user_id=current_user.id,
        scheme_id=scheme.id,
        tier=scheme.tier,
        account_name=acc_in.account_name.strip(),
        member_reference=acc_in.member_reference.strip() if acc_in.member_reference else None,
        employer_name=acc_in.employer_name,
        currency=acc_in.currency.upper().strip(),
        membership_start_date=acc_in.membership_start_date,
        status="ACTIVE",
        notes=acc_in.notes,
    )
    db.add(acc)
    await db.flush()
    await db.refresh(acc)
    acc.scheme = scheme
    acc.valuations = []
    return _to_account_response(acc)


@router.get("/accounts/{account_id}", response_model=PensionAccountResponse)
async def get_pension_account(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PensionAccountResponse:
    """Retrieve a single pension account owned by the authenticated user."""
    stmt = (
        select(PensionAccount)
        .where(PensionAccount.id == account_id, PensionAccount.user_id == current_user.id)
        .options(selectinload(PensionAccount.scheme), selectinload(PensionAccount.valuations))
    )
    acc = (await db.execute(stmt)).scalar_one_or_none()
    if not acc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pension account not found")
    return _to_account_response(acc)


@router.get("/accounts/{account_id}/contributions", response_model=List[PensionContributionResponse])
async def list_account_contributions(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[PensionContributionResponse]:
    """List contributions and expected-vs-actual reconciliation for a pension account."""
    acc = (
        await db.execute(
            select(PensionAccount).where(PensionAccount.id == account_id, PensionAccount.user_id == current_user.id)
        )
    ).scalar_one_or_none()
    if not acc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pension account not found")

    stmt = (
        select(PensionContribution)
        .where(PensionContribution.account_id == account_id, PensionContribution.user_id == current_user.id)
        .order_by(desc(PensionContribution.contribution_date))
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [_to_contribution_response(r) for r in rows]


@router.post("/accounts/{account_id}/contributions", response_model=PensionContributionResponse, status_code=status.HTTP_201_CREATED)
async def record_account_contribution(
    account_id: uuid.UUID,
    contrib_in: PensionContributionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PensionContributionResponse:
    """Record a pension contribution and optional expected-vs-actual reconciliation."""
    acc = (
        await db.execute(
            select(PensionAccount).where(PensionAccount.id == account_id, PensionAccount.user_id == current_user.id)
        )
    ).scalar_one_or_none()
    if not acc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pension account not found")

    row = PensionContribution(
        user_id=current_user.id,
        account_id=account_id,
        pay_period=contrib_in.pay_period.strip(),
        contribution_date=contrib_in.contribution_date,
        employee_amount=contrib_in.employee_amount,
        employer_amount=contrib_in.employer_amount,
        voluntary_amount=contrib_in.voluntary_amount,
        expected_amount=contrib_in.expected_amount,
        actual_credited_amount=contrib_in.actual_credited_amount,
        source=contrib_in.source.upper().strip(),
        notes=contrib_in.notes,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return _to_contribution_response(row)


@router.get("/accounts/{account_id}/valuations", response_model=List[PensionValuationResponse])
async def list_account_valuations(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[PensionValuation]:
    """List statement valuations for a pension account."""
    acc = (
        await db.execute(
            select(PensionAccount).where(PensionAccount.id == account_id, PensionAccount.user_id == current_user.id)
        )
    ).scalar_one_or_none()
    if not acc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pension account not found")

    stmt = (
        select(PensionValuation)
        .where(PensionValuation.account_id == account_id, PensionValuation.user_id == current_user.id)
        .order_by(desc(PensionValuation.valuation_date))
    )
    return list((await db.execute(stmt)).scalars().all())


@router.post("/accounts/{account_id}/valuations", response_model=PensionValuationResponse, status_code=status.HTTP_201_CREATED)
async def record_account_valuation(
    account_id: uuid.UUID,
    val_in: PensionValuationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PensionValuation:
    """Record an observed trustee statement valuation for a pension account."""
    acc = (
        await db.execute(
            select(PensionAccount).where(PensionAccount.id == account_id, PensionAccount.user_id == current_user.id)
        )
    ).scalar_one_or_none()
    if not acc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pension account not found")

    val = PensionValuation(
        user_id=current_user.id,
        account_id=account_id,
        valuation_date=val_in.valuation_date,
        statement_balance=val_in.statement_balance,
        units=val_in.units,
        unit_price=val_in.unit_price,
        source_document_ref=val_in.source_document_ref,
        notes=val_in.notes,
    )
    db.add(val)
    await db.flush()
    await db.refresh(val)
    return val


@router.post("/ssnit/profile", response_model=SSNITProfileResponse)
async def upsert_ssnit_profile(
    profile_in: SSNITProfileUpsert,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SSNITProfileResponse:
    """Create or update the user's SSNIT Tier 1 membership profile (masking SSNIT number)."""
    existing = (
        await db.execute(select(SSNITMembership).where(SSNITMembership.user_id == current_user.id))
    ).scalar_one_or_none()

    masked = mask_sensitive_ref(profile_in.ssnit_number)
    if existing:
        if masked is not None:
            existing.ssnit_number_masked = masked
        existing.membership_start_date = profile_in.membership_start_date
        existing.total_contribution_months = profile_in.total_contribution_months
        existing.last_statement_date = profile_in.last_statement_date
        existing.notes = profile_in.notes
        row = existing
    else:
        row = SSNITMembership(
            user_id=current_user.id,
            ssnit_number_masked=masked,
            membership_start_date=profile_in.membership_start_date,
            total_contribution_months=profile_in.total_contribution_months,
            last_statement_date=profile_in.last_statement_date,
            notes=profile_in.notes,
        )
        db.add(row)
    await db.flush()
    await db.refresh(row)

    return SSNITProfileResponse(
        ssnit_number_masked=row.ssnit_number_masked,
        membership_start_date=row.membership_start_date,
        total_contribution_months=row.total_contribution_months,
        last_statement_date=row.last_statement_date,
        notes=row.notes,
    )


@router.get("/ssnit/history", response_model=SSNITHistoryResponse)
async def get_ssnit_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SSNITHistoryResponse:
    """Retrieve SSNIT Tier 1 profile and employment history."""
    profile_row = (
        await db.execute(select(SSNITMembership).where(SSNITMembership.user_id == current_user.id))
    ).scalar_one_or_none()
    emp_rows = (
        await db.execute(
            select(PensionEmploymentPeriod)
            .where(PensionEmploymentPeriod.user_id == current_user.id)
            .order_by(desc(PensionEmploymentPeriod.start_date))
        )
    ).scalars().all()

    profile = (
        SSNITProfileResponse(
            ssnit_number_masked=profile_row.ssnit_number_masked,
            membership_start_date=profile_row.membership_start_date,
            total_contribution_months=profile_row.total_contribution_months,
            last_statement_date=profile_row.last_statement_date,
            notes=profile_row.notes,
        )
        if profile_row
        else None
    )
    return SSNITHistoryResponse(profile=profile, employment_periods=list(emp_rows))


@router.post("/ssnit/employment", response_model=PensionEmploymentPeriodResponse, status_code=status.HTTP_201_CREATED)
async def add_employment_period(
    emp_in: PensionEmploymentPeriodCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PensionEmploymentPeriod:
    """Record an employment period and optional pensionable salary for SSNIT/Tier 2 history."""
    emp = PensionEmploymentPeriod(
        user_id=current_user.id,
        employer_name=emp_in.employer_name.strip(),
        start_date=emp_in.start_date,
        end_date=emp_in.end_date,
        pensionable_salary=emp_in.pensionable_salary,
        currency=emp_in.currency.upper().strip(),
        notes=emp_in.notes,
    )
    db.add(emp)
    await db.flush()
    await db.refresh(emp)
    return emp


@router.post("/ssnit/estimate", response_model=SSNITBenefitEstimateResponse, status_code=status.HTTP_201_CREATED)
async def create_ssnit_estimate(
    est_in: SSNITBenefitEstimateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SSNITBenefitEstimateResponse:
    """Store a statement-derived or user-entered SSNIT Tier 1 monthly benefit estimate."""
    est = SSNITBenefitEstimate(
        user_id=current_user.id,
        estimate_date=est_in.estimate_date,
        target_retirement_age=est_in.target_retirement_age,
        source_type=est_in.source_type,
        methodology_version="manual-statement-v1",
        estimated_monthly_pension=est_in.estimated_monthly_pension,
        currency=est_in.currency.upper().strip(),
        data_completeness_note=est_in.data_completeness_note,
    )
    db.add(est)
    await db.flush()
    await db.refresh(est)
    return SSNITBenefitEstimateResponse(
        id=est.id,
        estimate_date=est.estimate_date,
        target_retirement_age=est.target_retirement_age,
        source_type=est.source_type,
        methodology_version=est.methodology_version,
        estimated_monthly_pension=float(est.estimated_monthly_pension),
        currency=est.currency,
        data_completeness_note=est.data_completeness_note,
        disclaimer=PENSION_FORECAST_DISCLAIMER,
    )


@router.get("/ssnit/estimate", response_model=SSNITBenefitEstimateResponse)
async def get_latest_ssnit_estimate(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SSNITBenefitEstimateResponse:
    """Retrieve the latest SSNIT Tier 1 monthly benefit estimate for the authenticated user."""
    stmt = (
        select(SSNITBenefitEstimate)
        .where(SSNITBenefitEstimate.user_id == current_user.id)
        .order_by(desc(SSNITBenefitEstimate.estimate_date), desc(SSNITBenefitEstimate.created_at))
        .limit(1)
    )
    est = (await db.execute(stmt)).scalar_one_or_none()
    if not est:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No SSNIT benefit estimate recorded")
    return SSNITBenefitEstimateResponse(
        id=est.id,
        estimate_date=est.estimate_date,
        target_retirement_age=est.target_retirement_age,
        source_type=est.source_type,
        methodology_version=est.methodology_version,
        estimated_monthly_pension=float(est.estimated_monthly_pension),
        currency=est.currency,
        data_completeness_note=est.data_completeness_note,
        disclaimer=PENSION_FORECAST_DISCLAIMER,
    )


@router.post("/forecast", response_model=PensionForecastResponse, status_code=status.HTTP_201_CREATED)
async def run_pension_forecast(
    req: PensionForecastRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PensionForecastResponse:
    """Run and persist a Ghana Tier 2/3 retirement projection with optional SSNIT estimate overlay."""
    if req.retirement_age < req.current_age:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="retirement_age must be greater than or equal to current_age",
        )

    summary = await calculate_pension_summary(db, current_user.id, current_user.default_currency)
    ssnit_est = (
        await db.execute(
            select(SSNITBenefitEstimate)
            .where(SSNITBenefitEstimate.user_id == current_user.id)
            .order_by(desc(SSNITBenefitEstimate.estimate_date), desc(SSNITBenefitEstimate.created_at))
            .limit(1)
        )
    ).scalar_one_or_none()

    ssnit_val = float(ssnit_est.estimated_monthly_pension) if ssnit_est else None
    result = compute_pension_projection(
        req=req,
        starting_tier2=summary.funded_tier2_balance,
        starting_tier3=summary.funded_tier3_balance,
        reporting_currency=current_user.default_currency,
        ssnit_monthly_estimate=ssnit_val,
    )

    saved = PensionForecastAssumptions(
        user_id=current_user.id,
        current_age=req.current_age,
        retirement_age=req.retirement_age,
        pensionable_salary=req.pensionable_salary,
        salary_growth_pct=req.salary_growth_pct,
        tier2_rate_pct=req.tier2_rate_pct,
        tier3_monthly=req.tier3_monthly,
        employer_match_pct=req.employer_match_pct,
        expected_return_pct=req.expected_return_pct,
        inflation_pct=req.inflation_pct,
        annual_fee_pct=req.annual_fee_pct,
        drawdown_years=req.drawdown_years,
        model_version=result.model_version,
        projected_funded_nominal=result.projected_funded_nominal,
        projected_funded_real=result.projected_funded_real,
    )
    db.add(saved)
    await db.flush()
    await db.refresh(saved)
    result.forecast_id = saved.id
    return result


@router.get("/forecast/{forecast_id}", response_model=PensionForecastResponse)
async def get_pension_forecast(
    forecast_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PensionForecastResponse:
    """Recompute and return a previously saved pension forecast owned by the user."""
    saved = (
        await db.execute(
            select(PensionForecastAssumptions).where(
                PensionForecastAssumptions.id == forecast_id,
                PensionForecastAssumptions.user_id == current_user.id,
            )
        )
    ).scalar_one_or_none()
    if not saved:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pension forecast not found")

    summary = await calculate_pension_summary(db, current_user.id, current_user.default_currency)
    ssnit_est = (
        await db.execute(
            select(SSNITBenefitEstimate)
            .where(SSNITBenefitEstimate.user_id == current_user.id)
            .order_by(desc(SSNITBenefitEstimate.estimate_date), desc(SSNITBenefitEstimate.created_at))
            .limit(1)
        )
    ).scalar_one_or_none()

    req = PensionForecastRequest(
        current_age=saved.current_age,
        retirement_age=saved.retirement_age,
        pensionable_salary=float(saved.pensionable_salary),
        salary_growth_pct=float(saved.salary_growth_pct),
        tier2_rate_pct=float(saved.tier2_rate_pct),
        tier3_monthly=float(saved.tier3_monthly),
        employer_match_pct=float(saved.employer_match_pct),
        expected_return_pct=float(saved.expected_return_pct),
        inflation_pct=float(saved.inflation_pct),
        annual_fee_pct=float(saved.annual_fee_pct),
        drawdown_years=saved.drawdown_years,
    )
    return compute_pension_projection(
        req=req,
        starting_tier2=summary.funded_tier2_balance,
        starting_tier3=summary.funded_tier3_balance,
        reporting_currency=current_user.default_currency,
        ssnit_monthly_estimate=float(ssnit_est.estimated_monthly_pension) if ssnit_est else None,
        forecast_id=saved.id,
    )
