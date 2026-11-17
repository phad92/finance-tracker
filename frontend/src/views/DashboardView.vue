<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  TrendingUp,
  Wallet,
  CreditCard,
  PieChart,
  PlusCircle,
  ArrowUpRight,
  Globe,
  Landmark,
} from 'lucide-vue-next'
import AppLayout from '@/components/layout/AppLayout.vue'
import { useWealthStore } from '@/stores/wealth'
import { useAuthStore } from '@/stores/auth'
import { usePensionsStore } from '@/stores/pensions'
import { formatCurrency } from '@/lib/utils'

const router = useRouter()
const wealthStore = useWealthStore()
const authStore = useAuthStore()
const pensionsStore = usePensionsStore()

onMounted(async () => {
  await authStore.fetchMe()
  await Promise.all([wealthStore.fetchSummary(), pensionsStore.fetchAll()])
})
</script>

<template>
  <AppLayout>
    <div class="space-y-8 max-w-7xl mx-auto">
      <!-- Page Header -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Financial Overview</h1>
          <p class="text-sm text-slate-500 dark:text-slate-400">Consolidated balance sheet and multi-currency wealth status</p>
        </div>
        <div class="flex items-center gap-3">
          <router-link
            to="/wealth"
            class="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium px-4 py-2 rounded-lg transition-colors shadow-lg shadow-blue-600/20"
          >
            <PlusCircle class="w-4 h-4" />
            <span>Manage Assets</span>
          </router-link>
          <router-link
            to="/forecasting"
            class="inline-flex items-center gap-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-medium px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 transition-colors"
          >
            <TrendingUp class="w-4 h-4 text-emerald-500 dark:text-emerald-400" />
            <span>Run Forecast</span>
          </router-link>
        </div>
      </div>

      <!-- Core KPI Cards -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- Net Worth Card -->
        <div class="bg-card border border-border rounded-xl p-6 relative overflow-hidden shadow-sm">
          <div class="flex items-center justify-between mb-4">
            <span class="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Total Net Worth</span>
            <div class="p-2 rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400">
              <Wallet class="w-5 h-5" />
            </div>
          </div>
          <div class="text-3xl font-bold text-slate-900 dark:text-white font-mono tracking-tight">
            {{ formatCurrency(wealthStore.summary?.net_worth || 0, wealthStore.summary?.reporting_currency) }}
          </div>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-2 flex items-center gap-1">
            <ArrowUpRight class="w-3.5 h-3.5 text-emerald-500 dark:text-emerald-400" />
            <span>Reporting Base: {{ wealthStore.summary?.reporting_currency || 'GHS' }}</span>
          </p>
        </div>

        <!-- Total Assets Card -->
        <div class="bg-card border border-border rounded-xl p-6 shadow-sm">
          <div class="flex items-center justify-between mb-4">
            <span class="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Total Assets</span>
            <div class="p-2 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
              <TrendingUp class="w-5 h-5" />
            </div>
          </div>
          <div class="text-3xl font-bold text-emerald-600 dark:text-emerald-400 font-mono tracking-tight">
            {{ formatCurrency(wealthStore.summary?.total_assets || 0, wealthStore.summary?.reporting_currency) }}
          </div>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-2">
            Cash, MoMo, equities, real estate & alternative assets
          </p>
        </div>

        <!-- Total Liabilities Card -->
        <div class="bg-card border border-border rounded-xl p-6 shadow-sm">
          <div class="flex items-center justify-between mb-4">
            <span class="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Total Liabilities</span>
            <div class="p-2 rounded-lg bg-rose-500/10 text-rose-600 dark:text-rose-400">
              <CreditCard class="w-5 h-5" />
            </div>
          </div>
          <div class="text-3xl font-bold text-rose-600 dark:text-rose-400 font-mono tracking-tight">
            {{ formatCurrency(wealthStore.summary?.total_liabilities || 0, wealthStore.summary?.reporting_currency) }}
          </div>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-2">
            Outstanding loans, mortgages & debt obligations
          </p>
        </div>
      </div>

      <!-- Breakdown Grid -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Asset Allocation by Category -->
        <div class="bg-card border border-border rounded-xl p-6 shadow-sm">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <PieChart class="w-4 h-4 text-blue-600 dark:text-blue-400" />
              <span>Asset Category Breakdown</span>
            </h2>
            <router-link to="/wealth" class="text-xs text-blue-600 dark:text-blue-400 hover:underline">View details</router-link>
          </div>

          <div v-if="wealthStore.summary?.assets_by_category && Object.keys(wealthStore.summary.assets_by_category).length > 0" class="space-y-4">
            <div
              v-for="(amount, category) in wealthStore.summary.assets_by_category"
              :key="category"
              class="flex items-center justify-between py-2 border-b border-border/50 last:border-none"
            >
              <div class="flex items-center gap-3">
                <div class="w-2.5 h-2.5 rounded-full bg-blue-500"></div>
                <span class="text-sm font-medium text-slate-700 dark:text-slate-200">{{ category }}</span>
              </div>
              <div class="text-right">
                <span class="text-sm font-mono font-semibold text-slate-900 dark:text-white">
                  {{ formatCurrency(amount, wealthStore.summary.reporting_currency) }}
                </span>
                <p class="text-[10px] text-slate-500 dark:text-slate-400 font-mono">
                  {{ ((amount / (wealthStore.summary.total_assets || 1)) * 100).toFixed(1) }}%
                </p>
              </div>
            </div>
          </div>
          <div v-else class="text-center py-12 text-slate-500 text-sm">
            No assets recorded yet. Click "Manage Assets" to add your bank accounts, MoMo, or properties.
          </div>
        </div>

        <!-- Currency Exposure Breakdown -->
        <div class="bg-card border border-border rounded-xl p-6 shadow-sm">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <Globe class="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
              <span>Multi-Currency Asset Exposure</span>
            </h2>
          </div>

          <div v-if="wealthStore.summary?.currency_exposure && Object.keys(wealthStore.summary.currency_exposure).length > 0" class="space-y-4">
            <div
              v-for="(amount, curr) in wealthStore.summary.currency_exposure"
              :key="curr"
              class="flex items-center justify-between py-2 border-b border-border/50 last:border-none"
            >
              <div class="flex items-center gap-3">
                <span class="text-xs font-mono font-bold bg-slate-100 dark:bg-slate-800 text-blue-600 dark:text-blue-400 px-2.5 py-1 rounded border border-slate-200 dark:border-slate-700">
                  {{ curr }}
                </span>
                <span class="text-sm text-slate-600 dark:text-slate-300">Converted Value ({{ wealthStore.summary.reporting_currency }})</span>
              </div>
              <div class="text-right">
                <span class="text-sm font-mono font-semibold text-slate-900 dark:text-white">
                  {{ formatCurrency(amount, wealthStore.summary.reporting_currency) }}
                </span>
                <p class="text-[10px] text-slate-500 dark:text-slate-400 font-mono">
                  {{ ((amount / (wealthStore.summary.total_assets || 1)) * 100).toFixed(1) }}% of assets
                </p>
              </div>
            </div>
          </div>
          <div v-else class="text-center py-12 text-slate-500 text-sm">
            No multi-currency holdings recorded yet.
          </div>
        </div>
      </div>

      <!-- Compact Retirement & Pensions Summary -->
      <div class="bg-card border border-border rounded-xl p-6 shadow-sm">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
            <Landmark class="w-4 h-4 text-blue-600 dark:text-blue-400" />
            <span>Retirement &amp; Pensions (Ghana 3-Tier)</span>
          </h2>
          <router-link to="/pensions" class="text-xs text-blue-600 dark:text-blue-400 hover:underline">Open Pensions</router-link>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <p class="text-xs text-slate-500">Funded Balances (Tier 2 + Tier 3)</p>
            <p class="text-xl font-bold font-mono text-slate-900 dark:text-white mt-1">
              {{ formatCurrency(pensionsStore.summary?.total_funded_retirement_balance || 0, pensionsStore.summary?.reporting_currency) }}
            </p>
          </div>
          <div>
            <p class="text-xs text-slate-500">SSNIT Tier 1 (Separate · Defined Benefit)</p>
            <p class="text-xl font-bold font-mono text-slate-900 dark:text-white mt-1">
              {{ pensionsStore.summary?.ssnit_contribution_months || 0 }} months
            </p>
          </div>
          <div>
            <p class="text-xs text-slate-500">Est. SSNIT Monthly Pension</p>
            <p class="text-xl font-bold font-mono text-slate-900 dark:text-white mt-1">
              {{
                pensionsStore.ssnitEstimate
                  ? formatCurrency(pensionsStore.ssnitEstimate.estimated_monthly_pension, pensionsStore.ssnitEstimate.currency)
                  : 'Not recorded'
              }}
            </p>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

