# Finance Tracker --- Code Review Findings & Pension Planning Scope

**Repository:** https://github.com/phad92/finance-tracker\
**Review basis:** Selected source files on `master`, product
requirements v1.3 (updated 17 November 2026), and official Ghana pension
sources reviewed on 17 November 2026.

> **Scope limitation:** This is a targeted source inspection, not a full
> security audit or an executed test run. Findings must be confirmed
> against the current branch and runtime before production changes.

## 1. Executive summary

The repository has a sound starting structure: FastAPI services and
APIs, SQLAlchemy models, Vue frontend, PostgreSQL migrations, Docker
deployment assets, tests and operational scripts.

The highest-priority concern is financial correctness. Some analytics
can look authoritative while relying on simplified or assumed
calculations. Make the ledger, FX conversion, performance calculations
and risk outputs dependable and auditable before expanding features.

A second product gap is retirement planning. The v1.3 plan includes
financial goals and investment portfolios, but does not explicitly model
Ghana's three-tier pension system: SSNIT Tier 1, mandatory occupational
Tier 2 and voluntary Tier 3. Add a distinct **Retirement & Pensions**
module.

## 2. Itemized code-review observations

Severity: **Critical** = can materially misstate finances or create
serious security/recovery risk; **High** = significant
reliability/privacy concern; **Medium** = important improvement.

### FIN-01 --- TWR is a relabelled total-return percentage

**Severity:** Critical \| **File:**
`backend/app/services/performance.py`

The implementation assigns `twr_cumulative_pct` from `total_return_pct`.
It does not chain sub-period returns around external cash flows.

**Why it matters:** TWR is designed to neutralize the effect of the
timing and size of investor cash flows. It is not interchangeable with
gain divided by cost basis or with XIRR.

**Action:** - Calculate portfolio valuations immediately before/after
external cash flows, or use a documented valuation frequency. -
Calculate each sub-period return and geometrically link them. - Define
external flows (deposits/withdrawals) versus internal events (trades and
reinvested dividends). - Disclose valuation frequency and missing price
data. - Until corrected, mark TWR unavailable rather than showing total
return under that label.

**Acceptance tests:** Different deposit timing should not change TWR for
otherwise identical investment performance; deposits and withdrawals
must not themselves create returns; compare against independently
calculated fixtures.

### FIN-02 --- FX service silently returns hardcoded or 1.0 fallback rates

**Severity:** Critical \| **File:** `backend/app/services/currency.py`

When no stored rate exists, the service returns hardcoded GHS pairs; for
unsupported pairs it returns `1.0`.

**Why it matters:** Unsupported or stale FX can silently distort net
worth, portfolio values, returns and risk. A 1.0 fallback is an
assumption, not a safe error state.

**Action:** - Return a typed result containing rate, source, effective
date, retrieval timestamp and quality/freshness. - If no valid rate
exists, return an explicit unavailable result/domain error. - If manual
fallback is allowed, require user approval and label it `MANUAL` or
`ESTIMATED`. - Enforce configurable staleness limits and show
warnings. - Preserve transaction-time rates for historical records; use
latest approved rates only for current valuations.

**Acceptance tests:** Unsupported pairs never return 1.0; stale rates
are flagged; inverse rates must be positive; every conversion is
traceable.

### FIN-03 --- FX ingestion gives synthetic GHS rates external-source provenance

**Severity:** Critical \| **File:**
`backend/app/services/market_data.py`

The inspected sync function fetches USD/EUR/GBP relationships from
Frankfurter, applies a hardcoded USD/GHS anchor and labels the combined
values `Frankfurter+BoG` or `BoG_Reference`.

**Why it matters:** These are not necessarily observed Bank of Ghana
rates. Provenance labels can imply authority the calculation does not
have.

**Action:** Ingest actual published BoG rates where available. Label
calculated cross-rates `CALCULATED_CROSS_RATE`, retaining component
sources/dates. Never describe a hardcoded anchor as live or official.
Distinguish official, provider-sourced, calculated, manual and stale
rates.

### FIN-04 --- XIRR solver coverage is narrow

**Severity:** High \| **File:** `backend/app/services/performance.py`

The routine uses Brent's method over a fixed interval, then a Newton
fallback. The visible tests cover a simple one-year 10% case and
all-negative cash flows.

**Action:** Validate and consolidate dated flows; document sign
convention and terminal valuation; detect solver failure or
multiple-root ambiguity; do not convert failure to zero. Add tests for
irregular dates, leap years, multiple deposits/withdrawals, zero
terminal value and non-conventional cash flows.

