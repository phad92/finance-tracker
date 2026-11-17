import uuid
from datetime import date
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient

from app.core.deps import get_current_user, get_db
from app.main import app
from app.models.identity import User
from app.schemas.pensions import PensionForecastRequest
from app.services.pensions import (
    calculate_pension_summary,
    compute_pension_projection,
    mask_sensitive_ref,
)


class _FakeResult:
    def __init__(self, items=None, scalar=None):
        self._items = items or []
        self._scalar = scalar

    def scalars(self):
        class _S:
            def __init__(self, items):
                self._items = items

            def all(self):
                return self._items

        return _S(self._items)

    def scalar_one_or_none(self):
        return self._scalar


class _PensionFakeSession:
    def __init__(self, accounts, ssnit):
        self._accounts = accounts
        self._ssnit = ssnit
        self._calls = 0

    async def execute(self, stmt):
        self._calls += 1
        if self._calls == 1:
            return _FakeResult(items=self._accounts)
        return _FakeResult(scalar=self._ssnit)


def test_mask_sensitive_ref():
    assert mask_sensitive_ref("GHA-123456789") == "*********6789"
    assert mask_sensitive_ref("1234") == "****"
    assert mask_sensitive_ref(None) is None


@pytest.mark.asyncio
async def test_pension_summary_separates_tier1_from_funded_tier2_tier3():
    """Verify Tier 2/3 funded balances aggregate separately from SSNIT Tier 1 and reconcile expected vs actual."""
    uid = uuid.uuid4()
    tier2_acc = SimpleNamespace(
        id=uuid.uuid4(),
        tier="TIER_2",
        currency="GHS",
        valuations=[SimpleNamespace(valuation_date=date(2026, 11, 1), statement_balance=45000.0)],
        contributions=[
            SimpleNamespace(expected_amount=500.0, actual_credited_amount=500.0),
            SimpleNamespace(expected_amount=500.0, actual_credited_amount=450.0),
        ],
    )
    tier3_acc = SimpleNamespace(
        id=uuid.uuid4(),
        tier="TIER_3",
        currency="GHS",
        valuations=[SimpleNamespace(valuation_date=date(2026, 11, 10), statement_balance=20000.0)],
        contributions=[],
    )
    ssnit = SimpleNamespace(total_contribution_months=84, last_statement_date=date(2026, 10, 31))

    summary = await calculate_pension_summary(_PensionFakeSession([tier2_acc, tier3_acc], ssnit), uid, "GHS")
    assert summary.funded_tier2_balance == pytest.approx(45000.0, abs=0.01)
    assert summary.funded_tier3_balance == pytest.approx(20000.0, abs=0.01)
    assert summary.total_funded_retirement_balance == pytest.approx(65000.0, abs=0.01)
    assert summary.tier2_expected_contributions == pytest.approx(1000.0, abs=0.01)
    assert summary.tier2_actual_credited == pytest.approx(950.0, abs=0.01)
    assert summary.tier2_reconciliation_variance == pytest.approx(-50.0, abs=0.01)
    assert summary.ssnit_contribution_months == 84
    assert summary.last_statement_date == date(2026, 11, 10)
    assert "2.5% NHIS" in summary.payroll_framework_note


def test_pensions_api_auth_and_tenant_isolation():
    """Verify pension endpoints require auth and return 404 on foreign/missing account IDs."""
    fake_user = User(
        id=uuid.uuid4(),
        email="pension@example.com",
        hashed_password="hashed",
        full_name="Pension User",
        default_currency="GHS",
        is_active=True,
        is_superuser=False,
    )

    class _EmptySession:
        async def execute(self, stmt):
            return _FakeResult(items=[], scalar=None)

        async def commit(self):
            return None

        async def rollback(self):
            return None

        async def close(self):
            return None

    async def _override_db():
        yield _EmptySession()

    async def _override_user():
        return fake_user

    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/api/v1/pensions/summary").status_code == 401

        app.dependency_overrides[get_db] = _override_db
        app.dependency_overrides[get_current_user] = _override_user
        try:
            foreign_id = uuid.uuid4()
            assert client.get(f"/api/v1/pensions/accounts/{foreign_id}").status_code == 404
            assert client.get(f"/api/v1/pensions/accounts/{foreign_id}/contributions").status_code == 404
            assert client.get(f"/api/v1/pensions/accounts/{foreign_id}/valuations").status_code == 404
            assert client.get(f"/api/v1/pensions/forecast/{foreign_id}").status_code == 404
            assert client.get("/api/v1/pensions/ssnit/estimate").status_code == 404
        finally:
            app.dependency_overrides.clear()


def test_retirement_projection_nominal_real_and_sensitivity():
    """Verify retirement forecast computes nominal > real under inflation, contributions+growth=ending, and sensitivity ordering."""
    req = PensionForecastRequest(
        current_age=35,
        retirement_age=60,
        pensionable_salary=10000.0,
        salary_growth_pct=5.0,
        tier2_rate_pct=5.0,
        tier3_monthly=500.0,
        employer_match_pct=0.0,
        expected_return_pct=12.0,
        inflation_pct=8.0,
        annual_fee_pct=1.5,
        drawdown_years=20,
        include_ssnit_estimate=True,
    )
    proj = compute_pension_projection(
        req=req,
        starting_tier2=40000.0,
        starting_tier3=10000.0,
        reporting_currency="GHS",
        ssnit_monthly_estimate=3500.0,
    )
    assert proj.projected_funded_nominal > proj.projected_funded_real
    assert proj.projected_funded_nominal == pytest.approx(
        proj.total_contributions_projected + proj.total_investment_growth_nominal, abs=0.1
    )
    assert proj.ssnit_estimated_monthly_pension == pytest.approx(3500.0, abs=0.01)
    assert proj.combined_estimated_monthly_income_nominal == pytest.approx(
        proj.estimated_monthly_funded_income_nominal + 3500.0, abs=0.05
    )
    # Conservative < Base < Optimistic
    cons, base, opt, _ = proj.sensitivity
    assert cons.projected_funded_nominal < base.projected_funded_nominal < opt.projected_funded_nominal
    assert "not guaranteed" in proj.disclaimer.lower()
