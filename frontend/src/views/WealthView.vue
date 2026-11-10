<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { PlusCircle, Wallet, CreditCard, Calendar, Building } from 'lucide-vue-next'
import AppLayout from '@/components/layout/AppLayout.vue'
import { useWealthStore } from '@/stores/wealth'
import { formatCurrency } from '@/lib/utils'

const wealthStore = useWealthStore()
const activeTab = ref<'assets' | 'liabilities'>('assets')

// Modal states
const showAddAssetModal = ref(false)
const showAddLiabilityModal = ref(false)

// Asset form
const assetName = ref('')
const assetCategory = ref('')
const assetInstitution = ref('')
const assetCurrency = ref('GHS')
const assetOwnership = ref(100)
const assetInitialValue = ref(0)
const assetNotes = ref('')

// Liability form
const liabName = ref('')
const liabCategory = ref('PERSONAL_LOAN')
const liabInstitution = ref('')
const liabCurrency = ref('GHS')
const liabOriginalBalance = ref(0)
const liabCurrentBalance = ref(0)
const liabInterestRate = ref<number | undefined>(undefined)
const liabMonthlyPayment = ref<number | undefined>(undefined)

onMounted(async () => {
  await wealthStore.fetchCategories()
  await wealthStore.fetchAssets()
  await wealthStore.fetchLiabilities()
})

async function handleCreateAsset() {
  const success = await wealthStore.createAsset({
    name: assetName.value,
    category_id: assetCategory.value,
    institution: assetInstitution.value || undefined,
    currency: assetCurrency.value,
    ownership_percentage: assetOwnership.value,
    notes: assetNotes.value || undefined,
    initial_valuation: assetInitialValue.value > 0 ? {
      value_original_currency: assetInitialValue.value,
      currency: assetCurrency.value,
      valuation_method: 'MANUAL',
    } : undefined
  })
  if (success) {
    showAddAssetModal.value = false
    assetName.value = ''
    assetInstitution.value = ''
    assetInitialValue.value = 0
  }
}

async function handleCreateLiability() {
  const success = await wealthStore.createLiability({
    name: liabName.value,
    category: liabCategory.value,
    institution: liabInstitution.value || undefined,
    currency: liabCurrency.value,
    original_balance: liabOriginalBalance.value,
    current_balance: liabCurrentBalance.value,
    interest_rate: liabInterestRate.value ? liabInterestRate.value / 100 : undefined,
    monthly_payment: liabMonthlyPayment.value || undefined,
  })
  if (success) {
    showAddLiabilityModal.value = false
    liabName.value = ''
    liabInstitution.value = ''
    liabOriginalBalance.value = 0
    liabCurrentBalance.value = 0
  }
}
</script>

