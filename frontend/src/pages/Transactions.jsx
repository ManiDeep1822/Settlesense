import React, { useState, useEffect } from 'react'
import { fetchTransactions } from '../services/api'
import StatusBadge from '../components/StatusBadge'

export default function Transactions({ onAskAboutTransaction }) {
  const [data, setData] = useState({ items: [], total: 0, page: 1, total_pages: 1 })
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('all')
  const [search, setSearch] = useState('')
  const [minAmount, setMinAmount] = useState('')
  const [maxAmount, setMaxAmount] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  const loadData = async (targetPage = page) => {
    setLoading(true)
    try {
      const res = await fetchTransactions({
        page: targetPage,
        pageSize: 12,
        status,
        search,
        minAmount: minAmount ? parseFloat(minAmount) : undefined,
        maxAmount: maxAmount ? parseFloat(maxAmount) : undefined,
        startDate: startDate || undefined,
        endDate: endDate || undefined
      })
      setData(res)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData(1)
    setPage(1)
  }, [status, startDate, endDate])

  const handleApplyFilters = (e) => {
    e?.preventDefault()
    loadData(1)
    setPage(1)
  }

  const exportCSV = () => {
    const headers = ['Transaction ID,Order Ref,Amount,Fee,Tax,Net Amount,Status,Date,Bank UTR,Failure Reason\n']
    const rows = data.items.map((t) =>
      `"${t.id}","${t.order_ref}",${t.amount},${t.fee},${t.tax},${t.net_amount},"${t.status}","${t.created_at}","${t.bank_ref || ''}","${(t.failure_reason || '').replace(/"/g, '""')}"`
    )
    const blob = new Blob([headers.concat(rows).join('\n')], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `settlesense_transactions_${Date.now()}.csv`
    a.click()
  }

  return (
    <div className="flex-1 p-gutter max-w-[1440px] mx-auto w-full overflow-y-auto">
      <div className="mb-6 flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
        <div>
          <h2 className="text-2xl font-bold text-on-surface">Transactions & Settlements</h2>
          <p className="text-sm text-on-surface-variant mt-1">
            Review, filter, and inspect structured reconciliation records from the settlement ledger.
          </p>
        </div>
        <button
          onClick={exportCSV}
          className="bg-primary text-on-primary px-4 py-2 rounded-md text-xs font-semibold shadow-sm hover:opacity-90 transition-opacity flex items-center gap-1.5"
        >
          <span className="material-symbols-outlined text-[16px]">download</span>
          Export CSV
        </button>
      </div>

      <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-4 mb-6 shadow-sm">
        <form onSubmit={handleApplyFilters} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 items-end">
          <div>
            <label className="block text-xs font-semibold text-on-surface-variant mb-1">Search Identifier</label>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="TXN-..., ORD-..., UTR..."
              className="w-full px-3 py-1.5 border border-outline-variant rounded-md text-xs font-mono focus:border-primary outline-none bg-transparent"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-on-surface-variant mb-1">Settlement Status</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="w-full px-3 py-1.5 border border-outline-variant rounded-md text-xs focus:border-primary outline-none bg-transparent"
            >
              <option value="all">All Statuses</option>
              <option value="matched">Matched</option>
              <option value="exception">Exception</option>
              <option value="pending">Pending</option>
              <option value="delayed">Delayed / On Hold</option>
              <option value="declined">Declined</option>
              <option value="unmatched">Unmatched</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-on-surface-variant mb-1">Date Range</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full px-3 py-1.5 border border-outline-variant rounded-md text-xs focus:border-primary outline-none bg-transparent"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-on-surface-variant mb-1">Amount Range (₹)</label>
            <div className="flex items-center gap-1.5">
              <input
                type="number"
                value={minAmount}
                onChange={(e) => setMinAmount(e.target.value)}
                placeholder="Min"
                className="w-full px-2 py-1.5 border border-outline-variant rounded-md text-xs focus:border-primary outline-none bg-transparent"
              />
              <span className="text-on-surface-variant">-</span>
              <input
                type="number"
                value={maxAmount}
                onChange={(e) => setMaxAmount(e.target.value)}
                placeholder="Max"
                className="w-full px-2 py-1.5 border border-outline-variant rounded-md text-xs focus:border-primary outline-none bg-transparent"
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              className="w-full bg-surface-container border border-outline-variant text-on-surface py-2 rounded-md text-xs font-semibold hover:bg-surface-container-high transition-colors"
            >
              Apply Filters
            </button>
          </div>
        </form>
      </div>

      <div className="bg-surface-container-lowest border border-outline-variant rounded-lg shadow-sm overflow-hidden relative">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead className="glass-header sticky top-0 border-b border-outline-variant z-10 font-semibold text-on-surface-variant uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4">Transaction ID</th>
                <th className="py-3 px-4">Order Ref</th>
                <th className="py-3 px-4 text-right">Gross Amount</th>
                <th className="py-3 px-4 text-right">Net Payout</th>
                <th className="py-3 px-4">Settlement Date</th>
                <th className="py-3 px-4">Bank UTR / Ref</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/50">
              {loading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-on-surface-variant">
                    <span className="material-symbols-outlined animate-spin text-2xl text-primary mb-2">refresh</span>
                    <p>Loading transactions...</p>
                  </td>
                </tr>
              ) : data.items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-on-surface-variant">
                    No transactions matching the selected criteria.
                  </td>
                </tr>
              ) : (
                data.items.map((t) => (
                  <tr
                    key={t.id}
                    className={`hover:bg-surface-container-low transition-colors group ${
                      t.status === 'exception' ? 'bg-error-container/15' : ''
                    }`}
                  >
                    <td className="py-3.5 px-4 font-mono font-medium text-on-surface group-hover:text-primary transition-colors">
                      {t.id}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-on-surface-variant">
                      {t.order_ref}
                    </td>
                    <td className="py-3.5 px-4 text-right font-medium text-on-surface">
                      ₹{t.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3.5 px-4 text-right font-medium text-on-surface">
                      ₹{t.net_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3.5 px-4 text-on-surface-variant">
                      {t.settlement_date || (
                        <span className="text-outline italic">Pending Cycle</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-[11px] text-on-surface-variant">
                      {t.bank_ref || <span className="text-outline italic">None</span>}
                    </td>
                    <td className="py-3.5 px-4">
                      <StatusBadge status={t.status} />
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <button
                        onClick={() => onAskAboutTransaction && onAskAboutTransaction(`What is the settlement breakdown and status for transaction ${t.id} (Order ${t.order_ref})?`)}
                        className="text-primary hover:bg-primary/10 px-2 py-1 rounded text-xs font-semibold transition-colors flex items-center gap-1 mx-auto"
                        title="Ask SettleSense about this transaction"
                      >
                        <span className="material-symbols-outlined text-[14px]">chat_bubble</span>
                        Ask AI
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="px-4 py-3 border-t border-outline-variant bg-surface-bright flex items-center justify-between text-xs text-on-surface-variant">
          <span>
            Showing {data.items.length > 0 ? (page - 1) * 12 + 1 : 0} to{' '}
            {Math.min(page * 12, data.total)} of {data.total} records
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                if (page > 1) {
                  setPage(page - 1)
                  loadData(page - 1)
                }
              }}
              disabled={page <= 1 || loading}
              className="p-1 border border-outline-variant rounded hover:bg-surface-container disabled:opacity-40"
            >
              <span className="material-symbols-outlined text-[18px]">chevron_left</span>
            </button>
            <span className="font-medium">
              Page {page} of {data.total_pages}
            </span>
            <button
              onClick={() => {
                if (page < data.total_pages) {
                  setPage(page + 1)
                  loadData(page + 1)
                }
              }}
              disabled={page >= data.total_pages || loading}
              className="p-1 border border-outline-variant rounded hover:bg-surface-container disabled:opacity-40"
            >
              <span className="material-symbols-outlined text-[18px]">chevron_right</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
