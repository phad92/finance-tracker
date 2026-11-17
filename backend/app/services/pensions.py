import uuid
from datetime import date
from typing import List, Optional
from sqlalchemy import desc, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pensions import (
    PensionAccount,
    PensionContribution,
    PensionForecastAssumptions,
    PensionScheme,
    PensionValuation,
    SSNITBenefitEstimate,
    SSNITMembership,
)
from app.schemas.pensions import (
    PensionForecastPoint,
    PensionForecastRequest,
    PensionForecastResponse,
    PensionSensitivityScenario,
    PensionSummaryResponse,
)
from app.services.currency import ExchangeRateUnavailableError, convert_amount


PAYROLL_FRAMEWORK_NOTE = (
    "Ghana statutory framework (Act 766): 18.5% mandatory total on pensionable salary — "
    "13.5% Tier 1 (11% SSNIT pension + 2.5% NHIS health component, which is not a retirement balance) "
    "and 5% Tier 2 occupational funded account. Tier 3 is voluntary."
)


def mask_sensitive_ref(raw: Optional[str]) -> Optional[str]:
    """Mask sensitive pension/SSNIT identifiers for UI display, logs, and AI prompts."""
    if not raw:
        return None
    cleaned = raw.strip()
    if len(cleaned) <= 4:
        return "*" * len(cleaned)
    return ("*" * (len(cleaned) - 4)) + cleaned[-4:]


async def seed_default_pension_schemes(db: AsyncSession) -> None:
    """Seed baseline NPRA-aligned Ghana pension scheme categories if empty."""
    existing = (await db.execute(select(PensionScheme).limit(1))).first()
    if existing is not None:
        return

    defaults = [
        PensionScheme(
            name="SSNIT Basic National Social Security Scheme",
            tier="TIER_1",
            scheme_type="SSNIT",
            trustee_provider="SSNIT",
            source_url="https://www.ssnit.org.gh/faqs/",
            is_custom=False,
            is_active=True,
        ),
        PensionScheme(
            name="Occupational Pension Scheme (Master Trust Tier 2)",
            tier="TIER_2",
            scheme_type="MASTER_TRUST_OCCUPATIONAL",
            trustee_provider="NPRA-Licensed Corporate Trustee",
            source_url="https://snapshot.npra.gov.gh/news-and-events/public-notices/approved-schemes-2025/",
            is_custom=False,
            is_active=True,
        ),
        PensionScheme(
            name="Provident Fund Scheme (Master Trust Tier 3)",
            tier="TIER_3",
            scheme_type="MASTER_TRUST_PROVIDENT",
            trustee_provider="NPRA-Licensed Corporate Trustee",
            source_url="https://snapshot.npra.gov.gh/news-and-events/public-notices/approved-schemes-2025/",
            is_custom=False,
            is_active=True,
        ),
        PensionScheme(
            name="Personal Pension Scheme (Individual Tier 3)",
            tier="TIER_3",
            scheme_type="PERSONAL_PENSION",
            trustee_provider="NPRA-Licensed Corporate Trustee",
            source_url="https://snapshot.npra.gov.gh/news-and-events/public-notices/approved-schemes-2025/",
            is_custom=False,
            is_active=True,
        ),
    ]
    db.add_all(defaults)
    await db.commit()


async def get_funded_pension_total(
    db: AsyncSession,
    user_id: uuid.UUID,
    reporting_currency: str = "GHS",
) -> float:
    """
    Compute total funded Tier 2 + Tier 3 statement balances in reporting_currency.
    Strictly excludes SSNIT Tier 1 (defined-benefit entitlement, not a funded account).
    """
    stmt = (
        select(PensionAccount)
        .where(
            PensionAccount.user_id == user_id,
            PensionAccount.status == "ACTIVE",
            PensionAccount.tier.in_(["TIER_2", "TIER_3"]),
        )
        .options(selectinload(PensionAccount.valuations))
    )
    accounts = (await db.execute(stmt)).scalars().all()
    total = 0.0
    for acc in accounts:
        if not acc.valuations:
            continue
        latest_val = float(acc.valuations[0].statement_balance)
        converted, _ = await convert_amount(
            db=db,
            amount=latest_val,
            from_currency=acc.currency,
            to_currency=reporting_currency,
        )
        total += converted
    return round(total, 2)


