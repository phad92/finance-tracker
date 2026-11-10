<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { PlusCircle, PieChart, ArrowUpRight, ArrowDownRight, Layers } from 'lucide-vue-next'
import AppLayout from '@/components/layout/AppLayout.vue'
import { usePortfolioStore } from '@/stores/portfolio'
import { formatCurrency } from '@/lib/utils'

const portfolioStore = usePortfolioStore()
const selectedPortfolioId = ref<string | null>(null)
const showCreatePortfolioModal = ref(false)

// New Portfolio Form
const newPortfolioName = ref('')
const newPortfolioDesc = ref('')
const newPortfolioCurrency = ref('GHS')

onMounted(async () => {
  await portfolioStore.fetchPortfolios()
  if (portfolioStore.portfolios.length > 0) {
    selectedPortfolioId.value = portfolioStore.portfolios[0].id
    await portfolioStore.fetchHoldings(selectedPortfolioId.value)
  }
})

async function handleSelectPortfolio(id: string) {
  selectedPortfolioId.value = id
  await portfolioStore.fetchHoldings(id)
}

async function handleCreatePortfolio() {
  const success = await portfolioStore.createPortfolio({
    name: newPortfolioName.value,
    description: newPortfolioDesc.value || undefined,
    reporting_currency: newPortfolioCurrency.value,
  })
  if (success) {
    showCreatePortfolioModal.value = false
    newPortfolioName.value = ''
    newPortfolioDesc.value = ''
    if (portfolioStore.portfolios.length > 0) {
      selectedPortfolioId.value = portfolioStore.portfolios[0].id
    }
  }
}
</script>

