<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  ShieldAlert,
  Layers,
  Activity,
  PlusCircle,
  Calculator,
  AlertTriangle,
} from 'lucide-vue-next'
import AppLayout from '@/components/layout/AppLayout.vue'
import { usePortfolioStore } from '@/stores/portfolio'
import api from '@/services/api'
import { formatCurrency } from '@/lib/utils'

const portfolioStore = usePortfolioStore()
const activeTab = ref<'book' | 'lab' | 'risk'>('book')

// Options Book state
const positions = ref<any[]>([])
const showNewOptionModal = ref(false)
const newPos = ref({
  underlying_symbol: 'AAPL',
  option_type: 'CALL',
  side: 'LONG',
  strategy_tag: 'SINGLE_LEG',
  exercise_style: 'AMERICAN',
  strike_price: 230,
  expiration_date: '2027-01-15',
  contract_multiplier: 100,
  contracts: 1,
  entry_premium: 8.5,
  fees: 1.3,
  currency: 'USD',
  assumed_volatility: 0.28,
})

// Calculator & Strategy Payoff state
const calcInput = ref({
  spot_price: 225,
  strike_price: 230,
  days_to_expiry: 45,
  volatility: 0.28,
  risk_free_rate: 0.045,
  option_type: 'CALL',
  side: 'LONG',
  exercise_style: 'AMERICAN',
  contract_multiplier: 100,
  contracts: 1,
  entry_premium: 7.5,
})
const calcResult = ref<any>(null)
const strategyPreset = ref('BULL_CALL_SPREAD')
const payoffResult = ref<any>(null)

// Portfolio Risk state
const selectedRiskPortfolioId = ref('')
const riskResult = ref<any>(null)
const riskLoading = ref(false)

async function fetchPositions() {
  try {
    const res = await api.get('/options/positions')
    positions.value = res.data
  } catch (err) {
    console.error('Failed to load option positions', err)
  }
}

async function handleCreateOption() {
  try {
    await api.post('/options/positions', newPos.value)
    showNewOptionModal.value = false
    await fetchPositions()
  } catch (err) {
    console.error('Failed to open option position', err)
  }
}

async function handleCloseOption(id: string, action: string) {
  try {
    await api.post(`/options/positions/${id}/close`, {
      action,
      closing_premium: 0,
      fees: 0,
    })
    await fetchPositions()
  } catch (err) {
    console.error('Failed to close position', err)
  }
}

async function runOptionCalculator() {
  try {
    const res = await api.post('/options/analyze', calcInput.value)
    calcResult.value = res.data
  } catch (err) {
    console.error('Option analyzer error', err)
  }
}

async function runStrategyPayoff() {
  const spot = calcInput.value.spot_price
  let legs: any[] = []

  if (strategyPreset.value === 'LONG_CALL') {
    legs = [{ option_type: 'CALL', side: 'LONG', strike_price: spot + 5, premium: 7.5, contracts: 1, contract_multiplier: 100 }]
  } else if (strategyPreset.value === 'COVERED_CALL') {
    legs = [
      { option_type: 'STOCK', side: 'LONG', strike_price: spot, premium: 0, contracts: 100, contract_multiplier: 1 },
      { option_type: 'CALL', side: 'SHORT', strike_price: spot + 15, premium: 5.2, contracts: 1, contract_multiplier: 100 },
    ]
  } else if (strategyPreset.value === 'CASH_SECURED_PUT') {
    legs = [{ option_type: 'PUT', side: 'SHORT', strike_price: spot - 10, premium: 4.8, contracts: 1, contract_multiplier: 100 }]
  } else if (strategyPreset.value === 'BULL_CALL_SPREAD') {
    legs = [
      { option_type: 'CALL', side: 'LONG', strike_price: spot, premium: 9.0, contracts: 1, contract_multiplier: 100 },
      { option_type: 'CALL', side: 'SHORT', strike_price: spot + 20, premium: 3.5, contracts: 1, contract_multiplier: 100 },
    ]
  } else if (strategyPreset.value === 'LONG_STRADDLE') {
    legs = [
      { option_type: 'CALL', side: 'LONG', strike_price: spot, premium: 8.5, contracts: 1, contract_multiplier: 100 },
      { option_type: 'PUT', side: 'LONG', strike_price: spot, premium: 8.0, contracts: 1, contract_multiplier: 100 },
    ]
  }

  try {
    const res = await api.post('/options/strategy-payoff', {
      underlying_spot: spot,
      legs,
      price_range_pct: 0.30,
    })
    payoffResult.value = res.data
  } catch (err) {
    console.error('Strategy payoff error', err)
  }
}