### FIN-05 --- Performance cash flows need reconciliation against accounting events

**Severity:** High \| **File:** `backend/app/services/performance.py`

The implementation uses BUY/SELL transactions, non-reinvested dividends
and current market value as a terminal inflow. Correctness depends on
how fees, taxes, realized gains and reinvested dividends are recorded
elsewhere.

**Action:** Define cash-flow rules for every event; prevent reinvested
dividends from being counted as external cash flows if represented by
internal purchases; avoid double-counting sold positions and terminal
value; consistently treat fees/taxes; reconcile total return, realized
P&L, unrealized P&L and dividends using worked examples.

### FIN-06 --- Risk calculations are approximations

**Severity:** High \| **File:** `backend/app/services/risk.py`

The observed-history path combines each asset's historical returns using
current portfolio weights. It does not reconstruct historical
weights/cash flows. The inspected code also uses raw instrument close
returns and does not visibly convert each series into reporting currency
before aggregation.

**Action:** Build a synchronized reporting-currency return series
including FX returns; label constant-mix approximations as such; align
by actual trading dates; account for missing/stale prices; disclose
assumptions and limitations.

### FIN-07 --- Parametric risk assumptions are hardcoded

**Severity:** High \| **File:** `backend/app/services/risk.py`

Expected returns, volatility and risk-free rates are fixed by reporting
currency; Sortino and drawdown estimates use simple multipliers.

**Action:** Move assumptions into versioned configuration; store source,
effective date, asset class and currency; separate estimates from
observed statistics; display assumptions and add sensitivity analysis.

### SEC-01 --- Access and refresh tokens are stored in localStorage

**Severity:** High \| **Files:** `frontend/src/stores/auth.ts`,
`frontend/src/services/api.ts`

Both tokens are stored in localStorage and the access token is read for
API requests. JavaScript running on the page can access localStorage, so
XSS can expose tokens.

**Action:** Prefer a `Secure`, `HttpOnly`, `SameSite` refresh cookie
with CSRF protection; keep access tokens short-lived/in memory;
implement refresh rotation and server-side revocation; review CSP,
output escaping and dependencies. Logout should invalidate the
server-side session.

### SEC-02 --- Tests do not prove isolation across the whole API

**Severity:** High \| **File:**
`backend/tests/test_security_and_isolation.py`

The inspected test exercises selected risk/options ownership cases, not
every user-owned endpoint.

**Action:** Build two-user integration fixtures; test
list/read/create/update/delete/import/export/report endpoints and nested
resources; test background jobs and AI tool calls; consider PostgreSQL
RLS as defence in depth; test admin paths separately.

### SEC-03 --- Production security configuration should fail closed

**Severity:** Medium--High \| **File:** `backend/app/config.py`

Settings include development defaults and a production validation
method. Verify validation runs before requests are served in every
production startup path.

**Action:** Fail startup when production secrets/origins are weak or
missing; validate CORS; disable or protect interactive API docs in
production; add a production-startup test.

### OPS-01 --- Restore verification checks table count, not financial integrity

**Severity:** High \| **Files:** `scripts/restore_postgres.sh`,
`_docs/deployment_and_operations.md`

The runbook describes a sandbox restore that verifies restored table
count and cleans up the temporary database.

**Action:** Verify critical foreign keys/constraints, selected row
counts/checksums and sample queries for users, accounts, transactions,
holdings, prices and (once implemented) pension records. Record backup
timestamp, database version, restore duration and verification outcome.
Perform periodic full recovery drills.

### DATA-01 --- Market-data freshness and provenance must be enforced end-to-end

**Severity:** High \| **Files:** `backend/app/services/market_data.py`,
market models and frontend market views

The product plan requires source, observation date, retrieval date and
quality status. Verify each provider adapter records these consistently
and that dependent calculations expose freshness.

**Action:** Add provider health/ingestion logs; distinguish observed,
calculated, manual, estimated and stale values; prevent stale prices
appearing current; show last successful sync and failures; document
licensing/delay/redistribution terms.

### DATA-02 --- Instrument master and currency metadata need validation

**Severity:** Medium \| **File:** `backend/app/services/market_data.py`

Seed data is useful, but exchange, currency and symbol metadata must be
verified. Support symbol changes, delistings and multiple listings;
retain source/verification status; test duplicate symbols across
exchanges.

## 3. Ghana pension and retirement-planning gap

### 3.1 What v1.3 already covers --- and what is missing