async def calculate_pension_summary(
    db: AsyncSession,
    user_id: uuid.UUID,
    reporting_currency: str = "GHS",
) -> PensionSummaryResponse:
    """Aggregate Tier 2/3 funded balances, Tier 2 reconciliation totals, and SSNIT Tier 1 status."""
    acc_stmt = (
        select(PensionAccount)
        .where(PensionAccount.user_id == user_id, PensionAccount.status == "ACTIVE")
        .options(
            selectinload(PensionAccount.valuations),
            selectinload(PensionAccount.contributions),
        )
    )
    accounts = (await db.execute(acc_stmt)).scalars().all()

    tier2_bal = 0.0
    tier3_bal = 0.0
    tier2_expected = 0.0
    tier2_actual = 0.0
    latest_stmt_date: Optional[date] = None
    fx_warnings: list[str] = []

    for acc in accounts:
        if acc.tier in {"TIER_2", "TIER_3"} and acc.valuations:
            latest = acc.valuations[0]
            if latest_stmt_date is None or latest.valuation_date > latest_stmt_date:
                latest_stmt_date = latest.valuation_date
            raw_bal = float(latest.statement_balance)
            try:
                conv_bal, _ = await convert_amount(
                    db=db,
                    amount=raw_bal,
                    from_currency=acc.currency,
                    to_currency=reporting_currency,
                )
                if acc.tier == "TIER_2":
                    tier2_bal += conv_bal
                else:
                    tier3_bal += conv_bal
            except ExchangeRateUnavailableError as exc:
                fx_warnings.append(str(exc))

        if acc.tier == "TIER_2":
            for c in acc.contributions:
                if c.expected_amount is not None:
                    tier2_expected += float(c.expected_amount)
                tier2_actual += float(c.actual_credited_amount)

    ssnit = (
        await db.execute(select(SSNITMembership).where(SSNITMembership.user_id == user_id))
    ).scalar_one_or_none()

    return PensionSummaryResponse(
        reporting_currency=reporting_currency,
        funded_tier2_balance=round(tier2_bal, 2),
        funded_tier3_balance=round(tier3_bal, 2),
        total_funded_retirement_balance=round(tier2_bal + tier3_bal, 2),
        tier2_expected_contributions=round(tier2_expected, 2),
        tier2_actual_credited=round(tier2_actual, 2),
        tier2_reconciliation_variance=round(tier2_actual - tier2_expected, 2),
        ssnit_contribution_months=ssnit.total_contribution_months if ssnit else 0,
        ssnit_last_statement_date=ssnit.last_statement_date if ssnit else None,
        last_statement_date=latest_stmt_date,
        active_accounts_count=len(accounts),
        payroll_framework_note=PAYROLL_FRAMEWORK_NOTE,
        fx_warning="; ".join(fx_warnings) if fx_warnings else None,
    )


PENSION_FORECAST_DISCLAIMER = (
    "Projections and SSNIT estimates are planning illustrations, not guaranteed benefits, "
    "official SSNIT benefit determinations, tax advice, or regulated investment advice."
)