const svgPolylinePoints = computed(() => {
  if (!payoffResult.value?.curve?.length) return ''
  const pts = payoffResult.value.curve as { underlying_price: number; pnl: number }[]
  const minX = pts[0].underlying_price
  const maxX = pts[pts.length - 1].underlying_price
  const pnls = pts.map(p => p.pnl)
  const minY = Math.min(...pnls, -100)
  const maxY = Math.max(...pnls, 100)
  const spanX = maxX - minX || 1
  const spanY = maxY - minY || 1

  return pts
    .map(p => {
      const x = ((p.underlying_price - minX) / spanX) * 560 + 20
      const y = 180 - ((p.pnl - minY) / spanY) * 150
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
})

const svgZeroLineY = computed(() => {
  if (!payoffResult.value?.curve?.length) return 105
  const pnls = payoffResult.value.curve.map((p: any) => p.pnl)
  const minY = Math.min(...pnls, -100)
  const maxY = Math.max(...pnls, 100)
  const spanY = maxY - minY || 1
  return 180 - ((0 - minY) / spanY) * 150
})

async function fetchPortfolioRisk() {
  if (!selectedRiskPortfolioId.value) return
  riskLoading.value = true
  try {
    const res = await api.get(`/risk/portfolio/${selectedRiskPortfolioId.value}`)
    riskResult.value = res.data
  } catch (err) {
    console.error('Risk fetch error', err)
  } finally {
    riskLoading.value = false
  }
}

onMounted(async () => {
  await Promise.all([
    fetchPositions(),
    runOptionCalculator(),
    runStrategyPayoff(),
    portfolioStore.fetchPortfolios(),
  ])
  if (portfolioStore.portfolios.length > 0) {
    selectedRiskPortfolioId.value = portfolioStore.portfolios[0].id
    await fetchPortfolioRisk()
  }
})
</script>

<template>
  <AppLayout>
    <div class="space-y-6 max-w-7xl mx-auto">
      <!-- Header -->
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Options Engine & Portfolio Risk</h1>
          <p class="text-sm text-slate-500 dark:text-slate-400">Zero-cost Python Black-Scholes/Binomial Greeks, strategy payoffs, and VaR stress testing</p>
        </div>

        <div class="flex items-center gap-2 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-1 rounded-xl">
          <button
            @click="activeTab = 'book'"
            class="px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5"
            :class="activeTab === 'book' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'"
          >
            <Layers class="w-3.5 h-3.5" />
            <span>Options Book</span>
          </button>
          <button
            @click="activeTab = 'lab'"
            class="px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5"
            :class="activeTab === 'lab' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'"
          >
            <Calculator class="w-3.5 h-3.5" />
            <span>Greeks & Payoff Lab</span>
          </button>
          <button
            @click="activeTab = 'risk'"
            class="px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5"
            :class="activeTab === 'risk' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'"
          >
            <ShieldAlert class="w-3.5 h-3.5" />
            <span>Portfolio Risk & VaR</span>
          </button>
        </div>
      </div>

      <!-- TAB 1: Options Book -->
      <div v-if="activeTab === 'book'" class="space-y-4">
        <div class="flex items-center justify-between bg-amber-500/10 border border-amber-500/20 rounded-xl p-4">
          <div class="flex items-center gap-3 text-xs text-amber-800 dark:text-amber-300">
            <AlertTriangle class="w-4 h-4 shrink-0 text-amber-600 dark:text-amber-400" />
            <span>
              <strong>Zero-Cost Quantitative Mode (Section 16.3):</strong> Contract fair values and Greeks are
              <code class="bg-amber-500/15 dark:bg-slate-900 px-1.5 py-0.5 rounded text-amber-900 dark:text-amber-200">MODEL_ESTIMATED</code> locally in Python using underlying equity prices and assumed IV without paid OPRA option feeds.
            </span>
          </div>
          <button
            @click="showNewOptionModal = true"
            class="shrink-0 inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium px-3.5 py-2 rounded-lg transition-colors"
          >
            <PlusCircle class="w-4 h-4" />
            <span>Log Contract</span>
          </button>
        </div>

        <div class="bg-card border border-border rounded-xl overflow-hidden shadow-sm">
          <table class="w-full text-left text-xs text-slate-700 dark:text-slate-300">
            <thead class="bg-slate-100/90 dark:bg-slate-900/60 uppercase font-bold text-slate-700 dark:text-slate-400 border-b border-border">
              <tr>
                <th class="px-5 py-3.5">Contract</th>
                <th class="px-5 py-3.5">Side / Style</th>
                <th class="px-5 py-3.5 text-right">Contracts (Mult)</th>
                <th class="px-5 py-3.5 text-right">Entry Prem</th>
                <th class="px-5 py-3.5 text-right">Model Fair Value</th>
                <th class="px-5 py-3.5 text-right">Delta / Theta</th>
                <th class="px-5 py-3.5 text-right">Est. P&L</th>
                <th class="px-5 py-3.5 text-right">Status / Action</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border/60 font-mono">
              <tr v-for="pos in positions" :key="pos.id" class="hover:bg-slate-50 dark:hover:bg-slate-800/30">
                <td class="px-5 py-3.5">
                  <div class="font-bold text-slate-900 dark:text-white">{{ pos.underlying_symbol }} ${{ pos.strike_price }} {{ pos.option_type }}</div>
                  <div class="text-[10px] text-slate-500 dark:text-slate-400">Exp: {{ pos.expiration_date }} &middot; {{ pos.strategy_tag }}</div>
                </td>
                <td class="px-5 py-3.5">
                  <span class="px-2 py-0.5 rounded text-[10px]" :class="pos.side === 'LONG' ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' : 'bg-rose-500/10 text-rose-600 dark:text-rose-400'">
                    {{ pos.side }}
                  </span>
                  <span class="ml-1 text-[10px] text-slate-500">{{ pos.exercise_style }}</span>
                </td>
                <td class="px-5 py-3.5 text-right">
                  {{ pos.contracts }} <span class="text-slate-500">(&times;{{ pos.contract_multiplier }})</span>
                </td>
                <td class="px-5 py-3.5 text-right">{{ formatCurrency(pos.entry_premium, pos.currency) }}</td>
                <td class="px-5 py-3.5 text-right">
                  <div v-if="pos.analytics">
                    <span class="text-blue-600 dark:text-blue-400 font-bold">{{ formatCurrency(pos.analytics.theoretical_price, pos.currency) }}</span>
                    <div class="text-[9px] text-slate-500">MODEL_ESTIMATED</div>
                  </div>
                  <span v-else class="text-slate-500">—</span>
                </td>
                <td class="px-5 py-3.5 text-right">
                  <div v-if="pos.analytics">
                    &Delta; {{ pos.analytics.greeks.delta }}<br />
                    <span class="text-[10px] text-rose-600 dark:text-rose-400">&Theta; {{ pos.analytics.greeks.theta_daily }}/d</span>
                  </div>
                  <span v-else class="text-slate-500">—</span>
                </td>
                <td class="px-5 py-3.5 text-right font-bold" :class="(pos.estimated_unrealized_pnl || 0) >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'">
                  {{ pos.estimated_unrealized_pnl !== null ? formatCurrency(pos.estimated_unrealized_pnl, pos.currency) : '—' }}
                </td>
                <td class="px-5 py-3.5 text-right">
                  <div v-if="pos.status === 'OPEN'" class="flex justify-end gap-1">
                    <button @click="handleCloseOption(pos.id, 'CLOSE')" class="px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-[10px]">Close</button>
                    <button @click="handleCloseOption(pos.id, 'EXPIRE')" class="px-2 py-1 rounded bg-slate-100 hover:bg-rose-500/15 dark:bg-slate-800 dark:hover:bg-rose-900/40 text-rose-600 dark:text-rose-400 text-[10px]">Expire</button>
                  </div>
                  <span v-else class="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 text-[10px]">{{ pos.status }}</span>
                </td>
              </tr>
              <tr v-if="positions.length === 0">
                <td colspan="8" class="px-6 py-12 text-center text-slate-500 font-sans">
                  No options contracts logged yet. Click "Log Contract" to track calls or puts.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- TAB 2: Greeks & Strategy Payoff Lab -->
      <div v-if="activeTab === 'lab'" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Single Contract Pricing & Greeks -->
        <div class="bg-card border border-border rounded-xl p-6 space-y-4 shadow-sm">
          <div class="flex items-center justify-between border-b border-border pb-3">
            <h2 class="text-sm font-bold text-slate-900 dark:text-white">Contract Pricing & Greeks Analyzer</h2>
            <span class="text-[10px] font-mono bg-blue-500/10 text-blue-600 dark:text-blue-400 px-2 py-0.5 rounded">Binomial / Black-Scholes</span>
          </div>

          <div class="grid grid-cols-3 gap-3 text-xs">
            <div>
              <label class="block text-slate-600 dark:text-slate-400 mb-1">Spot Price</label>
              <input v-model.number="calcInput.spot_price" @change="runOptionCalculator" type="number" step="1" class="w-full bg-slate-50 dark:bg-slate-900 border border-border rounded-lg px-2.5 py-1.5 text-slate-900 dark:text-white font-mono" />
            </div>
            <div>
              <label class="block text-slate-600 dark:text-slate-400 mb-1">Strike Price</label>
              <input v-model.number="calcInput.strike_price" @change="runOptionCalculator" type="number" step="1" class="w-full bg-slate-50 dark:bg-slate-900 border border-border rounded-lg px-2.5 py-1.5 text-slate-900 dark:text-white font-mono" />
            </div>
            <div>
              <label class="block text-slate-600 dark:text-slate-400 mb-1">Days to Expiry</label>
              <input v-model.number="calcInput.days_to_expiry" @change="runOptionCalculator" type="number" step="1" class="w-full bg-slate-50 dark:bg-slate-900 border border-border rounded-lg px-2.5 py-1.5 text-slate-900 dark:text-white font-mono" />
            </div>
            <div>
              <label class="block text-slate-600 dark:text-slate-400 mb-1">Implied Vol (IV)</label>
              <input v-model.number="calcInput.volatility" @change="runOptionCalculator" type="number" step="0.02" class="w-full bg-slate-50 dark:bg-slate-900 border border-border rounded-lg px-2.5 py-1.5 text-slate-900 dark:text-white font-mono" />
            </div>
            <div>
              <label class="block text-slate-600 dark:text-slate-400 mb-1">Type</label>
              <select v-model="calcInput.option_type" @change="runOptionCalculator" class="w-full bg-slate-50 dark:bg-slate-900 border border-border rounded-lg px-2.5 py-1.5 text-slate-900 dark:text-white">
                <option value="CALL">CALL</option>
                <option value="PUT">PUT</option>
              </select>
            </div>
            <div>
              <label class="block text-slate-600 dark:text-slate-400 mb-1">Style</label>
              <select v-model="calcInput.exercise_style" @change="runOptionCalculator" class="w-full bg-slate-50 dark:bg-slate-900 border border-border rounded-lg px-2.5 py-1.5 text-slate-900 dark:text-white">
                <option value="AMERICAN">AMERICAN</option>
                <option value="EUROPEAN">EUROPEAN</option>
              </select>
            </div>
          </div>

          <div v-if="calcResult" class="space-y-4 pt-2">
            <div class="grid grid-cols-3 gap-3">
              <div class="bg-slate-50 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-lg p-3">
                <span class="text-[10px] text-slate-500 dark:text-slate-400 uppercase">Fair Value</span>
                <p class="text-xl font-bold font-mono text-blue-600 dark:text-blue-400">${{ calcResult.theoretical_price }}</p>
                <span class="text-[9px] text-slate-500">{{ calcResult.pricing_model }}</span>
              </div>
              <div class="bg-slate-50 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-lg p-3">
                <span class="text-[10px] text-slate-500 dark:text-slate-400 uppercase">Prob. ITM</span>
                <p class="text-xl font-bold font-mono text-emerald-600 dark:text-emerald-400">{{ calcResult.prob_itm_pct }}%</p>
                <span class="text-[9px] text-slate-500">Break-even: ${{ calcResult.break_even_price }}</span>
              </div>
              <div class="bg-slate-50 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-lg p-3">
                <span class="text-[10px] text-slate-500 dark:text-slate-400 uppercase">Intrinsic / Time</span>
                <p class="text-sm font-bold font-mono text-slate-900 dark:text-white mt-1">${{ calcResult.intrinsic_value }} / ${{ calcResult.extrinsic_value }}</p>
              </div>
            </div>

            <div class="grid grid-cols-5 gap-2 text-center font-mono text-xs">
              <div class="bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-lg p-2">
                <div class="text-[10px] text-slate-500 dark:text-slate-400">Delta (&Delta;)</div>
                <div class="font-bold text-slate-900 dark:text-white mt-0.5">{{ calcResult.greeks.delta }}</div>
              </div>
              <div class="bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-lg p-2">
                <div class="text-[10px] text-slate-500 dark:text-slate-400">Gamma (&Gamma;)</div>
                <div class="font-bold text-slate-900 dark:text-white mt-0.5">{{ calcResult.greeks.gamma }}</div>
              </div>
              <div class="bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-lg p-2">
                <div class="text-[10px] text-slate-500 dark:text-slate-400">Theta (&Theta;/d)</div>
                <div class="font-bold text-rose-600 dark:text-rose-400 mt-0.5">{{ calcResult.greeks.theta_daily }}</div>
              </div>
              <div class="bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-lg p-2">
                <div class="text-[10px] text-slate-500 dark:text-slate-400">Vega (&nu;)</div>
                <div class="font-bold text-blue-600 dark:text-blue-400 mt-0.5">{{ calcResult.greeks.vega_per_pct }}</div>
              </div>
              <div class="bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-lg p-2">
                <div class="text-[10px] text-slate-500 dark:text-slate-400">Rho (&rho;)</div>
                <div class="font-bold text-slate-700 dark:text-slate-300 mt-0.5">{{ calcResult.greeks.rho_per_pct }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Strategy Payoff Diagram -->
        <div class="bg-card border border-border rounded-xl p-6 space-y-4 shadow-sm">
          <div class="flex items-center justify-between border-b border-border pb-3">
            <h2 class="text-sm font-bold text-slate-900 dark:text-white">Strategy Expiration Payoff Diagram</h2>
            <select v-model="strategyPreset" @change="runStrategyPayoff" class="bg-slate-50 dark:bg-slate-900 border border-border rounded-lg px-2.5 py-1 text-xs text-slate-900 dark:text-white">
              <option value="LONG_CALL">Long Call</option>
              <option value="COVERED_CALL">Covered Call</option>
              <option value="CASH_SECURED_PUT">Cash-Secured Put</option>
              <option value="BULL_CALL_SPREAD">Bull Call Spread</option>
              <option value="LONG_STRADDLE">Long Straddle</option>
            </select>
          </div>

          <div v-if="payoffResult" class="space-y-4">
            <div class="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl p-3">
              <svg viewBox="0 0 600 200" class="w-full h-48 overflow-visible">
                <!-- Zero P&L Reference Line -->
                <line x1="20" :y1="svgZeroLineY" x2="580" :y2="svgZeroLineY" class="stroke-slate-300 dark:stroke-slate-700" stroke-dasharray="4 4" stroke-width="1" />
                <!-- Payoff Curve -->
                <polyline fill="none" stroke="#3b82f6" stroke-width="2.5" :points="svgPolylinePoints" />
              </svg>
            </div>

            <div class="grid grid-cols-3 gap-3 text-xs font-mono">
              <div class="bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-lg p-3">
                <span class="text-[10px] text-slate-500 dark:text-slate-400">Max Profit</span>
                <p class="font-bold text-emerald-600 dark:text-emerald-400 mt-0.5">
                  {{ payoffResult.max_profit !== null ? `$${payoffResult.max_profit}` : 'Unlimited' }}
                </p>
              </div>
              <div class="bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-lg p-3">
                <span class="text-[10px] text-slate-500 dark:text-slate-400">Max Loss</span>
                <p class="font-bold text-rose-600 dark:text-rose-400 mt-0.5">
                  {{ payoffResult.max_loss !== null ? `$${payoffResult.max_loss}` : 'Unlimited' }}
                </p>
              </div>
              <div class="bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-lg p-3">
                <span class="text-[10px] text-slate-500 dark:text-slate-400">Break-Even(s)</span>
                <p class="font-bold text-slate-900 dark:text-white mt-0.5">
                  {{ payoffResult.break_even_prices.length ? payoffResult.break_even_prices.map((b: number) => `$${b}`).join(', ') : '—' }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- TAB 3: Portfolio Risk & Stress Testing -->
      <div v-if="activeTab === 'risk'" class="space-y-6">
        <div class="bg-card border border-border rounded-xl p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-sm">
          <div class="flex items-center gap-3">
            <label class="text-xs font-medium text-slate-700 dark:text-slate-300">Select Portfolio:</label>
            <select v-model="selectedRiskPortfolioId" @change="fetchPortfolioRisk" class="bg-slate-50 dark:bg-slate-900 border border-border rounded-lg px-3 py-1.5 text-xs text-slate-900 dark:text-white">
              <option v-for="p in portfolioStore.portfolios" :key="p.id" :value="p.id">{{ p.name }} ({{ p.reporting_currency }})</option>
            </select>
          </div>
          <div v-if="riskResult" class="text-[11px] font-mono text-slate-500 dark:text-slate-400 flex items-center gap-2">
            <span class="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-blue-600 dark:text-blue-400">{{ riskResult.estimation_status }}</span>
            <span>{{ riskResult.data_completeness_note }}</span>
          </div>
        </div>

        <div v-if="riskLoading" class="bg-card border border-border rounded-xl p-8 text-center text-xs text-slate-500 dark:text-slate-400">
          Calculating portfolio risk metrics and stress tests...
        </div>

        <div v-else-if="riskResult" class="space-y-6">
          <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div class="bg-card border border-border rounded-xl p-4 shadow-sm">
              <span class="text-[10px] text-slate-500 dark:text-slate-400 uppercase font-semibold">Annual Volatility</span>
              <p class="text-xl font-bold font-mono text-amber-600 dark:text-amber-400 mt-1">{{ riskResult.annualized_volatility_pct ?? '—' }}%</p>
            </div>
            <div class="bg-card border border-border rounded-xl p-4 shadow-sm">
              <span class="text-[10px] text-slate-500 dark:text-slate-400 uppercase font-semibold">Sharpe / Sortino</span>
              <p class="text-xl font-bold font-mono text-emerald-600 dark:text-emerald-400 mt-1">{{ riskResult.sharpe_ratio ?? '—' }} / {{ riskResult.sortino_ratio ?? '—' }}</p>
            </div>
            <div class="bg-card border border-border rounded-xl p-4 shadow-sm">
              <span class="text-[10px] text-slate-500 dark:text-slate-400 uppercase font-semibold">Max Drawdown Est.</span>
              <p class="text-xl font-bold font-mono text-rose-600 dark:text-rose-400 mt-1">{{ riskResult.max_drawdown_pct ?? '—' }}%</p>
            </div>
            <div class="bg-card border border-border rounded-xl p-4 shadow-sm">
              <span class="text-[10px] text-slate-500 dark:text-slate-400 uppercase font-semibold">Daily VaR (95%)</span>
              <p class="text-xl font-bold font-mono text-rose-600 dark:text-rose-400 mt-1">
                {{ riskResult.var_95_daily_amount !== null ? formatCurrency(riskResult.var_95_daily_amount, riskResult.reporting_currency) : '—' }}
              </p>
            </div>
            <div class="bg-card border border-border rounded-xl p-4 shadow-sm">
              <span class="text-[10px] text-slate-500 dark:text-slate-400 uppercase font-semibold">Concentration HHI</span>
              <p class="text-xl font-bold font-mono text-blue-600 dark:text-blue-400 mt-1">{{ riskResult.concentration_hhi }}</p>
              <span class="text-[9px] text-slate-500">{{ riskResult.concentration_hhi > 2500 ? 'High Concentration' : 'Diversified' }}</span>
            </div>
          </div>

          <!-- Stress Tests Table -->
          <div class="bg-card border border-border rounded-xl overflow-hidden shadow-sm">
            <div class="px-6 py-4 border-b border-border flex items-center justify-between">
              <h3 class="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <Activity class="w-4 h-4 text-rose-600 dark:text-rose-400" />
                <span>Market & Currency Stress Testing</span>
              </h3>
            </div>
            <table class="w-full text-left text-xs text-slate-700 dark:text-slate-300">
              <thead class="bg-slate-100/90 dark:bg-slate-900/60 uppercase font-bold text-slate-700 dark:text-slate-400 border-b border-border">
                <tr>
                  <th class="px-6 py-3">Scenario</th>
                  <th class="px-6 py-3">Shock Assumption</th>
                  <th class="px-6 py-3 text-right">Projected Value</th>
                  <th class="px-6 py-3 text-right">Impact</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border/60 font-mono">
                <tr v-for="st in riskResult.stress_tests" :key="st.scenario_name" class="hover:bg-slate-50 dark:hover:bg-slate-800/30">
                  <td class="px-6 py-3 font-sans font-semibold text-slate-900 dark:text-white">{{ st.scenario_name }}</td>
                  <td class="px-6 py-3 font-sans text-slate-500 dark:text-slate-400">{{ st.shock_description }}</td>
                  <td class="px-6 py-3 text-right text-slate-900 dark:text-white font-bold">{{ formatCurrency(st.estimated_portfolio_value, riskResult.reporting_currency) }}</td>
                  <td class="px-6 py-3 text-right font-bold" :class="st.estimated_pnl_impact >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'">
                    {{ formatCurrency(st.estimated_pnl_impact, riskResult.reporting_currency) }} ({{ st.estimated_impact_pct }}%)
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Log New Option Modal -->
      <div v-if="showNewOptionModal" class="fixed inset-0 bg-black/50 dark:bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div class="bg-card border border-border rounded-xl w-full max-w-lg p-6 space-y-4 shadow-2xl">
          <div class="flex items-center justify-between border-b border-border pb-3">
            <h3 class="font-bold text-slate-900 dark:text-white text-base">Log Options Contract</h3>
            <button @click="showNewOptionModal = false" class="text-slate-400 hover:text-slate-700 dark:hover:text-white">&times;</button>
          </div>
          <form @submit.prevent="handleCreateOption" class="space-y-4 text-xs">
            <div class="grid grid-cols-3 gap-3">
              <div>
                <label class="block text-slate-700 dark:text-slate-300 mb-1">Underlying</label>
                <input v-model="newPos.underlying_symbol" required class="w-full bg-slate-50 dark:bg-slate-900 border border-border rounded-lg px-3 py-2 text-slate-900 dark:text-white font-mono" />
              </div>
              <div>
                <label class="block text-slate-700 dark:text-slate-300 mb-1">Type</label>
                <select v-model="newPos.option_type" class="w-full bg-slate-50 dark:bg-slate-900 border border-border rounded-lg px-3 py-2 text-slate-900 dark:text-white">
                  <option value="CALL">CALL</option>
                  <option value="PUT">PUT</option>
                </select>
              </div>
              <div>
                <label class="block text-slate-700 dark:text-slate-300 mb-1">Side</label>
                <select v-model="newPos.side" class="w-full bg-slate-50 dark:bg-slate-900 border border-border rounded-lg px-3 py-2 text-slate-900 dark:text-white">
                  <option value="LONG">LONG</option>
                  <option value="SHORT">SHORT</option>
                </select>
              </div>
            </div>
            <div class="grid grid-cols-3 gap-3">
              <div>
                <label class="block text-slate-700 dark:text-slate-300 mb-1">Strike Price</label>
                <input v-model.number="newPos.strike_price" type="number" step="0.5" required class="w-full bg-slate-50 dark:bg-slate-900 border border-border rounded-lg px-3 py-2 text-slate-900 dark:text-white font-mono" />
              </div>
              <div>
                <label class="block text-slate-700 dark:text-slate-300 mb-1">Expiration Date</label>
                <input v-model="newPos.expiration_date" type="date" required class="w-full bg-slate-50 dark:bg-slate-900 border border-border rounded-lg px-3 py-2 text-slate-900 dark:text-white" />
              </div>
              <div>
                <label class="block text-slate-700 dark:text-slate-300 mb-1">Contracts</label>
                <input v-model.number="newPos.contracts" type="number" min="1" required class="w-full bg-slate-50 dark:bg-slate-900 border border-border rounded-lg px-3 py-2 text-slate-900 dark:text-white font-mono" />
              </div>
            </div>
            <div class="grid grid-cols-3 gap-3">
              <div>
                <label class="block text-slate-700 dark:text-slate-300 mb-1">Entry Premium</label>
                <input v-model.number="newPos.entry_premium" type="number" step="0.01" required class="w-full bg-slate-50 dark:bg-slate-900 border border-border rounded-lg px-3 py-2 text-slate-900 dark:text-white font-mono" />
              </div>
              <div>
                <label class="block text-slate-700 dark:text-slate-300 mb-1">Multiplier</label>
                <input v-model.number="newPos.contract_multiplier" type="number" min="1" required class="w-full bg-slate-50 dark:bg-slate-900 border border-border rounded-lg px-3 py-2 text-slate-900 dark:text-white font-mono" />
              </div>
              <div>
                <label class="block text-slate-700 dark:text-slate-300 mb-1">Assumed IV</label>
                <input v-model.number="newPos.assumed_volatility" type="number" step="0.01" required class="w-full bg-slate-50 dark:bg-slate-900 border border-border rounded-lg px-3 py-2 text-slate-900 dark:text-white font-mono" />
              </div>
            </div>
            <div class="flex justify-end gap-3 pt-4 border-t border-border">
              <button @click="showNewOptionModal = false" type="button" class="px-4 py-2 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white">Cancel</button>
              <button type="submit" class="bg-blue-600 hover:bg-blue-500 text-white font-medium px-4 py-2 rounded-lg">Open Position</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