The v1.3 plan already supports cash/bank/MoMo, listed shares, ETFs,
mutual funds, money-market funds, T-bills, bonds, financial goals
(including retirement) and general contribution/inflation assumptions.

It does **not** explicitly specify: - SSNIT Tier 1 membership and
contribution history. - Mandatory Tier 2 occupational pension
balances. - Voluntary Tier 3 personal pension/provident fund accounts. -
Employer/employee contribution breakdowns. - Pension trustee/provider
and scheme metadata. - Pension benefit estimates and pension-specific
assumptions. - Consolidated retirement-income projections.

Add a dedicated **Retirement & Pensions** module.

### 3.2 Ghana's three-tier structure

  ------------------------------------------------------------------------------------
  Tier              Type              Main characteristics   Treatment in the app
  ----------------- ----------------- ---------------------- -------------------------
  Tier 1            SSNIT basic       Mandatory for covered  Track
                    national social   formal-sector workers; contribution/employment
                    security          defined-benefit        history and estimate
                                      monthly pension and    monthly benefit
                                      related benefits       separately from funded
                                                             account balances

  Tier 2            Occupational      Mandatory, privately   Track member/employer
                    pension           managed, fully funded  contributions,
                                      defined-contribution   scheme/trustee, returns
                                      account; lump-sum      and statement balance
                                      benefit                

  Tier 3            Voluntary         Voluntary, privately   Track contributions,
                    provident         managed, fully funded; employer top-ups, fees,
                    fund/personal     employer-sponsored,    returns, withdrawals and
                    pension           group or individual    balance
                                      arrangements           
  ------------------------------------------------------------------------------------

**Contribution framework to model, subject to current payroll-rule
verification:** - Commonly stated statutory total: 18.5% of
pensionable/basic salary. - Tier 1 allocation: 13.5% in total, commonly
described as 11% for SSNIT pension and 2.5% for the health insurance
component. - Tier 2 allocation: 5%. - Tier 3: voluntary and separate
from the mandatory 18.5%.

Do not treat all 13.5% as an individual's SSNIT retirement account
balance. The 2.5% health component is not a Tier 1 pension account
balance.

Make rates, pensionable salary rules, caps, effective dates and
exceptions configurable. Allow actual payslip/administrator statement
amounts to be entered when payroll details are unavailable. Do not
hardcode rates as permanently valid.

### 3.3 Scheme types to support

NPRA publishes approved lists covering: - Employer-sponsored
occupational pension schemes. - Employer-sponsored provident fund
schemes. - Master trust occupational pension schemes. - Master trust
provident fund schemes. - Group personal pension schemes. - Personal
pension schemes.

The scheme catalogue should be extensible. Let users add a scheme
manually if it is not in the catalogue. Names in NPRA notices are
examples, not endorsements or guarantees of current availability. Verify
any scheme against the latest NPRA list before selection.

### 3.4 Proposed capabilities

#### A. Pension overview

Display: - Total funded retirement assets (Tier 2 + Tier 3 and other
included retirement investments). - SSNIT
membership/contribution-history summary. - Employee and employer
contributions. - Voluntary contributions. - Returns and fees where
statements provide data. - Last statement date and data freshness. -
Estimated retirement income at selected ages. - Nominal and
today's-money projections.

Show estimated Tier 1 monthly pension separately from funded Tier 2/Tier
3 balances. Do not treat an estimated future SSNIT pension as a liquid
asset in current net worth.

#### B. Tier 1 --- SSNIT profile and benefit estimate

Capture: - SSNIT member reference (sensitive; securely stored). -
Membership start date. - Employment periods and employers. - Pensionable
salary history where available. - Contribution months/years and actual
statement history. - Gaps or missing months.

Provide manual statement entry/import, contribution timeline,
missing-month review, eligibility/service summary and a monthly benefit
estimate with methodology, assumptions and disclaimer.

**Do not invent the statutory SSNIT pension formula.** Implement it only
after verifying current official SSNIT/NPRA rules, including salary
revaluation and qualifying contribution history. Until then, store
statement-derived or user-entered estimates with clear labels.

#### C. Tier 2 --- occupational pension account

Capture employer, scheme/trustee, member reference, membership dates,
pay-period contributions (employee/employer), actual credited amount,
statement balance, returns/fees and transfers/corrections.

Support monthly reconciliation: **expected contribution vs actual amount
credited**. Expected amounts must be configurable and never replace
actual trustee records.

#### D. Tier 3 --- voluntary pension accounts

Support personal pension, employer-sponsored provident fund, group
personal pension, master trust provident fund and other NPRA-registered
categories.

