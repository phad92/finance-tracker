import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

export interface Portfolio {
  id: string
  name: string
  description?: string
  reporting_currency: string
  is_active: boolean
  total_value_reporting: number
  total_cost_basis_reporting: number
  total_unrealized_pnl_reporting: number
  total_realized_pnl_reporting: number
  holdings_count: number
}

export interface PortfolioHolding {
  id: string
  portfolio_id: string
  instrument_id: string
  symbol: string
  instrument_name: string
  instrument_type: string
  quantity: number
  average_cost_per_share: number
  total_cost_basis: number
  current_price: number
  current_market_value: number
  currency: string
  unrealized_pnl: number
  realized_pnl: number
}

export const usePortfolioStore = defineStore('portfolio', () => {
  const portfolios = ref<Portfolio[]>([])
  const holdings = ref<PortfolioHolding[]>([])
  const loading = ref(false)

  async function fetchPortfolios() {
    loading.value = true
    try {
      const res = await api.get<Portfolio[]>('/portfolios')
      portfolios.value = res.data
    } catch (err) {
      console.error('Failed to fetch portfolios', err)
    } finally {
      loading.value = false
    }
  }

  async function createPortfolio(payload: { name: string; description?: string; reporting_currency?: string }) {
    try {
      await api.post('/portfolios', payload)
      await fetchPortfolios()
      return true
    } catch (err) {
      console.error('Failed to create portfolio', err)
      return false
    }
  }

  async function fetchHoldings(portfolioId: string) {
    loading.value = true
    try {
      const res = await api.get<PortfolioHolding[]>(`/portfolios/${portfolioId}/holdings`)
      holdings.value = res.data
    } catch (err) {
      console.error('Failed to fetch holdings', err)
    } finally {
      loading.value = false
    }
  }

  async function recordTransaction(portfolioId: string, payload: any) {
    try {
      await api.post(`/portfolios/${portfolioId}/transactions`, payload)
      await fetchHoldings(portfolioId)
      await fetchPortfolios()
      return true
    } catch (err) {
      console.error('Failed to record transaction', err)
      return false
    }
  }

  return {
    portfolios,
    holdings,
    loading,
    fetchPortfolios,
    createPortfolio,
    fetchHoldings,
    recordTransaction,
  }
})
