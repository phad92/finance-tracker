<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { Landmark, Plus, CheckCircle2, AlertTriangle, Shield } from 'lucide-vue-next'
import AppLayout from '@/components/layout/AppLayout.vue'
import { usePensionsStore } from '@/stores/pensions'

const store = usePensionsStore()
const activeTab = ref<'overview' | 'accounts' | 'reconciliation' | 'ssnit' | 'calculator'>('overview')
const selectedAccountId = ref<string>('')

const newAccount = ref({
  scheme_id: '',
  account_name: '',
  employer_name: '',
  member_reference: '',
  currency: 'GHS',
})

const newValuation = ref({
  account_id: '',
  valuation_date: new Date().toISOString().slice(0, 10),
  statement_balance: 0,
  source_document_ref: '',
})

const newContribution = ref({
  pay_period: new Date().toISOString().slice(0, 7),
  contribution_date: new Date().toISOString().slice(0, 10),
  employee_amount: 0,
  employer_amount: 0,
  voluntary_amount: 0,
  expected_amount: 0,
  actual_credited_amount: 0,
  source: 'PAYSLIP',
})

const ssnitForm = ref({
  ssnit_number: '',
  membership_start_date: '',
  total_contribution_months: 0,
  last_statement_date: '',
  notes: '',
})

const ssnitEstForm = ref({
  target_retirement_age: 60,
  source_type: 'STATEMENT_DERIVED',
  estimated_monthly_pension: 0,
  data_completeness_note: '',
})

const forecastForm = ref({
  current_age: 32,
  retirement_age: 60,
  pensionable_salary: 8000,
  salary_growth_pct: 5,
  tier2_rate_pct: 5,
  tier3_monthly: 500,
  employer_match_pct: 0,
  expected_return_pct: 12,
  inflation_pct: 8,
  annual_fee_pct: 1.5,
  drawdown_years: 20,
  include_ssnit_estimate: true,
})

onMounted(async () => {
  await store.fetchAll()
  if (store.schemes.length > 0 && !newAccount.value.scheme_id) {
    newAccount.value.scheme_id = store.schemes[0].id
  }
  if (store.accounts.length > 0) {
    selectedAccountId.value = store.accounts[0].id
    newValuation.value.account_id = store.accounts[0].id
    await store.fetchContributions(selectedAccountId.value)
  }
  if (store.ssnitProfile) {
    ssnitForm.value.total_contribution_months = store.ssnitProfile.total_contribution_months
    ssnitForm.value.membership_start_date = store.ssnitProfile.membership_start_date || ''
    ssnitForm.value.last_statement_date = store.ssnitProfile.last_statement_date || ''
    ssnitForm.value.notes = store.ssnitProfile.notes || ''
  }
})

watch(selectedAccountId, async (id) => {
  if (id) {
    await store.fetchContributions(id)
  }
})

async function handleCreateAccount() {
  if (!newAccount.value.scheme_id || !newAccount.value.account_name) return
  await store.createAccount(newAccount.value)
  newAccount.value.account_name = ''
  newAccount.value.member_reference = ''
}

async function handleRecordValuation() {
  if (!newValuation.value.account_id) return
  await store.recordValuation(newValuation.value.account_id, {
    valuation_date: newValuation.value.valuation_date,
    statement_balance: Number(newValuation.value.statement_balance),
    source_document_ref: newValuation.value.source_document_ref || undefined,
  })
}

async function handleRecordContribution() {
  if (!selectedAccountId.value) return
  await store.recordContribution(selectedAccountId.value, {
    ...newContribution.value,
    employee_amount: Number(newContribution.value.employee_amount),
    employer_amount: Number(newContribution.value.employer_amount),
    voluntary_amount: Number(newContribution.value.voluntary_amount),
    expected_amount: Number(newContribution.value.expected_amount) || undefined,
    actual_credited_amount: Number(newContribution.value.actual_credited_amount),
  })
}