<template>
  <AppLayout>
    <div class="space-y-6 max-w-7xl mx-auto">
      <!-- Header -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-white tracking-tight">Wealth & Balance Sheet</h1>
          <p class="text-sm text-slate-400">Track and value all physical, bank, mobile money, and alternative assets</p>
        </div>
        <div>
          <button
            v-if="activeTab === 'assets'"
            @click="showAddAssetModal = true"
            class="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium px-4 py-2 rounded-lg transition-colors shadow-lg shadow-blue-600/20"
          >
            <PlusCircle class="w-4 h-4" />
            <span>Add Asset</span>
          </button>
          <button
            v-else
            @click="showAddLiabilityModal = true"
            class="inline-flex items-center gap-2 bg-rose-600 hover:bg-rose-500 text-white text-xs font-medium px-4 py-2 rounded-lg transition-colors shadow-lg shadow-rose-600/20"
          >
            <PlusCircle class="w-4 h-4" />
            <span>Add Liability</span>
          </button>
        </div>
      </div>

      <!-- Tab Buttons -->
      <div class="flex items-center gap-3 border-b border-border pb-3">
        <button
          @click="activeTab = 'assets'"
          class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          :class="activeTab === 'assets' ? 'bg-blue-600 text-white shadow-md shadow-blue-600/20 font-semibold' : 'text-slate-400 hover:text-white'"
        >
          <Wallet class="w-4 h-4" />
          <span>Assets ({{ wealthStore.assets.length }})</span>
        </button>
        <button
          @click="activeTab = 'liabilities'"
          class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          :class="activeTab === 'liabilities' ? 'bg-rose-600 text-white shadow-md shadow-rose-600/20 font-semibold' : 'text-slate-400 hover:text-white'"
        >
          <CreditCard class="w-4 h-4" />
          <span>Liabilities ({{ wealthStore.liabilities.length }})</span>
        </button>
      </div>

      <!-- Assets Table -->
      <div v-if="activeTab === 'assets'" class="bg-card border border-border rounded-xl overflow-hidden shadow-sm">
        <table class="w-full text-left text-sm text-slate-300">
          <thead class="bg-slate-900/60 text-xs uppercase font-semibold text-slate-400 border-b border-border">
            <tr>
              <th class="px-6 py-4">Asset Name</th>
              <th class="px-6 py-4">Category</th>
              <th class="px-6 py-4">Institution</th>
              <th class="px-6 py-4">Currency</th>
              <th class="px-6 py-4 text-right">Latest Valuation</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border/60">
            <tr v-for="asset in wealthStore.assets" :key="asset.id" class="hover:bg-slate-800/30 transition-colors">
              <td class="px-6 py-4 font-medium text-white flex items-center gap-3">
                <div class="w-8 h-8 rounded-lg bg-blue-600/10 text-blue-400 flex items-center justify-center font-bold text-xs">
                  {{ asset.name.charAt(0).toUpperCase() }}
                </div>
                <span>{{ asset.name }}</span>
              </td>
              <td class="px-6 py-4 text-xs font-mono text-slate-300">
                {{ asset.category_name || 'General' }}
              </td>
              <td class="px-6 py-4 text-xs text-slate-400">
                {{ asset.institution || '—' }}
              </td>
              <td class="px-6 py-4 text-xs font-mono">
                <span class="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-blue-400">
                  {{ asset.currency }}
                </span>
              </td>
              <td class="px-6 py-4 text-right font-mono font-bold text-white">
                {{ asset.latest_valuation ? formatCurrency(asset.latest_valuation.value_original_currency, asset.currency) : '—' }}
              </td>
            </tr>
            <tr v-if="wealthStore.assets.length === 0">
              <td colspan="5" class="px-6 py-12 text-center text-slate-500">
                No assets added yet. Click "Add Asset" above to get started.
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Liabilities Table -->
      <div v-else class="bg-card border border-border rounded-xl overflow-hidden shadow-sm">
        <table class="w-full text-left text-sm text-slate-300">
          <thead class="bg-slate-900/60 text-xs uppercase font-semibold text-slate-400 border-b border-border">
            <tr>
              <th class="px-6 py-4">Liability</th>
              <th class="px-6 py-4">Type</th>
              <th class="px-6 py-4">Lender / Institution</th>
              <th class="px-6 py-4 text-right">Current Balance</th>
              <th class="px-6 py-4 text-right">Original Balance</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border/60">
            <tr v-for="liab in wealthStore.liabilities" :key="liab.id" class="hover:bg-slate-800/30 transition-colors">
              <td class="px-6 py-4 font-medium text-white">
                {{ liab.name }}
              </td>
              <td class="px-6 py-4 text-xs font-mono text-slate-400">
                {{ liab.category }}
              </td>
              <td class="px-6 py-4 text-xs text-slate-400">
                {{ liab.institution || '—' }}
              </td>
              <td class="px-6 py-4 text-right font-mono font-bold text-rose-400">
                {{ formatCurrency(liab.current_balance, liab.currency) }}
              </td>
              <td class="px-6 py-4 text-right font-mono text-xs text-slate-400">
                {{ formatCurrency(liab.original_balance, liab.currency) }}
              </td>
            </tr>
            <tr v-if="wealthStore.liabilities.length === 0">
              <td colspan="5" class="px-6 py-12 text-center text-slate-500">
                No liabilities recorded. Debt-free status!
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Add Asset Modal -->
      <div v-if="showAddAssetModal" class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div class="bg-card border border-border rounded-xl w-full max-w-lg p-6 space-y-4 shadow-2xl">
          <div class="flex items-center justify-between border-b border-border pb-3">
            <h3 class="font-bold text-white text-base">Record New Asset</h3>
            <button @click="showAddAssetModal = false" class="text-slate-400 hover:text-white">&times;</button>
          </div>

          <form @submit.prevent="handleCreateAsset" class="space-y-4">
            <div>
              <label class="block text-xs font-medium text-slate-300 mb-1">Asset Name</label>
              <input v-model="assetName" required placeholder="e.g. Stanbic Savings, MTN MoMo, Cantonments Land" class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-medium text-slate-300 mb-1">Category</label>
                <select v-model="assetCategory" required class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500">
                  <option disabled value="">Select category</option>
                  <option v-for="cat in wealthStore.categories" :key="cat.id" :value="cat.id">{{ cat.name }}</option>
                </select>
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-300 mb-1">Currency</label>
                <select v-model="assetCurrency" class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500">
                  <option value="GHS">GHS</option>
                  <option value="USD">USD</option>
                  <option value="GBP">GBP</option>
                  <option value="EUR">EUR</option>
                </select>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-medium text-slate-300 mb-1">Institution / Bank</label>
                <input v-model="assetInstitution" placeholder="e.g. Stanbic Bank, MTN" class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-300 mb-1">Initial Valuation Amount</label>
                <input v-model.number="assetInitialValue" type="number" step="0.01" min="0" class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
              </div>
            </div>

            <div class="flex justify-end gap-3 pt-4 border-t border-border">
              <button @click="showAddAssetModal = false" type="button" class="px-4 py-2 text-xs text-slate-400 hover:text-white">Cancel</button>
              <button type="submit" :disabled="wealthStore.loading" class="bg-blue-600 hover:bg-blue-500 text-white font-medium px-4 py-2 rounded-lg text-xs shadow-md shadow-blue-600/20">Save Asset</button>
            </div>
          </form>
        </div>
      </div>

      <!-- Add Liability Modal -->
      <div v-if="showAddLiabilityModal" class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div class="bg-card border border-border rounded-xl w-full max-w-lg p-6 space-y-4 shadow-2xl">
          <div class="flex items-center justify-between border-b border-border pb-3">
            <h3 class="font-bold text-white text-base">Record Liability / Debt</h3>
            <button @click="showAddLiabilityModal = false" class="text-slate-400 hover:text-white">&times;</button>
          </div>

          <form @submit.prevent="handleCreateLiability" class="space-y-4">
            <div>
              <label class="block text-xs font-medium text-slate-300 mb-1">Liability Description</label>
              <input v-model="liabName" required placeholder="e.g. Standard Chartered Auto Loan, Home Mortgage" class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-rose-500" />
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-medium text-slate-300 mb-1">Category</label>
                <select v-model="liabCategory" class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-rose-500">
                  <option value="MORTGAGE">Mortgage</option>
                  <option value="PERSONAL_LOAN">Personal Loan</option>
                  <option value="CREDIT_CARD">Credit Card</option>
                  <option value="BUSINESS_LOAN">Business Loan</option>
                </select>
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-300 mb-1">Currency</label>
                <select v-model="liabCurrency" class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-rose-500">
                  <option value="GHS">GHS</option>
                  <option value="USD">USD</option>
                  <option value="GBP">GBP</option>
                  <option value="EUR">EUR</option>
                </select>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-medium text-slate-300 mb-1">Current Balance Due</label>
                <input v-model.number="liabCurrentBalance" type="number" step="0.01" min="0" required class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-rose-500" />
              </div>
              <div>
                <label class="block text-xs font-medium text-slate-300 mb-1">Original Loan Amount</label>
                <input v-model.number="liabOriginalBalance" type="number" step="0.01" min="0" required class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-rose-500" />
              </div>
            </div>

            <div class="flex justify-end gap-3 pt-4 border-t border-border">
              <button @click="showAddLiabilityModal = false" type="button" class="px-4 py-2 text-xs text-slate-400 hover:text-white">Cancel</button>
              <button type="submit" :disabled="wealthStore.loading" class="bg-rose-600 hover:bg-rose-500 text-white font-medium px-4 py-2 rounded-lg text-xs shadow-md shadow-rose-600/20">Save Liability</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
