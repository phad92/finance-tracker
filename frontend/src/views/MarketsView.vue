<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RefreshCw, Upload, Globe, ArrowUpDown, CheckCircle2, AlertCircle, Plus, X } from 'lucide-vue-next'
import AppLayout from '@/components/layout/AppLayout.vue'
import api from '@/services/api'
import { formatCurrency } from '@/lib/utils'

interface Instrument {
  id: string
  symbol: string
  name: string
  exchange_code: string
  instrument_type: string
  currency_code: string
  sector?: string
  latest_price?: number
  latest_price_date?: string
  data_source?: string
}

const instruments = ref<Instrument[]>([])
const selectedExchange = ref<string>('ALL')
const loading = ref(false)
const syncingSymbol = ref<string | null>(null)
const syncStatusMessage = ref<string | null>(null)
const isError = ref(false)

// CSV upload
const csvFile = ref<File | null>(null)
const uploadingCsv = ref(false)

// Add instrument modal
const showAddModal = ref(false)
const addingInstrument = ref(false)
const addError = ref<string | null>(null)

const newInstrument = ref({
  symbol: '',
  name: '',
  exchange_code: 'NYSE',
  instrument_type: 'ETF',
  currency_code: 'USD',
  sector: '',
})

function openAddModal() {
  newInstrument.value = {
    symbol: '',
    name: '',
    exchange_code: selectedExchange.value !== 'ALL' ? selectedExchange.value : 'NYSE',
    instrument_type: selectedExchange.value === 'COMMODITIES' ? 'COMMODITY' : 'ETF',
    currency_code: selectedExchange.value === 'GSE' ? 'GHS' : 'USD',
    sector: selectedExchange.value === 'COMMODITIES' ? 'Precious Metals' : 'Index ETF',
  }
  addError.value = null
  showAddModal.value = true
}

async function submitAddInstrument() {
  if (!newInstrument.value.symbol || !newInstrument.value.name) {
    addError.value = 'Symbol and Name are required.'
    return
  }
  addingInstrument.value = true
  addError.value = null
  try {
    await api.post('/markets/instruments', {
      symbol: newInstrument.value.symbol.trim().toUpperCase(),
      name: newInstrument.value.name.trim(),
      exchange_code: newInstrument.value.exchange_code,
      instrument_type: newInstrument.value.instrument_type,
      currency_code: newInstrument.value.currency_code,
      sector: newInstrument.value.sector.trim() || undefined,
    })
    showAddModal.value = false
    syncStatusMessage.value = `Successfully registered ${newInstrument.value.symbol.toUpperCase()} in the market master.`
    isError.value = false
    await fetchInstruments()
  } catch (err: any) {
    addError.value = err.response?.data?.detail || 'Failed to add instrument.'
  } finally {
    addingInstrument.value = false
  }
}

const filteredInstruments = computed(() => {
  if (selectedExchange.value === 'ALL') return instruments.value
  return instruments.value.filter(i => i.exchange_code === selectedExchange.value)
})

async function fetchInstruments() {
  loading.value = true
  try {
    const res = await api.get<Instrument[]>('/markets/instruments')
    instruments.value = res.data
  } catch (err) {
    console.error('Failed to fetch instruments', err)
  } finally {
    loading.value = false
  }
}

async function syncFxRates() {
  syncStatusMessage.value = null
  isError.value = false
  try {
    const res = await api.post('/markets/sync/fx')
    syncStatusMessage.value = `Updated ${res.data.rates_updated?.length || 0} daily FX exchange rates.`
  } catch (err) {
    isError.value = true
    syncStatusMessage.value = 'Failed to synchronize FX rates.'
  }
}

async function syncUsTicker(symbol: string) {
  syncingSymbol.value = symbol
  syncStatusMessage.value = null
  isError.value = false
  try {
    const res = await api.post(`/markets/sync/us/${symbol}`)
    syncStatusMessage.value = res.data.message
    if (res.data.synced_count === 0) isError.value = true
    await fetchInstruments()
  } catch (err) {
    isError.value = true
    syncStatusMessage.value = `Error syncing ${symbol}`
  } finally {
    syncingSymbol.value = null
  }
}

function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    csvFile.value = target.files[0]
  }
}

