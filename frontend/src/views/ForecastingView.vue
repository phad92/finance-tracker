<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { TrendingUp, Target, Sliders, Activity, Sparkles, BarChart3 } from 'lucide-vue-next'
import AppLayout from '@/components/layout/AppLayout.vue'
import api from '@/services/api'
import { formatCurrency, formatPercent } from '@/lib/utils'

const forecastTab = ref<'deterministic' | 'montecarlo' | 'goals'>('deterministic')

// Deterministic Simulation Inputs
const initialAmount = ref(10000)
const monthlyContribution = ref(1000)
const annualReturnRate = ref(0.18) // 18%
const investmentYears = ref(10)
const inflationRate = ref(0.12)
const contributionGrowthRate = ref(0.05)
const simulationResult = ref<any>(null)
const loading = ref(false)

// Monte Carlo Inputs
const mcInitial = ref(10000)
const mcMonthly = ref(1000)
const mcReturn = ref(0.18)
const mcVol = ref(0.16) // 16% volatility
const mcYears = ref(10)
const mcSimulations = ref(1000)
const mcGoal = ref(500000)
const mcResult = ref<any>(null)
const mcLoading = ref(false)

// Goal Solver Inputs
const goalTarget = ref(500000)
const goalCurrent = ref(10000)
const goalYears = ref(5)
const goalReturn = ref(0.18)
const goalInflation = ref(0.12)
const goalResult = ref<any>(null)

async function runDeterministic() {
  loading.value = true
  try {
    const res = await api.post('/forecasting/simulate', {
      initial_amount: initialAmount.value,
      monthly_contribution: monthlyContribution.value,
      annual_return_rate: annualReturnRate.value,
      investment_years: investmentYears.value,
      inflation_rate: inflationRate.value,
      contribution_growth_rate: contributionGrowthRate.value,
    })
    simulationResult.value = res.data
  } catch (err) {
    console.error('Simulation error', err)
  } finally {
    loading.value = false
  }
}

async function runMonteCarlo() {
  mcLoading.value = true
  try {
    const res = await api.post('/forecasting/monte-carlo', {
      initial_amount: mcInitial.value,
      monthly_contribution: mcMonthly.value,
      expected_annual_return: mcReturn.value,
      annual_volatility: mcVol.value,
      investment_years: mcYears.value,
      num_simulations: mcSimulations.value,
      target_wealth_goal: mcGoal.value,
    })
    mcResult.value = res.data
  } catch (err) {
    console.error('Monte Carlo error', err)
  } finally {
    mcLoading.value = false
  }
}

async function solveGoal() {
  try {
    const res = await api.post('/forecasting/goal-savings', {
      target_amount: goalTarget.value,
      current_amount: goalCurrent.value,
      target_years: goalYears.value,
      expected_annual_return: goalReturn.value,
      inflation_rate: goalInflation.value,
    })
    goalResult.value = res.data
  } catch (err) {
    console.error('Goal solver error', err)
  }
}

onMounted(async () => {
  await Promise.all([
    runDeterministic(),
    runMonteCarlo(),
    solveGoal(),
  ])
})
</script>

