import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

export interface NetWorthSummary {
  reporting_currency: string
  total_assets: number
  total_liabilities: number
  net_worth: number
  assets_by_category: Record<string, number>
  currency_exposure: Record<string, number>
  as_of_date: string
}

export interface AssetCategory {
  id: string
  code: string
  name: string
  description?: string
  is_liquid: boolean
}

export interface AssetValuation {
  id: string
  asset_id: string
  valuation_date: string
  value_original_currency: number
  currency: string
  exchange_rate_to_reporting: number
  value_reporting_currency: number
  valuation_method: string
  notes?: string
}

export interface Asset {
  id: string
  category_id: string
  category_name?: string
  name: string
  institution?: string
  currency: string
  ownership_percentage: number
  is_active: boolean
  latest_valuation?: AssetValuation
  notes?: string
}

export interface Liability {
  id: string
  name: string
  institution?: string
  category: string
  currency: string
  original_balance: number
  current_balance: number
  interest_rate?: number
  monthly_payment?: number
  is_active: boolean
  notes?: string
}

export const useWealthStore = defineStore('wealth', () => {
  const summary = ref<NetWorthSummary | null>(null)
  const assets = ref<Asset[]>([])
  const liabilities = ref<Liability[]>([])
  const categories = ref<AssetCategory[]>([])
  const loading = ref(false)

  async function fetchSummary() {
    try {
      const res = await api.get<NetWorthSummary>('/wealth/summary')
      summary.value = res.data
    } catch (err) {
      console.error('Error fetching net worth summary', err)
    }
  }

  async function fetchAssets() {
    try {
      const res = await api.get<Asset[]>('/wealth/assets')
      assets.value = res.data
    } catch (err) {
      console.error('Error fetching assets', err)
    }
  }

  async function fetchLiabilities() {
    try {
      const res = await api.get<Liability[]>('/wealth/liabilities')
      liabilities.value = res.data
    } catch (err) {
      console.error('Error fetching liabilities', err)
    }
  }

  async function fetchCategories() {
    try {
      const res = await api.get<AssetCategory[]>('/wealth/categories')
      categories.value = res.data
    } catch (err) {
      console.error('Error fetching categories', err)
    }
  }

  async function createAsset(payload: any) {
    loading.value = true
    try {
      await api.post('/wealth/assets', payload)
      await fetchAssets()
      await fetchSummary()
      return true
    } catch (err) {
      console.error('Failed to create asset', err)
      return false
    } finally {
      loading.value = false
    }
  }

  async function createLiability(payload: any) {
    loading.value = true
    try {
      await api.post('/wealth/liabilities', payload)
      await fetchLiabilities()
      await fetchSummary()
      return true
    } catch (err) {
      console.error('Failed to create liability', err)
      return false
    } finally {
      loading.value = false
    }
  }

  return {
    summary,
    assets,
    liabilities,
    categories,
    loading,
    fetchSummary,
    fetchAssets,
    fetchLiabilities,
    fetchCategories,
    createAsset,
    createLiability,
  }
})

