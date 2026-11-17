<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  PlusCircle,
  PieChart,
  ArrowUpRight,
  ArrowDownRight,
  Coins,
  TrendingUp,
  History,
  DollarSign,
} from 'lucide-vue-next'
import AppLayout from '@/components/layout/AppLayout.vue'
import { usePortfolioStore } from '@/stores/portfolio'
import api from '@/services/api'
import { formatCurrency } from '@/lib/utils'

const portfolioStore = usePortfolioStore()
const selectedPortfolioId = ref<string | null>(null)
const activeSubTab = ref<'holdings' | 'transactions' | 'dividends'>('holdings')

const performance = ref<any>(null)
const transactions = ref<any[]>([])
const dividends = ref<any[]>([])
const instruments = ref<any[]>([])

// Modals
const showCreatePortfolioModal = ref(false)
const showTradeModal = ref(false)
const showDividendModal = ref(false)

// New Portfolio Form
const newPortfolioName = ref('')
const newPortfolioDesc = ref('')
const newPortfolioCurrency = ref('GHS')

// Trade Form
const tradeInstrumentId = ref('')
const tradeType = ref('BUY')
const tradeDate = ref(new Date().toISOString().split('T')[0])
const tradeQty = ref(10)
const tradePrice = ref(0)
const tradeFees = ref(0)
const tradeTaxes = ref(0)
const tradeCurrency = ref('GHS')
const tradeNotes = ref('')

// Dividend Form
const divInstrumentId = ref('')
const divPayableDate = ref(new Date().toISOString().split('T')[0])
const divGross = ref(0)
const divTax = ref(0)
const divCurrency = ref('GHS')
const divReinvested = ref(false)

async function loadPortfolioDetails(id: string) {
  await portfolioStore.fetchHoldings(id)
  try {
    const [perfRes, txRes, divRes] = await Promise.all([
      api.get(`/portfolios/${id}/performance`),
      api.get(`/portfolios/${id}/transactions`),
      api.get(`/portfolios/${id}/dividends`),
    ])
    performance.value = perfRes.data
    transactions.value = txRes.data
    dividends.value = divRes.data
  } catch (err) {
    console.error('Failed to load portfolio analytics', err)
  }
}

onMounted(async () => {
  await portfolioStore.fetchPortfolios()
  try {
    const instRes = await api.get('/markets/instruments')
    instruments.value = instRes.data
  } catch (err) {
    console.error('Failed to load instruments', err)
  }

  if (portfolioStore.portfolios.length > 0) {
    selectedPortfolioId.value = portfolioStore.portfolios[0].id
    await loadPortfolioDetails(selectedPortfolioId.value)
  }
})

async function handleSelectPortfolio(id: string) {
  selectedPortfolioId.value = id
  await loadPortfolioDetails(id)
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
      const latest = portfolioStore.portfolios[portfolioStore.portfolios.length - 1]
      selectedPortfolioId.value = latest.id
      await loadPortfolioDetails(latest.id)
    }
  }
}

function onInstrumentChange() {
  const inst = instruments.value.find(i => i.id === tradeInstrumentId.value)
  if (inst) {
    tradeCurrency.value = inst.currency_code
    if (inst.latest_price) tradePrice.value = inst.latest_price
  }
}

function onDivInstrumentChange() {
  const inst = instruments.value.find(i => i.id === divInstrumentId.value)
  if (inst) {
    divCurrency.value = inst.currency_code
  }
}

async function handleRecordTrade() {
  if (!selectedPortfolioId.value) return
  const success = await portfolioStore.recordTransaction(selectedPortfolioId.value, {
    instrument_id: tradeInstrumentId.value,
    transaction_type: tradeType.value,
    trade_date: tradeDate.value,
    quantity: tradeQty.value,
    price_per_share: tradePrice.value,
    fees: tradeFees.value,
    taxes: tradeTaxes.value,
    currency: tradeCurrency.value,
    notes: tradeNotes.value || undefined,
  })
  if (success) {
    showTradeModal.value = false
    await loadPortfolioDetails(selectedPortfolioId.value)
  }
}