<template>
  <AppLayout>
    <div class="space-y-6 max-w-7xl mx-auto">
      <!-- Header -->
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Forecasting & Wealth Modeling</h1>
          <p class="text-sm text-slate-500 dark:text-slate-400">Deterministic compounding, Monte Carlo volatility cones, and goal reverse solvers</p>
        </div>

        <!-- Mode Toggle Tabs -->
        <div class="flex items-center gap-2 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-1 rounded-xl">
          <button
            @click="forecastTab = 'deterministic'"
            class="px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5"
            :class="forecastTab === 'deterministic' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'"
          >
            <TrendingUp class="w-3.5 h-3.5" />
            <span>Compound Growth</span>
          </button>
          <button
            @click="forecastTab = 'montecarlo'"
            class="px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5"
            :class="forecastTab === 'montecarlo' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'"
          >
            <Activity class="w-3.5 h-3.5" />
            <span>Monte Carlo (1,000 Paths)</span>
          </button>
          <button
            @click="forecastTab = 'goals'"
            class="px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5"
            :class="forecastTab === 'goals' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'"
          >
            <Target class="w-3.5 h-3.5" />
            <span>Goal Reverse Solver</span>
          </button>
        </div>
      </div>

      <!-- TAB 1: Deterministic Compound Growth -->
      <div v-if="forecastTab === 'deterministic'" class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <!-- Controls Panel -->
        <div class="bg-card border border-border rounded-xl p-6 space-y-5 h-fit shadow-sm">
          <div class="flex items-center gap-2 border-b border-border pb-3">
            <Sliders class="w-4 h-4 text-blue-600 dark:text-blue-400" />
            <h2 class="font-bold text-sm text-slate-900 dark:text-white">Compound Assumptions</h2>
          </div>

          <div>
            <label class="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Initial Principal (GH₵)</label>
            <input v-model.number="initialAmount" type="number" step="1000" class="w-full bg-slate-50 dark:bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-slate-900 dark:text-white font-mono" />
          </div>

          <div>
            <label class="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Monthly Contribution (GH₵)</label>
            <input v-model.number="monthlyContribution" type="number" step="100" class="w-full bg-slate-50 dark:bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-slate-900 dark:text-white font-mono" />
          </div>

          <div>
            <div class="flex justify-between text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              <span>Expected Annual Return</span>
              <span class="text-blue-600 dark:text-blue-400 font-mono">{{ formatPercent(annualReturnRate) }}</span>
            </div>
            <input v-model.number="annualReturnRate" type="range" min="0.05" max="0.35" step="0.01" class="w-full accent-blue-600" />
          </div>

          <div>
            <div class="flex justify-between text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              <span>Time Horizon (Years)</span>
              <span class="text-blue-600 dark:text-blue-400 font-mono">{{ investmentYears }} Years</span>
            </div>
            <input v-model.number="investmentYears" type="range" min="1" max="40" step="1" class="w-full accent-blue-600" />
          </div>

          <div>
            <div class="flex justify-between text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              <span>Inflation Rate</span>
              <span class="text-rose-600 dark:text-rose-400 font-mono">{{ formatPercent(inflationRate) }}</span>
            </div>
            <input v-model.number="inflationRate" type="range" min="0.02" max="0.30" step="0.01" class="w-full accent-rose-600" />
          </div>

          <button
            @click="runDeterministic"
            :disabled="loading"
            class="w-full bg-blue-600 hover:bg-blue-500 text-white font-medium py-2.5 rounded-lg text-xs shadow-md shadow-blue-600/20 transition-colors flex items-center justify-center gap-2"
          >
            <TrendingUp class="w-4 h-4" />
            <span>Recalculate</span>
          </button>
        </div>

        <!-- Outputs -->
        <div class="lg:col-span-2 space-y-6">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4" v-if="simulationResult">
            <div class="bg-card border border-border rounded-xl p-5 shadow-sm">
              <span class="text-xs text-slate-500 dark:text-slate-400 uppercase font-semibold">Future Nominal Wealth</span>
              <p class="text-2xl font-bold font-mono text-emerald-600 dark:text-emerald-400 mt-1">
                {{ formatCurrency(simulationResult.final_nominal_wealth) }}
              </p>
              <span class="text-[10px] text-slate-500 font-mono">Future paper balance</span>
            </div>

            <div class="bg-card border border-border rounded-xl p-5 shadow-sm">
              <span class="text-xs text-slate-500 dark:text-slate-400 uppercase font-semibold">Real Purchasing Power</span>
              <p class="text-2xl font-bold font-mono text-blue-600 dark:text-blue-400 mt-1">
                {{ formatCurrency(simulationResult.final_real_wealth) }}
              </p>
              <span class="text-[10px] text-slate-500 font-mono">In today's money</span>
            </div>

            <div class="bg-card border border-border rounded-xl p-5 shadow-sm">
              <span class="text-xs text-slate-500 dark:text-slate-400 uppercase font-semibold">Investment Gains</span>
              <p class="text-2xl font-bold font-mono text-slate-900 dark:text-white mt-1">
                {{ formatCurrency(simulationResult.total_investment_gains) }}
              </p>
              <span class="text-[10px] text-slate-500 font-mono">Compound interest</span>
            </div>
          </div>

          <div class="bg-card border border-border rounded-xl overflow-hidden shadow-sm" v-if="simulationResult">
            <div class="px-6 py-4 border-b border-border flex items-center justify-between">
              <h3 class="font-bold text-sm text-slate-900 dark:text-white">Compounding Trajectory</h3>
              <span class="text-xs text-slate-500 dark:text-slate-400 font-mono">All figures in GHS</span>
            </div>
            <div class="max-h-96 overflow-y-auto">
              <table class="w-full text-left text-sm text-slate-700 dark:text-slate-300">
                <thead class="bg-slate-100/90 dark:bg-slate-900/60 text-xs uppercase font-bold text-slate-700 dark:text-slate-400 sticky top-0 border-b border-border">
                  <tr>
                    <th class="px-6 py-3">Year</th>
                    <th class="px-6 py-3 text-right">Contributions</th>
                    <th class="px-6 py-3 text-right">Nominal Value</th>
                    <th class="px-6 py-3 text-right">Real Value (Inflation Adj.)</th>
                    <th class="px-6 py-3 text-right">Interest Gained</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-border/60">
                  <tr v-for="pt in simulationResult.yearly_trajectory" :key="pt.year" class="hover:bg-slate-50 dark:hover:bg-slate-800/30 font-mono text-xs">
                    <td class="px-6 py-3 font-bold text-slate-900 dark:text-white">Year {{ pt.year }}</td>
                    <td class="px-6 py-3 text-right text-slate-500 dark:text-slate-400">{{ formatCurrency(pt.total_contributions) }}</td>
                    <td class="px-6 py-3 text-right font-bold text-emerald-600 dark:text-emerald-400">{{ formatCurrency(pt.nominal_wealth) }}</td>
                    <td class="px-6 py-3 text-right font-medium text-blue-600 dark:text-blue-400">{{ formatCurrency(pt.real_wealth_inflation_adjusted) }}</td>
                    <td class="px-6 py-3 text-right text-slate-800 dark:text-slate-200">{{ formatCurrency(pt.total_investment_gains) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <!-- TAB 2: Monte Carlo Simulation -->
      <div v-if="forecastTab === 'montecarlo'" class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div class="bg-card border border-border rounded-xl p-6 space-y-5 h-fit shadow-sm">
          <div class="flex items-center gap-2 border-b border-border pb-3">
            <Activity class="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <h2 class="font-bold text-sm text-slate-900 dark:text-white">Stochastic Parameters</h2>
          </div>

          <div>
            <label class="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Initial Capital (GH₵)</label>
            <input v-model.number="mcInitial" type="number" step="1000" class="w-full bg-slate-50 dark:bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-slate-900 dark:text-white font-mono" />
          </div>

          <div>
            <label class="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Monthly Savings (GH₵)</label>
            <input v-model.number="mcMonthly" type="number" step="100" class="w-full bg-slate-50 dark:bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-slate-900 dark:text-white font-mono" />
          </div>

          <div>
            <div class="flex justify-between text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              <span>Mean Return (&mu;)</span>
              <span class="text-emerald-600 dark:text-emerald-400 font-mono">{{ formatPercent(mcReturn) }}</span>
            </div>
            <input v-model.number="mcReturn" type="range" min="0.05" max="0.30" step="0.01" class="w-full accent-emerald-600" />
          </div>

          <div>
            <div class="flex justify-between text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              <span>Annual Volatility (&sigma;)</span>
              <span class="text-amber-600 dark:text-amber-400 font-mono">{{ formatPercent(mcVol) }}</span>
            </div>
            <input v-model.number="mcVol" type="range" min="0.05" max="0.40" step="0.01" class="w-full accent-amber-600" />
          </div>

          <div>
            <label class="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Target Wealth Goal (GH₵)</label>
            <input v-model.number="mcGoal" type="number" step="50000" class="w-full bg-slate-50 dark:bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-slate-900 dark:text-white font-mono" />
          </div>

          <button
            @click="runMonteCarlo"
            :disabled="mcLoading"
            class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-medium py-2.5 rounded-lg text-xs shadow-md shadow-emerald-600/20 transition-colors flex items-center justify-center gap-2"
          >
            <Activity class="w-4 h-4" />
            <span>{{ mcLoading ? 'Running 1,000 Paths...' : 'Run Simulation' }}</span>
          </button>
        </div>

        <div class="lg:col-span-2 space-y-6">
          <!-- Probability Card -->
          <div v-if="mcResult" class="bg-gradient-to-r from-blue-500/10 to-emerald-500/10 dark:from-blue-900/30 dark:to-emerald-900/30 border border-blue-500/30 rounded-xl p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div>
              <span class="text-xs uppercase font-bold text-blue-600 dark:text-blue-400 tracking-wider">Goal Attainment Probability</span>
              <p class="text-sm text-slate-700 dark:text-slate-300 mt-1">
                Chance of reaching <span class="font-mono font-bold text-slate-900 dark:text-white">{{ formatCurrency(mcResult.target_wealth_goal) }}</span> across 1,000 simulated market cycles:
              </p>
            </div>
            <div class="text-right">
              <span class="text-4xl font-bold font-mono text-emerald-600 dark:text-emerald-400">
                {{ mcResult.probability_of_reaching_goal }}%
              </span>
              <p class="text-[10px] text-slate-500 dark:text-slate-400 font-mono">Success Rate</p>
            </div>
          </div>

          <!-- Percentiles Table -->
          <div class="bg-card border border-border rounded-xl overflow-hidden shadow-sm" v-if="mcResult">
            <div class="px-6 py-4 border-b border-border flex items-center justify-between">
              <h3 class="font-bold text-sm text-slate-900 dark:text-white">Probabilistic Percentile Cones</h3>
              <span class="text-xs text-slate-500 dark:text-slate-400 font-mono">5th to 95th Percentile Bounds</span>
            </div>
            <div class="max-h-96 overflow-y-auto">
              <table class="w-full text-left text-sm text-slate-700 dark:text-slate-300">
                <thead class="bg-slate-100/90 dark:bg-slate-900/60 text-xs uppercase font-bold text-slate-700 dark:text-slate-400 sticky top-0 border-b border-border">
                  <tr>
                    <th class="px-6 py-3">Year</th>
                    <th class="px-6 py-3 text-right text-rose-600 dark:text-rose-400">5th % (Bear)</th>
                    <th class="px-6 py-3 text-right text-slate-600 dark:text-slate-300">25th %</th>
                    <th class="px-6 py-3 text-right text-blue-600 dark:text-blue-400 font-bold">50th % (Median)</th>
                    <th class="px-6 py-3 text-right text-slate-600 dark:text-slate-300">75th %</th>
                    <th class="px-6 py-3 text-right text-emerald-600 dark:text-emerald-400">95th % (Bull)</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-border/60">
                  <tr v-for="pt in mcResult.trajectory" :key="pt.year" class="hover:bg-slate-50 dark:hover:bg-slate-800/30 font-mono text-xs">
                    <td class="px-6 py-3 font-bold text-slate-900 dark:text-white">Year {{ pt.year }}</td>
                    <td class="px-6 py-3 text-right text-rose-600 dark:text-rose-400">{{ formatCurrency(pt.percentiles.p5) }}</td>
                    <td class="px-6 py-3 text-right text-slate-500 dark:text-slate-400">{{ formatCurrency(pt.percentiles.p25) }}</td>
                    <td class="px-6 py-3 text-right text-blue-600 dark:text-blue-400 font-bold">{{ formatCurrency(pt.percentiles.p50) }}</td>
                    <td class="px-6 py-3 text-right text-slate-700 dark:text-slate-300">{{ formatCurrency(pt.percentiles.p75) }}</td>
                    <td class="px-6 py-3 text-right text-emerald-600 dark:text-emerald-400 font-bold">{{ formatCurrency(pt.percentiles.p95) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <!-- TAB 3: Goal Reverse Solver -->
      <div v-if="forecastTab === 'goals'" class="bg-card border border-border rounded-xl p-8 max-w-3xl mx-auto shadow-sm space-y-6">
        <div class="flex items-center gap-2 border-b border-border pb-4">
          <Target class="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
          <div>
            <h2 class="text-base font-bold text-slate-900 dark:text-white">Financial Goal Reverse Solver</h2>
            <p class="text-xs text-slate-500 dark:text-slate-400">Calculate exact required monthly savings using ordinary annuity future-value formulas</p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label class="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Target Amount (GH₵)</label>
            <input v-model.number="goalTarget" @change="solveGoal" type="number" step="10000" class="w-full bg-slate-50 dark:bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-slate-900 dark:text-white font-mono" />
          </div>
          <div>
            <label class="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Current Principal (GH₵)</label>
            <input v-model.number="goalCurrent" @change="solveGoal" type="number" step="1000" class="w-full bg-slate-50 dark:bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-slate-900 dark:text-white font-mono" />
          </div>
          <div>
            <label class="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Target Horizon (Years)</label>
            <input v-model.number="goalYears" @change="solveGoal" type="number" step="1" class="w-full bg-slate-50 dark:bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-slate-900 dark:text-white font-mono" />
          </div>
          <div>
            <label class="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Expected Return</label>
            <input v-model.number="goalReturn" @change="solveGoal" type="number" step="0.01" class="w-full bg-slate-50 dark:bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-slate-900 dark:text-white font-mono" />
          </div>
        </div>

        <div v-if="goalResult" class="p-6 bg-slate-50 dark:bg-slate-900/90 border border-slate-200 dark:border-slate-800 rounded-xl space-y-4">
          <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
            <div>
              <span class="text-xs text-slate-500 dark:text-slate-400">Required Monthly Contribution:</span>
              <p class="text-3xl font-bold font-mono text-emerald-600 dark:text-emerald-400">
                {{ formatCurrency(goalResult.required_monthly_savings_nominal) }} <span class="text-xs text-slate-500 dark:text-slate-400 font-normal">/ month</span>
              </p>
            </div>
            <div class="md:text-right">
              <span class="text-xs text-slate-500 dark:text-slate-400">Inflation-Protected Contribution:</span>
              <p class="text-xl font-bold font-mono text-blue-600 dark:text-blue-400">
                {{ formatCurrency(goalResult.required_monthly_savings_inflation_adjusted) }} <span class="text-xs text-slate-500 dark:text-slate-400 font-normal">/ month</span>
              </p>
            </div>
          </div>
          <div class="grid grid-cols-2 text-xs font-mono text-slate-500 dark:text-slate-400">
            <div>Total Out-of-Pocket: <span class="text-slate-800 dark:text-slate-200">{{ formatCurrency(goalResult.projected_total_contributed) }}</span></div>
            <div class="text-right">Compounded Gains: <span class="text-emerald-600 dark:text-emerald-400">{{ formatCurrency(goalResult.projected_total_growth) }}</span></div>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
