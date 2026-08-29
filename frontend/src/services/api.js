const API_BASE = '/api'

export async function askSettlementQuery(query, merchantId) {
  const response = await fetch(`${API_BASE}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, merchant_id: merchantId })
  })
  if (!response.ok) {
    throw new Error(`Query failed: ${response.statusText}`)
  }
  return response.json()
}

export async function fetchTransactions(params = {}) {
  const query = new URLSearchParams()
  if (params.page) query.append('page', params.page)
  if (params.pageSize) query.append('page_size', params.pageSize)
  if (params.status && params.status !== 'all') query.append('status', params.status)
  if (params.search) query.append('search', params.search)
  if (params.minAmount) query.append('min_amount', params.minAmount)
  if (params.maxAmount) query.append('max_amount', params.maxAmount)
  if (params.startDate) query.append('start_date', params.startDate)
  if (params.endDate) query.append('end_date', params.endDate)

  const response = await fetch(`${API_BASE}/transactions?${query.toString()}`)
  if (!response.ok) {
    throw new Error(`Failed to fetch transactions: ${response.statusText}`)
  }
  return response.json()
}

export async function fetchExceptions(status = 'all') {
  const query = new URLSearchParams()
  if (status && status !== 'all') query.append('status', status)
  const response = await fetch(`${API_BASE}/exceptions?${query.toString()}`)
  if (!response.ok) {
    throw new Error(`Failed to fetch exceptions: ${response.statusText}`)
  }
  return response.json()
}

export async function resolveException(id, newStatus, notes) {
  const response = await fetch(`${API_BASE}/exceptions/${id}/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: newStatus, resolution_notes: notes })
  })
  if (!response.ok) {
    throw new Error(`Failed to resolve exception: ${response.statusText}`)
  }
  return response.json()
}

export async function fetchAccuracyReport() {
  const response = await fetch(`${API_BASE}/accuracy-report`)
  if (!response.ok) {
    throw new Error(`Failed to fetch accuracy report: ${response.statusText}`)
  }
  return response.json()
}

export async function runAccuracyBenchmark() {
  const response = await fetch(`${API_BASE}/accuracy-report/run`, {
    method: 'POST'
  })
  if (!response.ok) {
    throw new Error(`Failed to run benchmark: ${response.statusText}`)
  }
  return response.json()
}

export async function fetchMetrics() {
  const response = await fetch(`${API_BASE}/metrics`)
  if (!response.ok) {
    throw new Error(`Failed to fetch metrics: ${response.statusText}`)
  }
  return response.json()
}

export async function fetchSummaryKPIs() {
  const response = await fetch(`${API_BASE}/summary`)
  if (!response.ok) {
    throw new Error(`Failed to fetch summary: ${response.statusText}`)
  }
  return response.json()
}
