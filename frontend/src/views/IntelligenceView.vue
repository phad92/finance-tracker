<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  BrainCircuit,
  RefreshCw,
  Newspaper,
  Landmark,
  FileText,
  Sparkles,
  ExternalLink,
} from 'lucide-vue-next'
import AppLayout from '@/components/layout/AppLayout.vue'
import InfoTooltip from '@/components/ui/InfoTooltip.vue'
import api from '@/services/api'

interface MacroIndicator {
  id: string
  code: string
  name: string
  country_code: string
  category: string
  unit: string
  source: string
  source_url?: string | null
  acquisition_method?: 'LIVE_API' | 'BASELINE_SEED' | string
  update_cadence?: string | null
  explainer?: string | null
  latest_value: number | null
  latest_date: string | null
}

const activeTab = ref<'macro' | 'research' | 'news'>('macro')

const macroIndicators = ref<MacroIndicator[]>([])
const instruments = ref<any[]>([])
const newsArticles = ref<any[]>([])
const savedReports = ref<any[]>([])

const selectedInstrumentId = ref('')
const focusQuestion = ref('')
const scoreResult = ref<any>(null)
const activeReport = ref<any>(null)

const syncingMacro = ref(false)
const syncingNews = ref(false)
const scoringLoading = ref(false)
const reportLoading = ref(false)

async function loadData() {
  try {
    const [macroRes, instRes, newsRes, repRes] = await Promise.all([
      api.get('/intelligence/macro'),
      api.get('/markets/instruments'),
      api.get('/intelligence/news'),
      api.get('/intelligence/research-reports'),
    ])
    macroIndicators.value = macroRes.data
    instruments.value = instRes.data
    newsArticles.value = newsRes.data
    savedReports.value = repRes.data
    if (instruments.value.length > 0 && !selectedInstrumentId.value) {
      selectedInstrumentId.value = instruments.value[0].id
    }
    if (savedReports.value.length > 0 && !activeReport.value) {
      activeReport.value = savedReports.value[0]
    }
  } catch (err) {
    console.error('Failed to load intelligence data', err)
  }
}

async function syncWorldBank() {
  syncingMacro.value = true
  try {
    await api.post('/intelligence/macro/sync')
    const res = await api.get('/intelligence/macro')
    macroIndicators.value = res.data
  } finally {
    syncingMacro.value = false
  }
}

async function syncNews() {
  syncingNews.value = true
  try {
    await api.post('/intelligence/news/sync')
    const res = await api.get('/intelligence/news')
    newsArticles.value = res.data
  } finally {
    syncingNews.value = false
  }
}

async function runOpportunityScore() {
  if (!selectedInstrumentId.value) return
  scoringLoading.value = true
  try {
    const res = await api.get(`/intelligence/opportunity-score/${selectedInstrumentId.value}`)
    scoreResult.value = res.data
  } finally {
    scoringLoading.value = false
  }
}

async function generateResearchReport() {
  if (!selectedInstrumentId.value) return
  reportLoading.value = true
  try {
    const res = await api.post('/intelligence/research-reports', {
      instrument_id: selectedInstrumentId.value,
      focus_question: focusQuestion.value || undefined,
    })
    activeReport.value = res.data
    savedReports.value.unshift(res.data)
  } finally {
    reportLoading.value = false
  }
}

function getRatingClass(rating: string) {
  if (rating === 'STRONG_BUY') return 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
  if (rating === 'ACCUMULATE') return 'bg-blue-500/15 text-blue-400 border-blue-500/30'
  if (rating === 'HOLD') return 'bg-amber-500/15 text-amber-400 border-amber-500/30'
  return 'bg-rose-500/15 text-rose-400 border-rose-500/30'
}

function getAcquisitionMeta(method?: string) {
  if (method === 'LIVE_API') {
    return {
      label: 'Live API',
      badgeClass: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25',
    }
  }
  return {
    label: 'Reference Seed',
    badgeClass: 'bg-amber-500/10 text-amber-400 border-amber-500/25',
  }
}

onMounted(loadData)
</script>