Capture regular/one-off contributions, member/employer amounts,
matching, frequency/escalation, fund option where reported, fees,
withdrawals/transfers, statement balance and valuation date. Store
scheme-specific tax, vesting and withdrawal rules; do not assume every
Tier 3 scheme is identical.

#### E. Retirement calculator

Allow assumptions for: - Current age and retirement age. - Salary growth
and pensionable salary. - Tier 2 contribution rate and employer/employee
split. - Tier 3 contributions and employer matching. - Contribution
increases. - Investment return scenarios. - Inflation, fees and
charges. - Retirement income horizon/withdrawal assumptions. - Other
retirement assets and income streams.

Outputs: - Projected Tier 2 and Tier 3 balances. - Combined funded
pension balance. - SSNIT estimated monthly pension (separate). -
Estimated total monthly retirement income. - Nominal and
inflation-adjusted values. - Contributions versus investment-growth
breakdown. - Sensitivity to retirement age, contribution, salary growth
and returns.

All projections must be labelled estimates, not guaranteed benefits.

### 3.5 Proposed data model

  -----------------------------------------------------------------------
  Entity                              Purpose / key fields
  ----------------------------------- -----------------------------------
  `pension_schemes`                   Scheme name, tier, scheme type,
                                      trustee/provider, NPRA registration
                                      status/reference, source URL,
                                      effective dates

  `pension_accounts`                  User, scheme, tier, member
                                      reference, employer, currency,
                                      membership dates, status

  `pension_contributions`             Account, pay period/date, member
                                      amount, employer amount, other
                                      amount, expected/actual credited
                                      amount, source

  `pension_valuations`                Account, valuation date, statement
                                      balance, units/unit value where
                                      available, source document

  `pension_transactions`              Contributions, fees, returns,
                                      withdrawals, transfers, corrections
                                      and reversals

  `pension_employment_periods`        Employer, start/end dates,
                                      pensionable salary history

  `ssnit_membership`                  User, membership dates,
                                      contribution history summary,
                                      protected statement references

  `ssnit_benefit_estimates`           Estimate date, retirement age,
                                      service/salary assumptions,
                                      methodology version, monthly
                                      estimate, data completeness

  `pension_forecast_assumptions`      Return, inflation, salary growth,
                                      contribution rates, fees,
                                      retirement age and model version
  -----------------------------------------------------------------------

Keep statement facts separate from calculated estimates. A statement
balance is observed/manual source data; a projected balance is a model
output.

### 3.6 Suggested API surface

-   `GET /api/v1/pensions/summary`
-   `GET /api/v1/pensions/accounts`
-   `POST /api/v1/pensions/accounts`
-   `GET /api/v1/pensions/accounts/{id}`
-   `POST /api/v1/pensions/accounts/{id}/contributions`
-   `GET /api/v1/pensions/accounts/{id}/contributions`
-   `POST /api/v1/pensions/accounts/{id}/valuations`
-   `GET /api/v1/pensions/schemes`
-   `POST /api/v1/pensions/ssnit/profile`
-   `GET /api/v1/pensions/ssnit/history`
-   `POST /api/v1/pensions/ssnit/estimate`
-   `POST /api/v1/pensions/forecast`
-   `GET /api/v1/pensions/forecast/{id}`

All routes must enforce ownership. Sensitive identifiers/documents must
be excluded from ordinary logs and AI prompts.

### 3.7 Frontend navigation

Add **Retirement & Pensions** with: 1. Pension Overview 2. SSNIT
(Tier 1) 3. Occupational Pension (Tier 2) 4. Personal & Provident Funds
(Tier 3) 5. Retirement Calculator 6. Statements & Reconciliation

The main dashboard can show a compact retirement summary, while detailed
accounts and estimates remain in the dedicated module.