async function handleSaveSSNIT() {
  await store.saveSSNITProfile({
    ssnit_number: ssnitForm.value.ssnit_number || undefined,
    membership_start_date: ssnitForm.value.membership_start_date || undefined,
    total_contribution_months: Number(ssnitForm.value.total_contribution_months),
    last_statement_date: ssnitForm.value.last_statement_date || undefined,
    notes: ssnitForm.value.notes || undefined,
  })
  ssnitForm.value.ssnit_number = ''
}

async function handleSaveSSNITEstimate() {
  await store.saveSSNITEstimate({
    target_retirement_age: Number(ssnitEstForm.value.target_retirement_age),
    source_type: ssnitEstForm.value.source_type,
    estimated_monthly_pension: Number(ssnitEstForm.value.estimated_monthly_pension),
    data_completeness_note: ssnitEstForm.value.data_completeness_note || undefined,
  })
}

async function handleRunForecast() {
  await store.runForecast({
    ...forecastForm.value,
    current_age: Number(forecastForm.value.current_age),
    retirement_age: Number(forecastForm.value.retirement_age),
    pensionable_salary: Number(forecastForm.value.pensionable_salary),
    salary_growth_pct: Number(forecastForm.value.salary_growth_pct),
    tier2_rate_pct: Number(forecastForm.value.tier2_rate_pct),
    tier3_monthly: Number(forecastForm.value.tier3_monthly),
    employer_match_pct: Number(forecastForm.value.employer_match_pct),
    expected_return_pct: Number(forecastForm.value.expected_return_pct),
    inflation_pct: Number(forecastForm.value.inflation_pct),
    annual_fee_pct: Number(forecastForm.value.annual_fee_pct),
    drawdown_years: Number(forecastForm.value.drawdown_years),
  })
}
</script>

