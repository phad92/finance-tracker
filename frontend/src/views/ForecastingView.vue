<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { TrendingUp, Target, Sliders, ArrowUpRight } from 'lucide-vue-next'
import AppLayout from '@/components/layout/AppLayout.vue'
import api from '@/services/api'
import { formatCurrency, formatPercent } from '@/lib/utils'

// Simulation Inputs
const initialAmount = ref(10000)
const monthlyContribution = ref(1000)
const annualReturnRate = ref(0.18) // 18% typical emerging market / balanced portfolio
const investmentYears = ref(10)
const inflationRate = ref(0.12) // 12% inflation
const contributionGrowthRate = ref(0.05) // 5% annual step-up

// Simulation Results
const simulationResult = ref<any>(null)
const loading = ref(false)

// Goal Solver Inputs
const goalTarget = ref(500000)
const goalCurrent = ref(10000)
const goalYears = ref(5)
const goalReturn = ref(0.18)
const goalInflation = ref(0.12)
const goalResult = ref<any>(null)

async function runSimulation() {
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
  await runSimulation()
  await solveGoal()
})
</script>

<template>
  <AppLayout>
    <div class="space-y-8 max-w-7xl mx-auto">
      <!-- Header -->
      <div>
        <h1 class="text-2xl font-bold text-white tracking-tight">Financial Forecasting & Wealth Projection</h1>
        <p class="text-sm text-slate-400">Model long-term wealth trajectories, inflation-adjusted purchasing power, and target goals</p>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <!-- Controls Panel -->
        <div class="bg-card border border-border rounded-xl p-6 space-y-5 h-fit shadow-sm">
          <div class="flex items-center gap-2 border-b border-border pb-3">
            <Sliders class="w-4 h-4 text-blue-400" />
            <h2 class="font-bold text-sm text-white">Projection Assumptions</h2>
          </div>

          <div>
            <label class="block text-xs font-medium text-slate-300 mb-1">Initial Principal (GH₵)</label>
            <input v-model.number="initialAmount" type="number" step="1000" class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-white font-mono" />
          </div>

          <div>
            <label class="block text-xs font-medium text-slate-300 mb-1">Monthly Contribution (GH₵)</label>
            <input v-model.number="monthlyContribution" type="number" step="100" class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-white font-mono" />
          </div>

          <div>
            <div class="flex justify-between text-xs font-medium text-slate-300 mb-1">
              <span>Expected Annual Return</span>
              <span class="text-blue-400 font-mono">{{ formatPercent(annualReturnRate) }}</span>
            </div>
            <input v-model.number="annualReturnRate" type="range" min="0.05" max="0.35" step="0.01" class="w-full accent-blue-600" />
          </div>

          <div>
            <div class="flex justify-between text-xs font-medium text-slate-300 mb-1">
              <span>Time Horizon (Years)</span>
              <span class="text-blue-400 font-mono">{{ investmentYears }} Years</span>
            </div>
            <input v-model.number="investmentYears" type="range" min="1" max="40" step="1" class="w-full accent-blue-600" />
          </div>

          <div>
            <div class="flex justify-between text-xs font-medium text-slate-300 mb-1">
              <span>Inflation Rate Assumption</span>
              <span class="text-rose-400 font-mono">{{ formatPercent(inflationRate) }}</span>
            </div>
            <input v-model.number="inflationRate" type="range" min="0.02" max="0.30" step="0.01" class="w-full accent-rose-600" />
          </div>

          <button
            @click="runSimulation"
            :disabled="loading"
            class="w-full bg-blue-600 hover:bg-blue-500 text-white font-medium py-2.5 rounded-lg text-xs shadow-md shadow-blue-600/20 transition-colors flex items-center justify-center gap-2"
          >
            <TrendingUp class="w-4 h-4" />
            <span>Recalculate Projection</span>
          </button>
        </div>

        <!-- Simulation Outputs -->
        <div class="lg:col-span-2 space-y-6">
          <!-- KPI Summary Cards -->
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4" v-if="simulationResult">
            <div class="bg-card border border-border rounded-xl p-5">
              <span class="text-xs text-slate-400 uppercase font-semibold">Future Nominal Wealth</span>
              <p class="text-2xl font-bold font-mono text-emerald-400 mt-1">
                {{ formatCurrency(simulationResult.final_nominal_wealth) }}
              </p>
              <span class="text-[10px] text-slate-500 font-mono">Future paper value</span>
            </div>

            <div class="bg-card border border-border rounded-xl p-5">
              <span class="text-xs text-slate-400 uppercase font-semibold">Real Purchasing Power</span>
              <p class="text-2xl font-bold font-mono text-blue-400 mt-1">
                {{ formatCurrency(simulationResult.final_real_wealth) }}
              </p>
              <span class="text-[10px] text-slate-500 font-mono">In today's money</span>
            </div>

            <div class="bg-card border border-border rounded-xl p-5">
              <span class="text-xs text-slate-400 uppercase font-semibold">Compounding Growth</span>
              <p class="text-2xl font-bold font-mono text-white mt-1">
                {{ formatCurrency(simulationResult.total_investment_gains) }}
              </p>
              <span class="text-[10px] text-slate-500 font-mono">Pure investment return</span>
            </div>
          </div>

          <!-- Trajectory Table -->
          <div class="bg-card border border-border rounded-xl overflow-hidden shadow-sm" v-if="simulationResult">
            <div class="px-6 py-4 border-b border-border flex items-center justify-between">
              <h3 class="font-bold text-sm text-white">Year-by-Year Growth Trajectory</h3>
              <span class="text-xs text-slate-400 font-mono">All amounts in GHS</span>
            </div>
            <div class="max-h-80 overflow-y-auto">
              <table class="w-full text-left text-sm text-slate-300">
                <thead class="bg-slate-900/60 text-xs uppercase font-semibold text-slate-400 sticky top-0">
                  <tr>
                    <th class="px-6 py-3">Year</th>
                    <th class="px-6 py-3 text-right">Contributions</th>
                    <th class="px-6 py-3 text-right">Nominal Value</th>
                    <th class="px-6 py-3 text-right">Real Value (Inflation Adj.)</th>
                    <th class="px-6 py-3 text-right">Investment Gains</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-border/60">
                  <tr v-for="pt in simulationResult.yearly_trajectory" :key="pt.year" class="hover:bg-slate-800/30 font-mono text-xs">
                    <td class="px-6 py-3 font-bold text-white">Year {{ pt.year }}</td>
                    <td class="px-6 py-3 text-right text-slate-400">{{ formatCurrency(pt.total_contributions) }}</td>
                    <td class="px-6 py-3 text-right font-bold text-emerald-400">{{ formatCurrency(pt.nominal_wealth) }}</td>
                    <td class="px-6 py-3 text-right font-medium text-blue-400">{{ formatCurrency(pt.real_wealth_inflation_adjusted) }}</td>
                    <td class="px-6 py-3 text-right text-slate-200">{{ formatCurrency(pt.total_investment_gains) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Goal Solver Card -->
          <div class="bg-card border border-border rounded-xl p-6 shadow-sm">
            <div class="flex items-center gap-2 border-b border-border pb-3 mb-4">
              <Target class="w-5 h-5 text-emerald-400" />
              <h3 class="font-bold text-sm text-white">Financial Goal Reverse Solver</h3>
            </div>
            <p class="text-xs text-slate-400 mb-4">
              Determine the exact monthly savings required to hit a specific financial target (e.g. GH₵500,000 for home purchase or retirement).
            </p>

            <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
              <div>
                <label class="block text-xs font-medium text-slate-300 mb-1">Target Amount (GH₵)</label>
                <input v-model.number="goalTarget" @change="solveGoal" type="number" step="10000" class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-xs text-white font-mono" />
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-300 mb-1">Current Principal</label>
                <input v-model.number="goalCurrent" @change="solveGoal" type="number" step="1000" class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-xs text-white font-mono" />
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-300 mb-1">Target Horizon (Years)</label>
                <input v-model.number="goalYears" @change="solveGoal" type="number" step="1" class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-xs text-white font-mono" />
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-300 mb-1">Expected Return</label>
                <input v-model.number="goalReturn" @change="solveGoal" type="number" step="0.01" class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-xs text-white font-mono" />
              </div>
            </div>

            <div v-if="goalResult" class="p-4 bg-slate-900/80 border border-slate-800 rounded-lg flex items-center justify-between">
              <div>
                <span class="text-xs text-slate-400">Required Monthly Contribution:</span>
                <p class="text-2xl font-bold font-mono text-emerald-400">
                  {{ formatCurrency(goalResult.required_monthly_savings_nominal) }} / month
                </p>
              </div>
              <div class="text-right">
                <span class="text-xs text-slate-400">Inflation-Protected Contribution:</span>
                <p class="text-lg font-bold font-mono text-blue-400">
                  {{ formatCurrency(goalResult.required_monthly_savings_inflation_adjusted) }} / month
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