<template>
  <AppLayout>
    <div class="space-y-6 max-w-7xl mx-auto">
      <!-- Header -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-white tracking-tight">Investment Portfolios</h1>
          <p class="text-sm text-slate-400">Equity holdings, ETF allocations, and realized/unrealized performance</p>
        </div>
        <button
          @click="showCreatePortfolioModal = true"
          class="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium px-4 py-2 rounded-lg transition-colors shadow-lg shadow-blue-600/20"
        >
          <PlusCircle class="w-4 h-4" />
          <span>New Portfolio</span>
        </button>
      </div>

      <!-- Portfolio Selector Tabs -->
      <div v-if="portfolioStore.portfolios.length > 0" class="flex items-center gap-3 overflow-x-auto pb-2 border-b border-border">
        <button
          v-for="p in portfolioStore.portfolios"
          :key="p.id"
          @click="handleSelectPortfolio(p.id)"
          class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap"
          :class="selectedPortfolioId === p.id ? 'bg-blue-600 text-white shadow-md shadow-blue-600/20 font-semibold' : 'text-slate-400 hover:text-white bg-slate-900 border border-slate-800'"
        >
          <PieChart class="w-4 h-4" />
          <span>{{ p.name }}</span>
          <span class="text-xs font-mono opacity-80">({{ p.reporting_currency }})</span>
        </button>
      </div>

      <!-- Portfolio KPI Bar -->
      <div v-if="portfolioStore.portfolios.length > 0" class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div class="bg-card border border-border rounded-xl p-4">
          <span class="text-xs text-slate-400 uppercase font-semibold">Total Market Value</span>
          <p class="text-2xl font-bold font-mono text-white mt-1">
            {{ formatCurrency(portfolioStore.portfolios.find(p => p.id === selectedPortfolioId)?.total_value_reporting || 0) }}
          </p>
        </div>

        <div class="bg-card border border-border rounded-xl p-4">
          <span class="text-xs text-slate-400 uppercase font-semibold">Total Cost Basis</span>
          <p class="text-2xl font-bold font-mono text-slate-300 mt-1">
            {{ formatCurrency(portfolioStore.portfolios.find(p => p.id === selectedPortfolioId)?.total_cost_basis_reporting || 0) }}
          </p>
        </div>

        <div class="bg-card border border-border rounded-xl p-4">
          <span class="text-xs text-slate-400 uppercase font-semibold">Unrealized P&L</span>
          <div class="flex items-center gap-2 mt-1">
            <span
              class="text-2xl font-bold font-mono"
              :class="(portfolioStore.portfolios.find(p => p.id === selectedPortfolioId)?.total_unrealized_pnl_reporting || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'"
            >
              {{ formatCurrency(portfolioStore.portfolios.find(p => p.id === selectedPortfolioId)?.total_unrealized_pnl_reporting || 0) }}
            </span>
            <component
              :is="(portfolioStore.portfolios.find(p => p.id === selectedPortfolioId)?.total_unrealized_pnl_reporting || 0) >= 0 ? ArrowUpRight : ArrowDownRight"
              class="w-5 h-5"
              :class="(portfolioStore.portfolios.find(p => p.id === selectedPortfolioId)?.total_unrealized_pnl_reporting || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'"
            />
          </div>
        </div>

        <div class="bg-card border border-border rounded-xl p-4">
          <span class="text-xs text-slate-400 uppercase font-semibold">Positions Count</span>
          <p class="text-2xl font-bold font-mono text-blue-400 mt-1">
            {{ portfolioStore.holdings.length }} Holdings
          </p>
        </div>
      </div>

      <!-- Holdings Table -->
      <div class="bg-card border border-border rounded-xl overflow-hidden shadow-sm">
        <table class="w-full text-left text-sm text-slate-300">
          <thead class="bg-slate-900/60 text-xs uppercase font-semibold text-slate-400 border-b border-border">
            <tr>
              <th class="px-6 py-4">Symbol / Ticker</th>
              <th class="px-6 py-4">Security Name</th>
              <th class="px-6 py-4 text-right">Shares</th>
              <th class="px-6 py-4 text-right">Avg Cost</th>
              <th class="px-6 py-4 text-right">Current Price</th>
              <th class="px-6 py-4 text-right">Market Value</th>
              <th class="px-6 py-4 text-right">Unrealized P&L</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border/60">
            <tr v-for="h in portfolioStore.holdings" :key="h.id" class="hover:bg-slate-800/30 transition-colors">
              <td class="px-6 py-4 font-mono font-bold text-white flex items-center gap-2">
                <span class="px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 text-xs">
                  {{ h.symbol }}
                </span>
              </td>
              <td class="px-6 py-4 text-sm text-slate-300 font-medium">
                {{ h.instrument_name }}
              </td>
              <td class="px-6 py-4 text-right font-mono text-slate-200">
                {{ h.quantity.toLocaleString() }}
              </td>
              <td class="px-6 py-4 text-right font-mono text-slate-400">
                {{ formatCurrency(h.average_cost_per_share, h.currency) }}
              </td>
              <td class="px-6 py-4 text-right font-mono text-slate-200 font-semibold">
                {{ formatCurrency(h.current_price, h.currency) }}
              </td>
              <td class="px-6 py-4 text-right font-mono font-bold text-white">
                {{ formatCurrency(h.current_market_value, h.currency) }}
              </td>
              <td
                class="px-6 py-4 text-right font-mono font-bold"
                :class="h.unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'"
              >
                {{ formatCurrency(h.unrealized_pnl, h.currency) }}
              </td>
            </tr>
            <tr v-if="portfolioStore.holdings.length === 0">
              <td colspan="7" class="px-6 py-12 text-center text-slate-500">
                No stock or ETF positions recorded in this portfolio yet.
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Create Portfolio Modal -->
      <div v-if="showCreatePortfolioModal" class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div class="bg-card border border-border rounded-xl w-full max-w-md p-6 space-y-4 shadow-2xl">
          <div class="flex items-center justify-between border-b border-border pb-3">
            <h3 class="font-bold text-white text-base">Create Portfolio</h3>
            <button @click="showCreatePortfolioModal = false" class="text-slate-400 hover:text-white">&times;</button>
          </div>

          <form @submit.prevent="handleCreatePortfolio" class="space-y-4">
            <div>
              <label class="block text-xs font-medium text-slate-300 mb-1">Portfolio Name</label>
              <input v-model="newPortfolioName" required placeholder="e.g. GSE Equities, US Long Term Growth" class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
            </div>

            <div>
              <label class="block text-xs font-medium text-slate-300 mb-1">Reporting Currency</label>
              <select v-model="newPortfolioCurrency" class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500">
                <option value="GHS">GHS (Ghana Cedi)</option>
                <option value="USD">USD (US Dollar)</option>
                <option value="GBP">GBP (British Pound)</option>
                <option value="EUR">EUR (Euro)</option>
              </select>
            </div>

            <div>
              <label class="block text-xs font-medium text-slate-300 mb-1">Description (Optional)</label>
              <textarea v-model="newPortfolioDesc" rows="3" placeholder="Strategic notes or allocation target" class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"></textarea>
            </div>

            <div class="flex justify-end gap-3 pt-4 border-t border-border">
              <button @click="showCreatePortfolioModal = false" type="button" class="px-4 py-2 text-xs text-slate-400 hover:text-white">Cancel</button>
              <button type="submit" class="bg-blue-600 hover:bg-blue-500 text-white font-medium px-4 py-2 rounded-lg text-xs shadow-md shadow-blue-600/20">Create Portfolio</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