async function uploadGseCsv() {
  if (!csvFile.value) return
  uploadingCsv.value = true
  syncStatusMessage.value = null
  isError.value = false
  try {
    const formData = new FormData()
    formData.append('file', csvFile.value)
    const res = await api.post('/markets/gse/upload-csv', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    syncStatusMessage.value = res.data.message
    csvFile.value = null
    await fetchInstruments()
  } catch (err) {
    isError.value = true
    syncStatusMessage.value = 'Failed to ingest GSE CSV file.'
  } finally {
    uploadingCsv.value = false
  }
}

onMounted(async () => {
  await fetchInstruments()
})
</script>

<template>
  <AppLayout>
    <div class="space-y-6 max-w-7xl mx-auto">
      <!-- Header -->
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold text-white tracking-tight">Markets & Data Ingestion</h1>
          <p class="text-sm text-slate-400">Manage global securities, sync US market feeds, and ingest GSE daily bulletins</p>
        </div>
        <div class="flex items-center gap-3">
          <button
            @click="openAddModal"
            class="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-4 py-2 rounded-lg shadow-md transition-colors"
          >
            <Plus class="w-4 h-4" />
            <span>Add Security</span>
          </button>
          <button
            @click="syncFxRates"
            class="inline-flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium px-4 py-2 rounded-lg border border-slate-700 transition-colors"
          >
            <ArrowUpDown class="w-4 h-4 text-blue-400" />
            <span>Sync FX Rates</span>
          </button>
        </div>
      </div>

      <!-- Status Notification -->
      <div
        v-if="syncStatusMessage"
        class="p-4 rounded-xl border flex items-center gap-3 text-xs font-medium"
        :class="isError ? 'bg-rose-500/10 border-rose-500/20 text-rose-400' : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'"
      >
        <component :is="isError ? AlertCircle : CheckCircle2" class="w-4 h-4 shrink-0" />
        <span>{{ syncStatusMessage }}</span>
      </div>

      <!-- GSE CSV Ingestion Panel -->
      <div class="bg-card border border-border rounded-xl p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h2 class="text-sm font-bold text-white flex items-center gap-2">
            <Globe class="w-4 h-4 text-amber-400" />
            <span>Ghana Stock Exchange (GSE) Daily Price Uploader</span>
          </h2>
          <p class="text-xs text-slate-400 mt-1">
            Upload a CSV file containing GSE Daily Official List prices (<code class="text-slate-300">Symbol, ClosePrice, Volume, Date</code>).
          </p>
        </div>
        <div class="flex items-center gap-3">
          <input
            type="file"
            accept=".csv"
            @change="handleFileSelect"
            class="text-xs text-slate-400 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border file:border-slate-700 file:text-xs file:font-medium file:bg-slate-800 file:text-slate-200 hover:file:bg-slate-700"
          />
          <button
            @click="uploadGseCsv"
            :disabled="!csvFile || uploadingCsv"
            class="inline-flex items-center gap-2 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white text-xs font-medium px-4 py-2 rounded-lg transition-colors"
          >
            <Upload class="w-4 h-4" />
            <span>{{ uploadingCsv ? 'Uploading...' : 'Ingest CSV' }}</span>
          </button>
        </div>
      </div>

      <!-- Exchange Filters -->
      <div class="flex items-center gap-2 border-b border-border pb-3 overflow-x-auto">
        <button
          v-for="ex in ['ALL', 'GSE', 'NYSE', 'NASDAQ', 'COMMODITIES']"
          :key="ex"
          @click="selectedExchange = ex"
          class="px-3 py-1.5 rounded-lg text-xs font-mono font-semibold transition-colors whitespace-nowrap"
          :class="selectedExchange === ex ? 'bg-blue-600 text-white' : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'"
        >
          {{ ex }}
        </button>
      </div>

      <!-- Instruments Master Table -->
      <div class="bg-card border border-border rounded-xl overflow-hidden shadow-sm">
        <table class="w-full text-left text-sm text-slate-300">
          <thead class="bg-slate-900/60 text-xs uppercase font-semibold text-slate-400 border-b border-border">
            <tr>
              <th class="px-6 py-4">Symbol</th>
              <th class="px-6 py-4">Company / Security</th>
              <th class="px-6 py-4">Exchange</th>
              <th class="px-6 py-4">Sector</th>
              <th class="px-6 py-4 text-right">Latest Price</th>
              <th class="px-6 py-4">Source / Date</th>
              <th class="px-6 py-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border/60">
            <tr v-for="inst in filteredInstruments" :key="inst.id" class="hover:bg-slate-800/30 transition-colors">
              <td class="px-6 py-4 font-mono font-bold text-white">
                {{ inst.symbol }}
              </td>
              <td class="px-6 py-4 text-sm text-slate-200 font-medium">
                {{ inst.name }}
              </td>
              <td class="px-6 py-4 text-xs font-mono">
                <span class="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-blue-400">
                  {{ inst.exchange_code }}
                </span>
              </td>
              <td class="px-6 py-4 text-xs text-slate-400">
                {{ inst.sector || '—' }}
              </td>
              <td class="px-6 py-4 text-right font-mono font-bold text-white">
                {{ inst.latest_price ? formatCurrency(inst.latest_price, inst.currency_code) : '—' }}
              </td>
              <td class="px-6 py-4 text-xs text-slate-400 font-mono">
                <span v-if="inst.latest_price_date">{{ inst.latest_price_date }} ({{ inst.data_source }})</span>
                <span v-else>No quotes</span>
              </td>
              <td class="px-6 py-4 text-right">
                <button
                  v-if="inst.exchange_code !== 'GSE'"
                  @click="syncUsTicker(inst.symbol)"
                  :disabled="syncingSymbol === inst.symbol"
                  class="inline-flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 bg-blue-500/10 hover:bg-blue-500/20 px-2.5 py-1 rounded border border-blue-500/20 transition-colors"
                >
                  <RefreshCw class="w-3 h-3" :class="{ 'animate-spin': syncingSymbol === inst.symbol }" />
                  <span>Sync EOD</span>
                </button>
                <span v-else class="text-[10px] text-slate-500 font-mono">CSV / Manual</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Add Security Modal -->
      <div
        v-if="showAddModal"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm"
        @click.self="showAddModal = false"
      >
        <div class="bg-card border border-border w-full max-w-lg rounded-2xl p-6 shadow-2xl space-y-5">
          <div class="flex items-center justify-between border-b border-border pb-3">
            <div>
              <h3 class="text-base font-bold text-white">Add Security / ETF / Commodity</h3>
              <p class="text-xs text-slate-400 mt-0.5">Register a security in the market master for tracking and pricing</p>
            </div>
            <button
              @click="showAddModal = false"
              class="text-slate-400 hover:text-white p-1 rounded-lg transition-colors"
            >
              <X class="w-5 h-5" />
            </button>
          </div>

          <div v-if="addError" class="p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-xs text-rose-400">
            {{ addError }}
          </div>

          <form @submit.prevent="submitAddInstrument" class="space-y-4">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-semibold text-slate-300 mb-1.5">Symbol / Ticker</label>
                <input
                  v-model="newInstrument.symbol"
                  placeholder="e.g. VTI, GLD, CC=F"
                  required
                  class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label class="block text-xs font-semibold text-slate-300 mb-1.5">Exchange / Market</label>
                <select
                  v-model="newInstrument.exchange_code"
                  class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                >
                  <option value="NYSE">NYSE (New York)</option>
                  <option value="NASDAQ">NASDAQ</option>
                  <option value="COMMODITIES">COMMODITIES (Gold, Cocoa, Oil)</option>
                  <option value="GSE">GSE (Ghana)</option>
                  <option value="JSE">JSE (Johannesburg)</option>
                </select>
              </div>
            </div>

            <div>
              <label class="block text-xs font-semibold text-slate-300 mb-1.5">Security / Commodity Name</label>
              <input
                v-model="newInstrument.name"
                placeholder="e.g. Vanguard Total Stock Market ETF"
                required
                class="w-full bg-slate-900 border border-border rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
              />
            </div>

            <div class="grid grid-cols-3 gap-3">
              <div>
                <label class="block text-xs font-semibold text-slate-300 mb-1.5">Type</label>
                <select
                  v-model="newInstrument.instrument_type"
                  class="w-full bg-slate-900 border border-border rounded-lg px-2.5 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                >
                  <option value="ETF">ETF</option>
                  <option value="EQUITY">Stock (Equity)</option>
                  <option value="COMMODITY">Commodity</option>
                  <option value="BOND">Bond</option>
                </select>
              </div>
              <div>
                <label class="block text-xs font-semibold text-slate-300 mb-1.5">Currency</label>
                <select
                  v-model="newInstrument.currency_code"
                  class="w-full bg-slate-900 border border-border rounded-lg px-2.5 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                >
                  <option value="USD">USD ($)</option>
                  <option value="GHS">GHS (GH₵)</option>
                  <option value="EUR">EUR (€)</option>
                  <option value="GBP">GBP (£)</option>
                </select>
              </div>
              <div>
                <label class="block text-xs font-semibold text-slate-300 mb-1.5">Sector</label>
                <input
                  v-model="newInstrument.sector"
                  placeholder="e.g. Index ETF, Precious Metals"
                  class="w-full bg-slate-900 border border-border rounded-lg px-2.5 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>

            <div class="flex items-center justify-end gap-3 pt-3 border-t border-border">
              <button
                type="button"
                @click="showAddModal = false"
                class="px-4 py-2 rounded-lg text-xs font-semibold text-slate-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                :disabled="addingInstrument"
                class="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-colors flex items-center gap-1.5"
              >
                <span v-if="addingInstrument" class="animate-spin mr-1">⌛</span>
                <span>Register Security</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