<template>
  <AppLayout>
    <div class="space-y-6 max-w-7xl mx-auto">
      <!-- Header -->
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Research & Market Intelligence</h1>
          <p class="text-sm text-slate-500 dark:text-slate-400">Macroeconomic indicators, multi-factor opportunity scoring, AI research reports, and news</p>
        </div>

        <div class="flex items-center gap-2 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-1 rounded-xl">
          <button
            @click="activeTab = 'macro'"
            class="px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5"
            :class="activeTab === 'macro' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'"
          >
            <Landmark class="w-3.5 h-3.5" />
            <span>Macro Dashboard</span>
          </button>
          <button
            @click="activeTab = 'research'"
            class="px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5"
            :class="activeTab === 'research' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'"
          >
            <BrainCircuit class="w-3.5 h-3.5" />
            <span>Scoring & AI Reports</span>
          </button>
          <button
            @click="activeTab = 'news'"
            class="px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5"
            :class="activeTab === 'news' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'"
          >
            <Newspaper class="w-3.5 h-3.5" />
            <span>Market News</span>
          </button>
        </div>
      </div>

      <!-- TAB 1: Macro Dashboard -->
      <div v-if="activeTab === 'macro'" class="space-y-6">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-center gap-2">
            <h2 class="text-sm font-bold text-slate-700 dark:text-slate-200 uppercase tracking-wider">Ghana & Global Economic Indicators</h2>
            <InfoTooltip
              label="About macroeconomic data sources"
              title="Macro Data Sources & Provenance"
              content="Displays domestic (Ghana) and US macroeconomic benchmarks. Series badged Live API update directly from the World Bank v2 API; Reference Seed series come from Bank of Ghana, Ghana Statistical Service, and FRED reference baselines."
              meta="World Bank v2 / BoG / GSS / FRED"
            />
          </div>
          <div class="flex items-center gap-2">
            <button
              @click="syncWorldBank"
              :disabled="syncingMacro"
              class="inline-flex items-center gap-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-medium px-3.5 py-2 rounded-lg border border-slate-200 dark:border-slate-700 transition-colors"
            >
              <RefreshCw class="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" :class="{ 'animate-spin': syncingMacro }" />
              <span>Sync World Bank API</span>
            </button>
            <InfoTooltip
              label="What Sync World Bank API updates"
              title="World Bank API Sync"
              content="Pulls the newest annual GDP growth and CPI inflation observations for Ghana and the US from api.worldbank.org. Central bank policy rates and Treasury Bill tender yields retain their Bank of Ghana / FRED baseline values unless separately updated."
              meta="Endpoint: api.worldbank.org/v2"
              source-url="https://data.worldbank.org/"
              source-name="World Bank Open Data"
              align="end"
            />
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div
            v-for="ind in macroIndicators"
            :key="ind.id"
            class="bg-card border border-border rounded-xl p-5 flex flex-col justify-between shadow-sm"
          >
            <div>
              <div class="flex items-start justify-between gap-2">
                <div class="flex flex-wrap items-center gap-1.5">
                  <span class="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-blue-600 dark:text-blue-400">
                    {{ ind.country_code }} &middot; {{ ind.category }}
                  </span>
                  <span
                    class="text-[10px] font-mono font-semibold px-2 py-0.5 rounded border"
                    :class="getAcquisitionMeta(ind.acquisition_method).badgeClass"
                  >
                    {{ getAcquisitionMeta(ind.acquisition_method).label }}
                  </span>
                </div>
                <InfoTooltip
                  :label="`More about ${ind.name}`"
                  :title="ind.name"
                  :content="ind.explainer || 'Macroeconomic benchmark tracked for portfolio context and valuation models.'"
                  :meta="ind.update_cadence ? `Cadence: ${ind.update_cadence}` : undefined"
                  :source-url="ind.source_url"
                  :source-name="ind.source"
                  align="end"
                />
              </div>
              <h3 class="text-sm font-semibold text-slate-900 dark:text-white mt-2.5">{{ ind.name }}</h3>
            </div>
            <div class="mt-4 flex items-end justify-between gap-3">
              <span class="text-3xl font-bold font-mono text-emerald-600 dark:text-emerald-400 shrink-0">
                {{ ind.latest_value !== null ? ind.latest_value : '—' }}{{ ind.unit }}
              </span>
              <div class="text-right text-[10px] font-mono text-slate-500 dark:text-slate-400 space-y-0.5 min-w-0">
                <a
                  v-if="ind.source_url"
                  :href="ind.source_url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="inline-flex items-center justify-end gap-1 text-blue-600 dark:text-blue-400 hover:text-blue-500 dark:hover:text-blue-300 transition-colors max-w-full"
                  :title="`Open source: ${ind.source}`"
                >
                  <span class="truncate">Source: {{ ind.source }}</span>
                  <ExternalLink class="w-2.5 h-2.5 shrink-0" aria-hidden="true" />
                </a>
                <div v-else class="truncate">Source: {{ ind.source }}</div>
                <div>As of {{ ind.latest_date || 'N/A' }}</div>
                <div v-if="ind.update_cadence" class="text-slate-400 dark:text-slate-500 truncate">{{ ind.update_cadence }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- TAB 2: Opportunity Scoring & 12-Section AI Research Reports -->
      <div v-if="activeTab === 'research'" class="space-y-6">
        <!-- Control Bar -->
        <div class="bg-card border border-border rounded-xl p-6 space-y-4 shadow-sm">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
            <div>
              <label class="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Select Security to Analyze</label>
              <select v-model="selectedInstrumentId" class="w-full bg-slate-50 dark:bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-slate-900 dark:text-white">
                <option v-for="inst in instruments" :key="inst.id" :value="inst.id">
                  {{ inst.symbol }} — {{ inst.name }} ({{ inst.exchange_code }})
                </option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Research Focus Question (Optional)</label>
              <input v-model="focusQuestion" placeholder="e.g. Dividend sustainability & currency risks" class="w-full bg-slate-50 dark:bg-slate-900 border border-border rounded-lg px-3 py-2 text-sm text-slate-900 dark:text-white" />
            </div>
            <div class="flex items-center gap-2">
              <button
                @click="runOpportunityScore"
                :disabled="scoringLoading"
                class="flex-1 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-white text-xs font-semibold px-4 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 transition-colors"
              >
                {{ scoringLoading ? 'Scoring...' : 'Calculate Score' }}
              </button>
              <button
                @click="generateResearchReport"
                :disabled="reportLoading"
                class="flex-1 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-4 py-2.5 rounded-lg shadow-lg shadow-blue-600/20 transition-colors flex items-center justify-center gap-1.5"
              >
                <Sparkles class="w-3.5 h-3.5" />
                <span>{{ reportLoading ? 'Generating...' : 'Generate Report' }}</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Opportunity Score Breakdown -->
        <div v-if="scoreResult" class="bg-card border border-border rounded-xl p-6 space-y-4 shadow-sm">
          <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-4">
            <div>
              <div class="flex items-center gap-1.5">
                <span class="text-xs font-mono text-slate-500 dark:text-slate-400 uppercase">Quantitative Opportunity Model</span>
                <InfoTooltip
                  label="How the Quantitative Opportunity Model scores instruments"
                  title="Multi-Factor Opportunity Score (0–100)"
                  content="Weighted composite of Fundamentals (25%), Valuation (20%), Growth (20%), Momentum (15%), Macro (10%), and Risk (10%). Score ratings combine internal price history, fundamentals, and macro benchmarks."
                  meta="Weights: 25/20/20/15/10/10%"
                />
              </div>
              <h3 class="text-lg font-bold text-slate-900 dark:text-white">{{ scoreResult.symbol }} — {{ scoreResult.name }}</h3>
            </div>
            <div class="flex items-center gap-4">
              <div class="text-right">
                <span class="text-3xl font-bold font-mono text-slate-900 dark:text-white">{{ scoreResult.total_score }}</span>
                <span class="text-xs text-slate-500 dark:text-slate-400 font-mono"> / 100</span>
              </div>
              <span class="px-3 py-1 rounded-full border text-xs font-mono font-bold" :class="getRatingClass(scoreResult.rating)">
                {{ scoreResult.rating }}
              </span>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div v-for="f in scoreResult.factors" :key="f.factor" class="bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-lg p-4 space-y-2">
              <div class="flex items-center justify-between">
                <span class="text-xs font-bold text-slate-800 dark:text-slate-200">{{ f.factor }} ({{ (f.weight * 100).toFixed(0) }}%)</span>
                <span class="text-xs font-mono font-bold text-blue-600 dark:text-blue-400">{{ f.raw_score }}/100</span>
              </div>
              <div class="w-full bg-slate-200 dark:bg-slate-800 h-1.5 rounded-full overflow-hidden">
                <div class="bg-blue-500 h-full rounded-full" :style="{ width: `${f.raw_score}%` }"></div>
              </div>
              <p class="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">{{ f.rationale }}</p>
            </div>
          </div>
        </div>

        <!-- 12-Section Research Report Display -->
        <div v-if="activeReport" class="bg-card border border-border rounded-xl p-6 space-y-6 shadow-sm">
          <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-4">
            <div>
              <div class="flex items-center gap-2">
                <FileText class="w-4 h-4 text-blue-600 dark:text-blue-400" />
                <h3 class="text-base font-bold text-slate-900 dark:text-white">{{ activeReport.title }}</h3>
              </div>
              <p class="text-xs text-slate-500 dark:text-slate-400 font-mono mt-1">
                Model: {{ activeReport.model_used }} &middot; Quality: {{ activeReport.data_quality_summary }} &middot; Score: {{ activeReport.opportunity_score }}/100
              </p>
            </div>
            <div v-if="savedReports.length > 1">
              <select
                @change="(e: any) => activeReport = savedReports.find(r => r.id === e.target.value)"
                class="bg-slate-50 dark:bg-slate-900 border border-border rounded-lg px-3 py-1.5 text-xs text-slate-700 dark:text-slate-300"
              >
                <option v-for="r in savedReports" :key="r.id" :value="r.id">{{ r.symbol }} ({{ new Date(r.created_at).toLocaleDateString() }})</option>
              </select>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
            <div class="space-y-2">
              <h4 class="font-bold text-slate-900 dark:text-white uppercase tracking-wider text-[11px]">1. Executive Summary</h4>
              <p>{{ activeReport.report_data.executive_summary }}</p>
            </div>
            <div class="space-y-2">
              <h4 class="font-bold text-slate-900 dark:text-white uppercase tracking-wider text-[11px]">2. Investment Thesis</h4>
              <p>{{ activeReport.report_data.investment_thesis }}</p>
            </div>
            <div class="space-y-2">
              <h4 class="font-bold text-slate-900 dark:text-white uppercase tracking-wider text-[11px]">3. Market Overview</h4>
              <p>{{ activeReport.report_data.market_overview }}</p>
            </div>
            <div class="space-y-2">
              <h4 class="font-bold text-slate-900 dark:text-white uppercase tracking-wider text-[11px]">4. Company Financial Analysis</h4>
              <p>{{ activeReport.report_data.company_financial_analysis }}</p>
            </div>
            <div class="space-y-2">
              <h4 class="font-bold text-slate-900 dark:text-white uppercase tracking-wider text-[11px]">5. Valuation</h4>
              <p>{{ activeReport.report_data.valuation }}</p>
            </div>
            <div class="space-y-2">
              <h4 class="font-bold text-slate-900 dark:text-white uppercase tracking-wider text-[11px]">7. Competitive Position</h4>
              <p>{{ activeReport.report_data.competitive_position }}</p>
            </div>
            <div class="space-y-2">
              <h4 class="font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider text-[11px]">6. Growth Catalysts</h4>
              <ul class="list-disc pl-4 space-y-1">
                <li v-for="c in activeReport.report_data.growth_catalysts" :key="c">{{ c }}</li>
              </ul>
            </div>
            <div class="space-y-2">
              <h4 class="font-bold text-rose-600 dark:text-rose-400 uppercase tracking-wider text-[11px]">8. Key Risks</h4>
              <ul class="list-disc pl-4 space-y-1">
                <li v-for="r in activeReport.report_data.key_risks" :key="r">{{ r }}</li>
              </ul>
            </div>
          </div>

          <!-- 9. Bear / Base / Bull Scenarios -->
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
            <div class="p-4 rounded-lg bg-rose-500/5 border border-rose-500/20">
              <span class="text-[11px] font-bold uppercase text-rose-600 dark:text-rose-400">Bear Case</span>
              <p class="text-xs text-slate-600 dark:text-slate-300 mt-1">{{ activeReport.report_data.scenarios?.bear }}</p>
            </div>
            <div class="p-4 rounded-lg bg-blue-500/5 border border-blue-500/20">
              <span class="text-[11px] font-bold uppercase text-blue-600 dark:text-blue-400">Base Case</span>
              <p class="text-xs text-slate-600 dark:text-slate-300 mt-1">{{ activeReport.report_data.scenarios?.base }}</p>
            </div>
            <div class="p-4 rounded-lg bg-emerald-500/5 border border-emerald-500/20">
              <span class="text-[11px] font-bold uppercase text-emerald-600 dark:text-emerald-400">Bull Case</span>
              <p class="text-xs text-slate-600 dark:text-slate-300 mt-1">{{ activeReport.report_data.scenarios?.bull }}</p>
            </div>
          </div>

          <!-- 10-12 Metadata, Confidence & Thesis Invalidation -->
          <div class="bg-slate-50 dark:bg-slate-900/70 border border-slate-200 dark:border-slate-800 rounded-lg p-4 grid grid-cols-1 md:grid-cols-3 gap-4 text-[11px] text-slate-600 dark:text-slate-400">
            <div>
              <span class="font-bold text-slate-800 dark:text-slate-200 uppercase block mb-1">10. Data Sources</span>
              <ul class="space-y-0.5 font-mono">
                <li v-for="s in activeReport.report_data.data_sources_and_dates" :key="s">&bull; {{ s }}</li>
              </ul>
            </div>
            <div>
              <span class="font-bold text-slate-800 dark:text-slate-200 uppercase block mb-1">11. Confidence & Completeness</span>
              <p>{{ activeReport.report_data.confidence_and_data_completeness }}</p>
            </div>
            <div>
              <span class="font-bold text-amber-600 dark:text-amber-400 uppercase block mb-1">12. Thesis Invalidation</span>
              <ul class="space-y-0.5">
                <li v-for="inv in activeReport.report_data.thesis_invalidation_conditions" :key="inv">&bull; {{ inv }}</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <!-- TAB 3: Market News -->
      <div v-if="activeTab === 'news'" class="space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-center gap-2">
            <h2 class="text-sm font-bold text-slate-700 dark:text-slate-200 uppercase tracking-wider">Financial News & Market Events</h2>
            <InfoTooltip
              label="About market news feeds and provenance"
              title="RSS Feed Ingestion"
              content="Articles are synced on demand from configured financial RSS feeds and tagged with tracked security symbols when ticker references appear in the headline or summary."
              meta="Source: Live RSS Feeds"
            />
          </div>
          <div class="flex items-center gap-2">
            <button
              @click="syncNews"
              :disabled="syncingNews"
              class="inline-flex items-center gap-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-medium px-3.5 py-2 rounded-lg border border-slate-200 dark:border-slate-700 transition-colors"
            >
              <RefreshCw class="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" :class="{ 'animate-spin': syncingNews }" />
              <span>Sync RSS Feeds</span>
            </button>
          </div>
        </div>

        <div class="space-y-3">
          <div
            v-for="article in newsArticles"
            :key="article.id"
            class="bg-card border border-border rounded-xl p-5 hover:border-slate-300 dark:hover:border-slate-700 transition-colors shadow-sm"
          >
            <div class="flex items-start justify-between gap-4">
              <div class="space-y-1.5">
                <div class="flex items-center gap-2 text-[10px] font-mono text-slate-500 dark:text-slate-400">
                  <span class="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-blue-600 dark:text-blue-400 border border-slate-200 dark:border-slate-700">{{ article.country_code }}</span>
                  <span>{{ article.publisher }}</span>
                  <span>&middot;</span>
                  <span>{{ new Date(article.published_at).toLocaleDateString() }}</span>
                </div>
                <a :href="article.url" target="_blank" rel="noopener noreferrer" class="text-sm font-bold text-slate-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400 transition-colors block">
                  {{ article.title }}
                </a>
                <p v-if="article.summary" class="text-xs text-slate-600 dark:text-slate-400 line-clamp-2">{{ article.summary }}</p>
              </div>
              <div v-if="article.related_symbols" class="flex flex-wrap gap-1 shrink-0">
                <span
                  v-for="sym in article.related_symbols.split(',')"
                  :key="sym"
                  class="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 text-[10px] font-mono font-bold"
                >
                  {{ sym }}
                </span>
              </div>
            </div>
          </div>

          <div v-if="newsArticles.length === 0" class="bg-card border border-border rounded-xl p-12 text-center text-sm text-slate-500">
            No news articles ingested yet. Click "Sync RSS Feeds" to collect headlines.
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