async function handleRecordDividend() {
  if (!selectedPortfolioId.value) return
  try {
    await api.post(`/portfolios/${selectedPortfolioId.value}/dividends`, {
      instrument_id: divInstrumentId.value,
      payable_date: divPayableDate.value,
      gross_amount: divGross.value,
      withholding_tax: divTax.value,
      currency: divCurrency.value,
      is_reinvested: divReinvested.value,
    })
    showDividendModal.value = false
    await loadPortfolioDetails(selectedPortfolioId.value)
  } catch (err) {
    console.error('Failed to record dividend', err)
  }
}
</script>

<template>
  <AppLayout>
    <div class="space-y-6 max-w-7xl mx-auto">
      <!-- Header -->
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold text-white tracking-tight">Investment Portfolios</h1>
          <p class="text-sm text-slate-400">Equity holdings, XIRR return analytics, FIFO tax-lots, and dividend tracking</p>
        </div>
        <div class="flex items-center gap-2">
          <button
            v-if="selectedPortfolioId"
            @click="showDividendModal = true"
            class="inline-flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-emerald-400 text-xs font-medium px-3 py-2 rounded-lg border border-slate-700 transition-colors"
          >
            <Coins class="w-4 h-4" />
            <span>Log Dividend</span>
          </button>
          <button
            v-if="selectedPortfolioId"
            @click="showTradeModal = true"
            class="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium px-3 py-2 rounded-lg transition-colors shadow-lg shadow-emerald-600/20"
          >
            <PlusCircle class="w-4 h-4" />
            <span>Record Trade</span>
          </button>
          <button
            @click="showCreatePortfolioModal = true"
            class="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium px-3 py-2 rounded-lg transition-colors shadow-lg shadow-blue-600/20"
          >
            <PlusCircle class="w-4 h-4" />
            <span>New Portfolio</span>
          </button>
        </div>
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

      <!-- Institutional Performance KPI Bar -->
      <div v-if="performance" class="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div class="bg-card border border-border rounded-xl p-4">
          <span class="text-xs text-slate-400 uppercase font-semibold">Market Value</span>
          <p class="text-xl font-bold font-mono text-white mt-1">
            {{ formatCurrency(performance.total_market_value, performance.reporting_currency) }}
          </p>
        </div>

        <div class="bg-card border border-border rounded-xl p-4">
          <span class="text-xs text-slate-400 uppercase font-semibold">Cost Basis</span>
          <p class="text-xl font-bold font-mono text-slate-300 mt-1">
            {{ formatCurrency(performance.total_cost_basis, performance.reporting_currency) }}
          </p>
        </div>

        <div class="bg-card border border-border rounded-xl p-4">
          <span class="text-xs text-slate-400 uppercase font-semibold">Total Return</span>
          <div class="flex items-center gap-1.5 mt-1">
            <span class="text-xl font-bold font-mono" :class="performance.total_return_amount >= 0 ? 'text-emerald-400' : 'text-rose-400'">
              {{ formatCurrency(performance.total_return_amount, performance.reporting_currency) }}
            </span>
          </div>
          <span class="text-[10px] font-mono" :class="performance.total_return_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'">
            {{ performance.total_return_pct >= 0 ? '+' : '' }}{{ performance.total_return_pct }}%
          </span>
        </div>

        <div class="bg-card border border-border rounded-xl p-4">
          <span class="text-xs text-slate-400 uppercase font-semibold flex items-center gap-1">
            <TrendingUp class="w-3.5 h-3.5 text-blue-400" /> XIRR (Annualized)
          </span>
          <p class="text-xl font-bold font-mono text-blue-400 mt-1">
            {{ performance.xirr_annualized_pct !== null ? `${performance.xirr_annualized_pct}%` : '—' }}
          </p>
          <span class="text-[10px] text-slate-500 font-mono">Money-weighted</span>
        </div>

        <div class="bg-card border border-border rounded-xl p-4">
          <span class="text-xs text-slate-400 uppercase font-semibold flex items-center gap-1">
            <Coins class="w-3.5 h-3.5 text-amber-400" /> Net Dividends
          </span>
          <p class="text-xl font-bold font-mono text-amber-400 mt-1">
            {{ formatCurrency(performance.total_dividends_net, performance.reporting_currency) }}
          </p>
          <span class="text-[10px] text-slate-500 font-mono">After WHT</span>
        </div>
      </div>

      <!-- Sub-navigation Tabs -->
      <div v-if="selectedPortfolioId" class="flex items-center gap-4 border-b border-border pb-2">
        <button
          @click="activeSubTab = 'holdings'"
          class="text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors"
          :class="activeSubTab === 'holdings' ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-white'"
        >
          Holdings ({{ portfolioStore.holdings.length }})
        </button>
        <button
          @click="activeSubTab = 'transactions'"
          class="text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5"
          :class="activeSubTab === 'transactions' ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-white'"
        >
          <History class="w-3.5 h-3.5" />
          <span>Trade Ledger ({{ transactions.length }})</span>
        </button>
        <button
          @click="activeSubTab = 'dividends'"
          class="text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5"
          :class="activeSubTab === 'dividends' ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-white'"
        >
          <DollarSign class="w-3.5 h-3.5" />
          <span>Dividends ({{ dividends.length }})</span>
        </button>
      </div>

      <!-- Holdings Table -->
      <div v-if="activeSubTab === 'holdings'" class="bg-card border border-border rounded-xl overflow-hidden shadow-sm">
        <table class="w-full text-left text-sm text-slate-300">
          <thead class="bg-slate-900/60 text-xs uppercase font-semibold text-slate-400 border-b border-border">
            <tr>
              <th class="px-6 py-4">Symbol</th>
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
              <td class="px-6 py-4 font-mono font-bold text-white">
                <span class="px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 text-xs">
                  {{ h.symbol }}
                </span>
              </td>
              <td class="px-6 py-4 text-sm text-slate-300 font-medium">{{ h.instrument_name }}</td>
              <td class="px-6 py-4 text-right font-mono text-slate-200">{{ h.quantity.toLocaleString() }}</td>
              <td class="px-6 py-4 text-right font-mono text-slate-400">{{ formatCurrency(h.average_cost_per_share, h.currency) }}</td>
              <td class="px-6 py-4 text-right font-mono text-slate-200 font-semibold">{{ formatCurrency(h.current_price, h.currency) }}</td>
              <td class="px-6 py-4 text-right font-mono font-bold text-white">{{ formatCurrency(h.current_market_value, h.currency) }}</td>
              <td class="px-6 py-4 text-right font-mono font-bold" :class="h.unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'">
                {{ formatCurrency(h.unrealized_pnl, h.currency) }}
              </td>
            </tr>
            <tr v-if="portfolioStore.holdings.length === 0">
              <td colspan="7" class="px-6 py-12 text-center text-slate-500">
                No positions recorded in this portfolio yet. Click "Record Trade" to add your first stock or ETF.
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Transactions Ledger Table -->
      <div v-if="activeSubTab === 'transactions'" class="bg-card border border-border rounded-xl overflow-hidden shadow-sm">
        <table class="w-full text-left text-sm text-slate-300">
          <thead class="bg-slate-900/60 text-xs uppercase font-semibold text-slate-400 border-b border-border">
            <tr>
              <th class="px-6 py-4">Trade Date</th>
              <th class="px-6 py-4">Type</th>
              <th class="px-6 py-4">Symbol</th>
              <th class="px-6 py-4 text-right">Qty</th>
              <th class="px-6 py-4 text-right">Price</th>
              <th class="px-6 py-4 text-right">Fees + Tax</th>
              <th class="px-6 py-4 text-right">Net Amount</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border/60">
            <tr v-for="tx in transactions" :key="tx.id" class="hover:bg-slate-800/30 font-mono text-xs">
              <td class="px-6 py-4 text-slate-300">{{ tx.trade_date }}</td>
              <td class="px-6 py-4">
                <span class="px-2 py-0.5 rounded font-bold" :class="tx.transaction_type === 'BUY' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'">
                  {{ tx.transaction_type }}
                </span>
              </td>
              <td class="px-6 py-4 font-bold text-white">{{ tx.symbol }}</td>
              <td class="px-6 py-4 text-right">{{ tx.quantity }}</td>
              <td class="px-6 py-4 text-right">{{ formatCurrency(tx.price_per_share, tx.currency) }}</td>
              <td class="px-6 py-4 text-right text-slate-400">{{ formatCurrency(tx.fees + tx.taxes, tx.currency) }}</td>
              <td class="px-6 py-4 text-right font-bold text-white">{{ formatCurrency(tx.net_amount, tx.currency) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Dividends Table -->
      <div v-if="activeSubTab === 'dividends'" class="bg-card border border-border rounded-xl overflow-hidden shadow-sm">
        <table class="w-full text-left text-sm text-slate-300">
          <thead class="bg-slate-900/60 text-xs uppercase font-semibold text-slate-400 border-b border-border">
            <tr>
              <th class="px-6 py-4">Payable Date</th>
              <th class="px-6 py-4">Symbol</th>
              <th class="px-6 py-4 text-right">Gross</th>
              <th class="px-6 py-4 text-right">Withholding Tax</th>
              <th class="px-6 py-4 text-right">Net Cash</th>
              <th class="px-6 py-4">Reinvested</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border/60">
            <tr v-for="d in dividends" :key="d.id" class="hover:bg-slate-800/30 font-mono text-xs">
              <td class="px-6 py-4 text-slate-300">{{ d.payable_date }}</td>
              <td class="px-6 py-4 font-bold text-white">{{ d.symbol }}</td>
              <td class="px-6 py-4 text-right">{{ formatCurrency(d.gross_amount, d.currency) }}</td>
              <td class="px-6 py-4 text-right text-rose-400">{{ formatCurrency(d.withholding_tax, d.currency) }}</td>
              <td class="px-6 py-4 text-right font-bold text-emerald-400">{{ formatCurrency(d.net_amount, d.currency) }}</td>
              <td class="px-6 py-4">{{ d.is_reinvested ? 'Yes' : 'Cash' }}</td>
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
              <input v-model="newPortfolioName" required placeholder="e.g. GSE Equities, US Growth" class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-white" />
            </div>
            <div>
              <label class="block text-xs font-medium text-slate-300 mb-1">Reporting Currency</label>
              <select v-model="newPortfolioCurrency" class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-white">
                <option value="GHS">GHS</option>
                <option value="USD">USD</option>
                <option value="GBP">GBP</option>
                <option value="EUR">EUR</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-medium text-slate-300 mb-1">Description</label>
              <textarea v-model="newPortfolioDesc" rows="2" class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-white"></textarea>
            </div>
            <div class="flex justify-end gap-3 pt-4 border-t border-border">
              <button @click="showCreatePortfolioModal = false" type="button" class="px-4 py-2 text-xs text-slate-400 hover:text-white">Cancel</button>
              <button type="submit" class="bg-blue-600 hover:bg-blue-500 text-white font-medium px-4 py-2 rounded-lg text-xs">Create</button>
            </div>
          </form>
        </div>
      </div>

      <!-- Record Trade Modal -->
      <div v-if="showTradeModal" class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div class="bg-card border border-border rounded-xl w-full max-w-lg p-6 space-y-4 shadow-2xl">
          <div class="flex items-center justify-between border-b border-border pb-3">
            <h3 class="font-bold text-white text-base">Record Investment Trade</h3>
            <button @click="showTradeModal = false" class="text-slate-400 hover:text-white">&times;</button>
          </div>
          <form @submit.prevent="handleRecordTrade" class="space-y-4">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-medium text-slate-300 mb-1">Instrument</label>
                <select v-model="tradeInstrumentId" @change="onInstrumentChange" required class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-white">
                  <option disabled value="">Select Ticker</option>
                  <option v-for="inst in instruments" :key="inst.id" :value="inst.id">{{ inst.symbol }} ({{ inst.exchange_code }})</option>
                </select>
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-300 mb-1">Action</label>
                <select v-model="tradeType" class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-white">
                  <option value="BUY">BUY</option>
                  <option value="SELL">SELL</option>
                </select>
              </div>
            </div>
            <div class="grid grid-cols-3 gap-4">
              <div>
                <label class="block text-xs font-medium text-slate-300 mb-1">Trade Date</label>
                <input v-model="tradeDate" type="date" required class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-xs text-white" />
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-300 mb-1">Quantity</label>
                <input v-model.number="tradeQty" type="number" step="0.0001" min="0.0001" required class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-xs text-white font-mono" />
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-300 mb-1">Price ({{ tradeCurrency }})</label>
                <input v-model.number="tradePrice" type="number" step="0.0001" min="0" required class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-xs text-white font-mono" />
              </div>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-medium text-slate-300 mb-1">Broker Fees</label>
                <input v-model.number="tradeFees" type="number" step="0.01" min="0" class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-xs text-white font-mono" />
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-300 mb-1">Taxes / Levies</label>
                <input v-model.number="tradeTaxes" type="number" step="0.01" min="0" class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-xs text-white font-mono" />
              </div>
            </div>
            <div class="flex justify-end gap-3 pt-4 border-t border-border">
              <button @click="showTradeModal = false" type="button" class="px-4 py-2 text-xs text-slate-400 hover:text-white">Cancel</button>
              <button type="submit" class="bg-emerald-600 hover:bg-emerald-500 text-white font-medium px-4 py-2 rounded-lg text-xs">Submit Trade</button>
            </div>
          </form>
        </div>
      </div>

      <!-- Record Dividend Modal -->
      <div v-if="showDividendModal" class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div class="bg-card border border-border rounded-xl w-full max-w-md p-6 space-y-4 shadow-2xl">
          <div class="flex items-center justify-between border-b border-border pb-3">
            <h3 class="font-bold text-white text-base">Log Dividend Distribution</h3>
            <button @click="showDividendModal = false" class="text-slate-400 hover:text-white">&times;</button>
          </div>
          <form @submit.prevent="handleRecordDividend" class="space-y-4">
            <div>
              <label class="block text-xs font-medium text-slate-300 mb-1">Instrument</label>
              <select v-model="divInstrumentId" @change="onDivInstrumentChange" required class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-white">
                <option disabled value="">Select Ticker</option>
                <option v-for="inst in instruments" :key="inst.id" :value="inst.id">{{ inst.symbol }} ({{ inst.exchange_code }})</option>
              </select>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-medium text-slate-300 mb-1">Payable Date</label>
                <input v-model="divPayableDate" type="date" required class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-xs text-white" />
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-300 mb-1">Currency</label>
                <input v-model="divCurrency" readonly class="w-full bg-slate-800 border border-border rounded-lg px-3 py-2 text-xs text-slate-400 font-mono" />
              </div>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-medium text-slate-300 mb-1">Gross Dividend</label>
                <input v-model.number="divGross" type="number" step="0.01" min="0.01" required class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-xs text-white font-mono" />
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-300 mb-1">Withholding Tax</label>
                <input v-model.number="divTax" type="number" step="0.01" min="0" class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-xs text-white font-mono" />
              </div>
            </div>
            <div class="flex items-center gap-2">
              <input v-model="divReinvested" type="checkbox" id="reinvest" class="rounded bg-slate-900 border-border" />
              <label for="reinvest" class="text-xs text-slate-300">Dividend was automatically reinvested (DRIP)</label>
            </div>
            <div class="flex justify-end gap-3 pt-4 border-t border-border">
              <button @click="showDividendModal = false" type="button" class="px-4 py-2 text-xs text-slate-400 hover:text-white">Cancel</button>
              <button type="submit" class="bg-blue-600 hover:bg-blue-500 text-white font-medium px-4 py-2 rounded-lg text-xs">Save Dividend</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