def compute_pension_projection(
    req: PensionForecastRequest,
    starting_tier2: float,
    starting_tier3: float,
    reporting_currency: str = "GHS",
    ssnit_monthly_estimate: Optional[float] = None,
    forecast_id: Optional[uuid.UUID] = None,
) -> PensionForecastResponse:
    """
    Project Tier 2 & Tier 3 funded balances from current_age to retirement_age,
    computing nominal and inflation-adjusted values, contributions vs. growth, and sensitivity.
    """
    years = max(0, req.retirement_age - req.current_age)
    net_annual_return = (req.expected_return_pct - req.annual_fee_pct) / 100.0
    inflation = req.inflation_pct / 100.0
    salary_growth = req.salary_growth_pct / 100.0
    tier2_rate = req.tier2_rate_pct / 100.0
    match_mult = 1.0 + (req.employer_match_pct / 100.0)

    def _simulate(ret_rate: float, sim_years: int) -> tuple[float, float, float, List[PensionForecastPoint]]:
        t2 = float(starting_tier2)
        t3 = float(starting_tier3)
        cum_contrib = float(starting_tier2 + starting_tier3)
        salary = float(req.pensionable_salary)
        base_year = date.today().year
        pts: List[PensionForecastPoint] = []

        for y in range(sim_years + 1):
            total_nom = t2 + t3
            deflator = (1.0 + inflation) ** y if inflation > -0.99 else 1.0
            total_real = total_nom / deflator
            pts.append(
                PensionForecastPoint(
                    age=req.current_age + y,
                    year=base_year + y,
                    tier2_nominal=round(t2, 2),
                    tier3_nominal=round(t3, 2),
                    total_funded_nominal=round(total_nom, 2),
                    total_funded_real=round(total_real, 2),
                    cumulative_contributions=round(cum_contrib, 2),
                    cumulative_growth=round(total_nom - cum_contrib, 2),
                )
            )
            if y < sim_years:
                annual_t2_contrib = salary * 12.0 * tier2_rate
                annual_t3_contrib = req.tier3_monthly * 12.0 * match_mult
                t2 = (t2 + annual_t2_contrib) * (1.0 + ret_rate)
                t3 = (t3 + annual_t3_contrib) * (1.0 + ret_rate)
                cum_contrib += annual_t2_contrib + annual_t3_contrib
                salary *= (1.0 + salary_growth)

        return t2, t3, cum_contrib, pts

    t2_end, t3_end, total_contrib, trajectory = _simulate(net_annual_return, years)
    funded_nom = t2_end + t3_end
    deflator_end = (1.0 + inflation) ** years if inflation > -0.99 else 1.0
    funded_real = funded_nom / deflator_end
    growth_nom = funded_nom - total_contrib

    drawdown_months = max(1, req.drawdown_years * 12)
    monthly_funded_nom = funded_nom / drawdown_months
    monthly_funded_real = funded_real / drawdown_months
    ssnit_val = float(ssnit_monthly_estimate) if (req.include_ssnit_estimate and ssnit_monthly_estimate is not None) else None
    combined_monthly_nom = monthly_funded_nom + (ssnit_val or 0.0)

    # Sensitivity scenarios
    sensitivity: List[PensionSensitivityScenario] = []
    for label, r_delta, y_delta in [
        ("Conservative (-2% Return)", -0.02, 0),
        ("Base Case", 0.0, 0),
        ("Optimistic (+2% Return)", 0.02, 0),
        ("Retire +2 Years Later", 0.0, 2),
    ]:
        s_years = max(0, years + y_delta)
        s_t2, s_t3, _, _ = _simulate(net_annual_return + r_delta, s_years)
        s_nom = s_t2 + s_t3
        s_real = s_nom / ((1.0 + inflation) ** s_years if inflation > -0.99 else 1.0)
        sensitivity.append(
            PensionSensitivityScenario(
                scenario_name=label,
                projected_funded_nominal=round(s_nom, 2),
                projected_funded_real=round(s_real, 2),
                estimated_monthly_funded_income_real=round(s_real / drawdown_months, 2),
            )
        )

    return PensionForecastResponse(
        forecast_id=forecast_id,
        reporting_currency=reporting_currency,
        starting_tier2_balance=round(starting_tier2, 2),
        starting_tier3_balance=round(starting_tier3, 2),
        projected_tier2_nominal=round(t2_end, 2),
        projected_tier3_nominal=round(t3_end, 2),
        projected_funded_nominal=round(funded_nom, 2),
        projected_funded_real=round(funded_real, 2),
        total_contributions_projected=round(total_contrib, 2),
        total_investment_growth_nominal=round(growth_nom, 2),
        estimated_monthly_funded_income_nominal=round(monthly_funded_nom, 2),
        estimated_monthly_funded_income_real=round(monthly_funded_real, 2),
        ssnit_estimated_monthly_pension=round(ssnit_val, 2) if ssnit_val is not None else None,
        combined_estimated_monthly_income_nominal=round(combined_monthly_nom, 2),
        trajectory=trajectory,
        sensitivity=sensitivity,
        model_version="gh-pension-proj-v1",
        disclaimer=PENSION_FORECAST_DISCLAIMER,
    )