<template>
  <AppLayout>
    <div class="space-y-6">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Landmark class="w-6 h-6 text-blue-600 dark:text-blue-400" />
            Retirement &amp; Pensions (Ghana 3-Tier)
          </h1>
          <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Track SSNIT Tier 1 service history separately from funded Tier 2 &amp; Tier 3 pension balances.
          </p>
        </div>
      </div>

      <!-- Tabs -->
      <div class="flex flex-wrap gap-2 border-b border-slate-200 dark:border-slate-800 pb-2">
        <button
          v-for="tab in [
            { id: 'overview', label: 'Overview' },
            { id: 'accounts', label: 'Tier 2 & Tier 3 Accounts' },
            { id: 'reconciliation', label: 'Contributions & Reconciliation' },
            { id: 'ssnit', label: 'SSNIT (Tier 1)' },
            { id: 'calculator', label: 'Retirement Calculator' },
          ]"
          :key="tab.id"
          @click="activeTab = tab.id as any"
          class="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors"
          :class="
            activeTab === tab.id
              ? 'bg-blue-600 text-white'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          "
        >
          {{ tab.label }}
        </button>
      </div>

      <!-- Overview -->
      <div v-if="activeTab === 'overview'" class="space-y-6">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
            <p class="text-xs uppercase tracking-wider text-slate-500">Funded Retirement (Tier 2 + Tier 3)</p>
            <p class="text-2xl font-bold text-slate-900 dark:text-white mt-2">
              {{ store.summary?.reporting_currency || 'GHS' }} {{ (store.summary?.total_funded_retirement_balance || 0).toLocaleString() }}
            </p>
            <p class="text-xs text-slate-500 mt-1">
              Tier 2: {{ (store.summary?.funded_tier2_balance || 0).toLocaleString() }} · Tier 3: {{ (store.summary?.funded_tier3_balance || 0).toLocaleString() }}
            </p>
          </div>

          <div class="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
            <p class="text-xs uppercase tracking-wider text-slate-500">Tier 2 Reconciliation Variance</p>
            <p
              class="text-2xl font-bold mt-2"
              :class="(store.summary?.tier2_reconciliation_variance || 0) < 0 ? 'text-amber-500' : 'text-emerald-500'"
            >
              {{ store.summary?.reporting_currency || 'GHS' }} {{ (store.summary?.tier2_reconciliation_variance || 0).toLocaleString() }}
            </p>
            <p class="text-xs text-slate-500 mt-1">
              Actual {{ (store.summary?.tier2_actual_credited || 0).toLocaleString() }} vs Expected {{ (store.summary?.tier2_expected_contributions || 0).toLocaleString() }}
            </p>
          </div>

          <div class="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
            <p class="text-xs uppercase tracking-wider text-slate-500 flex items-center gap-1">
              <Shield class="w-3.5 h-3.5 text-blue-500" /> SSNIT Tier 1 (Defined Benefit)
            </p>
            <p class="text-2xl font-bold text-slate-900 dark:text-white mt-2">
              {{ store.summary?.ssnit_contribution_months || 0 }} months
            </p>
            <p class="text-xs text-slate-500 mt-1">
              Excluded from funded net worth · Last stmt: {{ store.summary?.ssnit_last_statement_date || 'N/A' }}
            </p>
          </div>
        </div>

        <div class="p-4 rounded-xl border border-blue-500/20 bg-blue-500/5 text-xs text-slate-600 dark:text-slate-300">
          {{ store.summary?.payroll_framework_note }}
        </div>

        <div v-if="store.summary?.fx_warning" class="p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 text-xs text-amber-600 dark:text-amber-300 flex items-center gap-2">
          <AlertTriangle class="w-4 h-4 shrink-0" />
          {{ store.summary.fx_warning }}
        </div>
      </div>

      <!-- Accounts & Valuations -->
      <div v-if="activeTab === 'accounts'" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-4">
          <h2 class="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
            <Plus class="w-4 h-4" /> Add Pension Account
          </h2>
          <div class="space-y-3">
            <select v-model="newAccount.scheme_id" class="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2 text-sm">
              <option v-for="s in store.schemes" :key="s.id" :value="s.id">{{ s.tier }} — {{ s.name }}</option>
            </select>
            <input v-model="newAccount.account_name" placeholder="Account Name (e.g. Employer Tier 2)" class="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2 text-sm" />
            <input v-model="newAccount.employer_name" placeholder="Employer (optional)" class="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2 text-sm" />
            <input v-model="newAccount.member_reference" placeholder="Member Reference (masked in UI)" class="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2 text-sm" />
            <button @click="handleCreateAccount" class="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700">
              Create Account
            </button>
          </div>
        </div>

        <div class="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-4">
          <h2 class="font-semibold text-slate-900 dark:text-white">Record Statement Valuation</h2>
          <div class="space-y-3">
            <select v-model="newValuation.account_id" class="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2 text-sm">
              <option v-for="a in store.accounts" :key="a.id" :value="a.id">{{ a.tier }} — {{ a.account_name }}</option>
            </select>
            <input v-model="newValuation.valuation_date" type="date" class="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2 text-sm" />
            <input v-model.number="newValuation.statement_balance" type="number" step="0.01" placeholder="Statement Balance" class="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2 text-sm" />
            <input v-model="newValuation.source_document_ref" placeholder="Statement Ref (optional)" class="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2 text-sm" />
            <button @click="handleRecordValuation" class="px-4 py-2 rounded-lg bg-emerald-600 text-white text-sm font-medium hover:bg-emerald-700">
              Save Statement Balance
            </button>
          </div>
        </div>

        <div class="lg:col-span-2 p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
          <h2 class="font-semibold text-slate-900 dark:text-white mb-3">Registered Accounts</h2>
          <div class="overflow-x-auto">
            <table class="w-full text-sm text-left">
              <thead class="text-xs uppercase text-slate-500 border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th class="py-2">Tier</th>
                  <th class="py-2">Account</th>
                  <th class="py-2">Scheme</th>
                  <th class="py-2">Ref</th>
                  <th class="py-2 text-right">Statement Balance</th>
                  <th class="py-2 text-right">As Of</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="acc in store.accounts" :key="acc.id" class="border-b border-slate-100 dark:border-slate-800/60">
                  <td class="py-2 font-mono text-xs">{{ acc.tier }}</td>
                  <td class="py-2 font-medium">{{ acc.account_name }}</td>
                  <td class="py-2 text-slate-500">{{ acc.scheme_name }}</td>
                  <td class="py-2 font-mono text-xs">{{ acc.member_reference_masked || '—' }}</td>
                  <td class="py-2 text-right font-semibold">{{ acc.currency }} {{ acc.latest_balance.toLocaleString() }}</td>
                  <td class="py-2 text-right text-xs text-slate-500">{{ acc.last_valuation_date || 'No statement' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Contributions & Reconciliation -->
      <div v-if="activeTab === 'reconciliation'" class="space-y-6">
        <div class="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-4">
          <h2 class="font-semibold text-slate-900 dark:text-white">Record Contribution &amp; Reconcile</h2>
          <div class="grid grid-cols-1 sm:grid-cols-4 gap-3">
            <select v-model="selectedAccountId" class="rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2 text-sm">
              <option v-for="a in store.accounts" :key="a.id" :value="a.id">{{ a.tier }} — {{ a.account_name }}</option>
            </select>
            <input v-model="newContribution.pay_period" placeholder="Pay Period (YYYY-MM)" class="rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2 text-sm" />
            <input v-model.number="newContribution.expected_amount" type="number" step="0.01" placeholder="Expected Amount" class="rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2 text-sm" />
            <input v-model.number="newContribution.actual_credited_amount" type="number" step="0.01" placeholder="Actual Credited" class="rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2 text-sm" />
          </div>
          <button @click="handleRecordContribution" class="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700">
            Record Contribution
          </button>
        </div>

        <div class="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
          <h2 class="font-semibold text-slate-900 dark:text-white mb-3">Contribution History</h2>
          <table class="w-full text-sm text-left">
            <thead class="text-xs uppercase text-slate-500 border-b border-slate-200 dark:border-slate-800">
              <tr>
                <th class="py-2">Pay Period</th>
                <th class="py-2">Source</th>
                <th class="py-2 text-right">Expected</th>
                <th class="py-2 text-right">Actual Credited</th>
                <th class="py-2 text-right">Variance</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="c in store.contributions" :key="c.id" class="border-b border-slate-100 dark:border-slate-800/60">
                <td class="py-2 font-mono text-xs">{{ c.pay_period }}</td>
                <td class="py-2 text-xs">{{ c.source }}</td>
                <td class="py-2 text-right">{{ c.expected_amount ?? '—' }}</td>
                <td class="py-2 text-right font-medium">{{ c.actual_credited_amount.toLocaleString() }}</td>
                <td class="py-2 text-right" :class="(c.reconciliation_variance || 0) < 0 ? 'text-amber-500' : 'text-emerald-500'">
                  {{ c.reconciliation_variance ?? '—' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- SSNIT Tier 1 -->
      <div v-if="activeTab === 'ssnit'" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-4">
          <h2 class="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
            <CheckCircle2 class="w-4 h-4 text-blue-500" /> SSNIT Tier 1 Membership Profile
          </h2>
          <div class="space-y-3">
            <input v-model="ssnitForm.ssnit_number" placeholder="SSNIT Member Reference (stored masked)" class="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2 text-sm" />
            <label class="block text-xs text-slate-500">Total Contribution Months</label>
            <input v-model.number="ssnitForm.total_contribution_months" type="number" class="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2 text-sm" />
            <label class="block text-xs text-slate-500">Last Statement Date</label>
            <input v-model="ssnitForm.last_statement_date" type="date" class="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2 text-sm" />
            <button @click="handleSaveSSNIT" class="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700">
              Save SSNIT Profile
            </button>
          </div>
        </div>

        <div class="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-4">
          <h2 class="font-semibold text-slate-900 dark:text-white">SSNIT Monthly Benefit Estimate (Statement / User-Entered)</h2>
          <div class="space-y-3">
            <select v-model="ssnitEstForm.source_type" class="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2 text-sm">
              <option value="STATEMENT_DERIVED">Statement Derived</option>
              <option value="USER_ENTERED">User Entered</option>
            </select>
            <label class="block text-xs text-slate-500">Target Retirement Age</label>
            <input v-model.number="ssnitEstForm.target_retirement_age" type="number" class="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2 text-sm" />
            <label class="block text-xs text-slate-500">Estimated Monthly Pension (GHS)</label>
            <input v-model.number="ssnitEstForm.estimated_monthly_pension" type="number" step="0.01" class="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2 text-sm" />
            <button @click="handleSaveSSNITEstimate" class="px-4 py-2 rounded-lg bg-emerald-600 text-white text-sm font-medium hover:bg-emerald-700">
              Save SSNIT Estimate
            </button>
            <p v-if="store.ssnitEstimate" class="text-xs text-slate-500">
              Current Estimate: {{ store.ssnitEstimate.currency }} {{ store.ssnitEstimate.estimated_monthly_pension.toLocaleString() }}/mo (Age {{ store.ssnitEstimate.target_retirement_age }}, {{ store.ssnitEstimate.source_type }})
            </p>
          </div>
        </div>
      </div>

      <!-- Retirement Calculator -->
      <div v-if="activeTab === 'calculator'" class="space-y-6">
        <div class="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-4">
          <h2 class="font-semibold text-slate-900 dark:text-white">Retirement &amp; Pension Projection</h2>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
            <div>
              <label class="block text-xs text-slate-500 mb-1">Current Age</label>
              <input v-model.number="forecastForm.current_age" type="number" class="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2" />
            </div>
            <div>
              <label class="block text-xs text-slate-500 mb-1">Retirement Age</label>
              <input v-model.number="forecastForm.retirement_age" type="number" class="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2" />
            </div>
            <div>
              <label class="block text-xs text-slate-500 mb-1">Monthly Pensionable Salary</label>
              <input v-model.number="forecastForm.pensionable_salary" type="number" class="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2" />
            </div>
            <div>
              <label class="block text-xs text-slate-500 mb-1">Tier 3 Monthly</label>
              <input v-model.number="forecastForm.tier3_monthly" type="number" class="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2" />
            </div>
            <div>
              <label class="block text-xs text-slate-500 mb-1">Expected Return (%)</label>
              <input v-model.number="forecastForm.expected_return_pct" type="number" step="0.5" class="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2" />
            </div>
            <div>
              <label class="block text-xs text-slate-500 mb-1">Inflation (%)</label>
              <input v-model.number="forecastForm.inflation_pct" type="number" step="0.5" class="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2" />
            </div>
            <div>
              <label class="block text-xs text-slate-500 mb-1">Annual Fee (%)</label>
              <input v-model.number="forecastForm.annual_fee_pct" type="number" step="0.1" class="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2" />
            </div>
            <div>
              <label class="block text-xs text-slate-500 mb-1">Drawdown Years</label>
              <input v-model.number="forecastForm.drawdown_years" type="number" class="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2" />
            </div>
          </div>
          <button @click="handleRunForecast" class="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700">
            Run Retirement Projection
          </button>
        </div>

        <div v-if="store.forecast" class="space-y-4">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div class="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
              <p class="text-xs uppercase text-slate-500">Projected Funded Balance (Nominal)</p>
              <p class="text-xl font-bold mt-1">{{ store.forecast.reporting_currency }} {{ store.forecast.projected_funded_nominal.toLocaleString() }}</p>
              <p class="text-xs text-slate-500 mt-1">Today's Money (Real): {{ store.forecast.projected_funded_real.toLocaleString() }}</p>
            </div>
            <div class="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
              <p class="text-xs uppercase text-slate-500">Est. Monthly Income (Funded + SSNIT)</p>
              <p class="text-xl font-bold mt-1">{{ store.forecast.reporting_currency }} {{ store.forecast.combined_estimated_monthly_income_nominal.toLocaleString() }}/mo</p>
              <p class="text-xs text-slate-500 mt-1">
                Funded: {{ store.forecast.estimated_monthly_funded_income_nominal.toLocaleString() }} · SSNIT: {{ store.forecast.ssnit_estimated_monthly_pension ?? 'Not set' }}
              </p>
            </div>
            <div class="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
              <p class="text-xs uppercase text-slate-500">Contributions vs Growth</p>
              <p class="text-sm font-semibold mt-1">Contrib: {{ store.forecast.total_contributions_projected.toLocaleString() }}</p>
              <p class="text-sm text-emerald-500 font-semibold">Growth: {{ store.forecast.total_investment_growth_nominal.toLocaleString() }}</p>
            </div>
          </div>
          <p class="text-xs text-slate-500">{{ store.forecast.disclaimer }}</p>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