## 4. Prioritized engineering backlog

  -----------------------------------------------------------------------------------------
  ID                Priority          Work item                 Completion condition
  ----------------- ----------------- ------------------------- ---------------------------
  FIN-01            P0                Implement genuine TWR     Independent cash-flow
                                                                timing fixtures pass

  FIN-02            P0                Remove silent FX          Missing/stale FX explicit
                                      fallbacks                 and traceable

  FIN-03            P0                Correct FX provenance     Actual vs calculated source
                                                                clearly labelled

  FIN-05            P0                Reconcile                 Buy/sell/dividend/fee/tax
                                      ledger/performance cash   examples reconcile
                                      flows                     

  FIN-04            P1                Expand XIRR edge handling Irregular/ambiguous
                                                                cash-flow tests pass

  FIN-06            P1                Rebuild                   FX-aware aligned series and
                                      reporting-currency        methodology labels
                                      portfolio returns         

  FIN-07            P1                Version risk assumptions  Assumptions dated, sourced
                                                                and visible

  SEC-01            P1                Harden token lifecycle    HttpOnly refresh cookie,
                                                                rotation and revocation
                                                                tested

  SEC-02            P1                Full API tenant-isolation Two-user tests cover all
                                      suite                     user-owned endpoints

  OPS-01            P1                Stronger restore drill    Financial
                                                                records/constraints
                                                                verified

  DATA-01           P1                Enforce market            Stale/missing provider
                                      freshness/provenance      states visible

  PENS-01           P1                Add pension model and     Tier 1/2/3 accounts stored
                                      scheme catalogue          separately

  PENS-02           P1                Add contribution          Expected vs actual credits
                                      tracking/reconciliation   visible

  PENS-03           P1                Add statement             Tier 2/3 valuations
                                      balances/history          auditable

  PENS-04           P2                Add retirement            Scenarios and inflation
                                      projections               supported

  PENS-05           P2                Add SSNIT benefit         Verified method or clearly
                                      estimate                  labelled statement estimate

  PENS-06           P2                Add retirement-income     Funded balances and
                                      dashboard                 estimated SSNIT income
                                                                separate
  -----------------------------------------------------------------------------------------

### Suggested sequencing

-   **Sprint A --- Financial truth:** FIN-01, FIN-02, FIN-03, FIN-05.
-   **Sprint B --- Reliability/security:** FIN-04, FIN-06, FIN-07,
    SEC-01, SEC-02, OPS-01, DATA-01.
-   **Sprint C --- Pension foundation:** PENS-01, PENS-02, PENS-03.
    Start with manual entry and statement imports; do not depend on
    direct SSNIT/trustee integrations.
-   **Sprint D --- Retirement planning:** PENS-04, PENS-05, PENS-06. Add
    modelling after balances and contribution history are dependable.

## 5. Product and data safeguards

1.  Never imply SSNIT/trustee connectivity unless an authorized
    integration exists.
2.  Manual entry and statement import are acceptable first-release
    paths.
3.  Distinguish observed, user-entered, provider-sourced and forecast
    values.
4.  Preserve statement date, provider, source reference and import
    timestamp.
5.  Treat pension IDs, salary histories and statements as sensitive
    financial data; apply least privilege, encryption, audit trails and
    redaction.
6.  Avoid double counting: pension balance is included once;
    contributions must not remain counted as cash after transfer.
7.  SSNIT is not a personal investment account: track
    service/contribution history and estimated monthly entitlement
    separately from funded account balances.
8.  Tier 3 tax, withdrawal, vesting and fee rules must be scheme- and
    rule-version-specific.
9.  Present this module as record-keeping and planning, not official
    benefit determination, tax advice or regulated investment advice.

## 6. Official Ghana pension references

Re-check current official notices and legislation before implementing
statutory calculations or maintaining a scheme catalogue.

-   **Ministry of Finance --- Pension scheme FAQ:** three-tier structure
    and stated contribution framework.\
    https://www.mofep.gov.gh/index.php/about-mof/faqs/
-   **SSNIT --- FAQs:** mandatory first and second tiers, voluntary
    third tier and contribution overview.\
    https://www.ssnit.org.gh/faqs/
-   **NPRA --- Approved Schemes 2025:** approved occupational, provident
    fund, master trust, group personal and personal pension scheme
    categories.\
    https://snapshot.npra.gov.gh/news-and-events/public-notices/approved-schemes-2025/
-   **National Pensions Act, 2008 (Act 766), as amended:** legal
    framework for the three-tier scheme.\
    https://ghalii.org/akn/gh/act/2008/766/eng%402023-03-08

## 7. Final recommendation

Pension support should not be a small extra field on the wealth
dashboard. It closes a meaningful gap in the product's promise to answer
where the user stands today and what retirement may look like.

For a Ghana-based user, a useful retirement picture combines personal
investments, cash and other assets with SSNIT contribution history, Tier
2 occupational pension and Tier 3 voluntary pension savings. Show funded
balances and estimated retirement income separately, with clear
differences in certainty and liquidity.

**Recommended next engineering milestone:** implement pension
account/contribution models with manual statement entry, alongside the
financial-correctness fixes. This delivers immediate value without
requiring expensive APIs or unverified integrations.
