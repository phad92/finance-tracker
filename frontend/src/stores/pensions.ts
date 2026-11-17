import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

export interface PensionSummary {
  reporting_currency: string
  funded_tier2_balance: number
  funded_tier3_balance: number
  total_funded_retirement_balance: number
  tier2_expected_contributions: number
  tier2_actual_credited: number
  tier2_reconciliation_variance: number
  ssnit_contribution_months: number
  ssnit_last_statement_date: string | null
  last_statement_date: string | null
  active_accounts_count: number
  payroll_framework_note: string
  fx_warning: string | null
}

export interface PensionScheme {
  id: string
  name: string
  tier: 'TIER_1' | 'TIER_2' | 'TIER_3'
  scheme_type: string
  trustee_provider?: string
  npra_reg_ref?: string
  is_custom: boolean
}

export interface PensionAccount {
  id: string
  scheme_id: string
  scheme_name?: string
  trustee_provider?: string
  tier: 'TIER_1' | 'TIER_2' | 'TIER_3'
  account_name: string
  member_reference_masked?: string
  employer_name?: string
  currency: string
  membership_start_date?: string
  status: string
  latest_balance: number
  last_valuation_date?: string
  notes?: string
}

export interface PensionContribution {
  id: string
  account_id: string
  pay_period: string
  contribution_date: string
  employee_amount: number
  employer_amount: number
  voluntary_amount: number
  expected_amount?: number
  actual_credited_amount: number
  reconciliation_variance?: number
  source: string
  notes?: string
}

export interface SSNITProfile {
  ssnit_number_masked?: string
  membership_start_date?: string
  total_contribution_months: number
  last_statement_date?: string
  notes?: string
}

export interface SSNITBenefitEstimate {
  id: string
  estimate_date: string
  target_retirement_age: number
  source_type: string
  methodology_version: string
  estimated_monthly_pension: number
  currency: string
  data_completeness_note?: string
  disclaimer: string
}

export interface PensionForecastResponse {
  forecast_id?: string
  reporting_currency: string
  starting_tier2_balance: number
  starting_tier3_balance: number
  projected_tier2_nominal: number
  projected_tier3_nominal: number
  projected_funded_nominal: number
  projected_funded_real: number
  total_contributions_projected: number
  total_investment_growth_nominal: number
  estimated_monthly_funded_income_nominal: number
  estimated_monthly_funded_income_real: number
  ssnit_estimated_monthly_pension?: number
  combined_estimated_monthly_income_nominal: number
  sensitivity: Array<{
    scenario_name: string
    projected_funded_nominal: number
    projected_funded_real: number
    estimated_monthly_funded_income_real: number
  }>
  model_version: string
  disclaimer: string
}

export const usePensionsStore = defineStore('pensions', () => {
  const summary = ref<PensionSummary | null>(null)
  const schemes = ref<PensionScheme[]>([])
  const accounts = ref<PensionAccount[]>([])
  const contributions = ref<PensionContribution[]>([])
  const ssnitProfile = ref<SSNITProfile | null>(null)
  const ssnitEstimate = ref<SSNITBenefitEstimate | null>(null)
  const forecast = ref<PensionForecastResponse | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchAll() {
    loading.value = true
    error.value = null
    try {
      const [sumRes, schRes, accRes, ssnitRes] = await Promise.all([
        api.get<PensionSummary>('/pensions/summary'),
        api.get<PensionScheme[]>('/pensions/schemes'),
        api.get<PensionAccount[]>('/pensions/accounts'),
        api.get<{ profile: SSNITProfile | null }>('/pensions/ssnit/history'),
      ])
      summary.value = sumRes.data
      schemes.value = schRes.data
      accounts.value = accRes.data
      ssnitProfile.value = ssnitRes.data.profile
      try {
        const estRes = await api.get<SSNITBenefitEstimate>('/pensions/ssnit/estimate')
        ssnitEstimate.value = estRes.data
      } catch {
        ssnitEstimate.value = null
      }
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to load pension data'
    } finally {
      loading.value = false
    }
  }

  async function fetchContributions(accountId: string) {
    const res = await api.get<PensionContribution[]>(`/pensions/accounts/${accountId}/contributions`)
    contributions.value = res.data
  }

  async function createAccount(payload: {
    scheme_id: string
    account_name: string
    member_reference?: string
    employer_name?: string
    currency?: string
  }) {
    await api.post('/pensions/accounts', payload)
    await fetchAll()
  }

  async function recordValuation(accountId: string, payload: { valuation_date: string; statement_balance: number; source_document_ref?: string }) {
    await api.post(`/pensions/accounts/${accountId}/valuations`, payload)
    await fetchAll()
  }

  async function recordContribution(
    accountId: string,
    payload: {
      pay_period: string
      contribution_date: string
      employee_amount: number
      employer_amount: number
      voluntary_amount: number
      expected_amount?: number
      actual_credited_amount: number
      source: string
    }
  ) {
    await api.post(`/pensions/accounts/${accountId}/contributions`, payload)
    await fetchContributions(accountId)
    await fetchAll()
  }

  async function saveSSNITProfile(payload: {
    ssnit_number?: string
    membership_start_date?: string
    total_contribution_months: number
    last_statement_date?: string
    notes?: string
  }) {
    await api.post('/pensions/ssnit/profile', payload)
    await fetchAll()
  }

  async function saveSSNITEstimate(payload: {
    target_retirement_age: number
    source_type: string
    estimated_monthly_pension: number
    currency?: string
    data_completeness_note?: string
  }) {
    const res = await api.post<SSNITBenefitEstimate>('/pensions/ssnit/estimate', payload)
    ssnitEstimate.value = res.data
  }

  async function runForecast(payload: {
    current_age: number
    retirement_age: number
    pensionable_salary: number
    salary_growth_pct: number
    tier2_rate_pct: number
    tier3_monthly: number
    employer_match_pct: number
    expected_return_pct: number
    inflation_pct: number
    annual_fee_pct: number
    drawdown_years: number
    include_ssnit_estimate: boolean
  }) {
    const res = await api.post<PensionForecastResponse>('/pensions/forecast', payload)
    forecast.value = res.data
  }

  return {
    summary,
    schemes,
    accounts,
    contributions,
    ssnitProfile,
    ssnitEstimate,
    forecast,
    loading,
    error,
    fetchAll,
    fetchContributions,
    createAccount,
    recordValuation,
    recordContribution,
    saveSSNITProfile,
    saveSSNITEstimate,
    runForecast,
  }
})
