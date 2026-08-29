import React, { useState, useEffect } from 'react'
import { fetchSummaryKPIs, fetchMetrics, fetchExceptions } from '../services/api'
import StatusBadge from '../components/StatusBadge'

export default function Dashboard({ onNavigateToChat, onNavigateToTransactions, onNavigateToExceptions }) {
  const [summary, setSummary] = useState(null)
  const [metrics, setMetrics] = useState(null)
  const [recentExceptions, setRecentExceptions] = useState([])
  const [loading, setLoading] = useState(true)
  const [quickInput, setQuickInput] = useState('')

  const loadData = async () => {
    setLoading(true)
    try {
      const [sumData, metData, excData] = await Promise.all([
        fetchSummaryKPIs(),
        fetchMetrics(),
        fetchExceptions('UNRESOLVED')
      ])
      setSummary(sumData)
      setMetrics(metData)
      setRecentExceptions(excData.slice(0, 4))
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleQuickSubmit = (e) => {
    e.preventDefault()
    if (quickInput.trim()) {
      onNavigateToChat(quickInput.trim())
    }
  }

  return (
    <div className="flex-1 p-gutter max-w-[1440px] mx-auto w-full overflow-y-auto">
      <div className="mb-6 flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
        <div>
          <h2 className="text-2xl font-bold text-on-surface">Finance Controller Dashboard</h2>
          <p className="text-sm text-on-surface-variant mt-1">
            Real-time settlement reconciliation status, payout pipelines, and AI reasoning metrics.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => onNavigateToChat("What is my pending payout for last week?")}
            className="bg-primary text-on-primary px-4 py-2 rounded-md text-xs font-semibold shadow-sm hover:bg-primary-fixed-variant transition-colors flex items-center gap-2"
          >
            <span className="material-symbols-outlined text-[16px]">chat_bubble</span>
            Ask SettleSense
          </button>
        </div>
      </div>

      {loading ? (
        <div className="py-20 text-center text-on-surface-variant">
          <span className="material-symbols-outlined animate-spin text-3xl text-primary mb-2">refresh</span>
          <p className="text-sm">Loading financial data...</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-5 shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-on-surface-variant">Total Settled Volume</span>
                <span className="w-8 h-8 rounded-full bg-secondary/10 text-secondary flex items-center justify-center">
                  <span className="material-symbols-outlined text-[18px]">account_balance</span>
                </span>
              </div>
              <p className="text-2xl font-bold text-on-surface">
                ₹{Number(summary?.total_settled_amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </p>
              <p className="text-xs text-secondary mt-1 font-medium flex items-center gap-1">
                <span className="material-symbols-outlined text-[14px]">check</span>
                {summary?.matched_count || 0} reconciled transactions
              </p>
            </div>

            <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-5 shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-on-surface-variant">Pending Payout Pipeline</span>
                <span className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center">
                  <span className="material-symbols-outlined text-[18px]">hourglass_top</span>
                </span>
              </div>
              <p className="text-2xl font-bold text-primary">
                ₹{Number(summary?.pending_payout_amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </p>
              <p className="text-xs text-on-surface-variant mt-1">
                Awaiting upcoming morning batch cycles
              </p>
            </div>

            <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-5 shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-on-surface-variant">Reconciliation Match Rate</span>
                <span className="w-8 h-8 rounded-full bg-secondary/10 text-secondary flex items-center justify-center">
                  <span className="material-symbols-outlined text-[18px]">verified_user</span>
                </span>
              </div>
              <p className="text-2xl font-bold text-secondary">
                {summary?.reconciliation_rate || 0}%
              </p>
              <p className="text-xs text-on-surface-variant mt-1">
                Across {summary?.total_transactions_count || 0} total ledger records
              </p>
            </div>

            <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-5 shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-on-surface-variant">Active Exceptions</span>
                <span className="w-8 h-8 rounded-full bg-error/10 text-error flex items-center justify-center">
                  <span className="material-symbols-outlined text-[18px]">report_problem</span>
                </span>
              </div>
              <p className="text-2xl font-bold text-error">
                {summary?.exception_count || 0}
              </p>
              <p className="text-xs text-error mt-1 font-medium">
                {metrics?.unresolved_exception_count || 0} requiring operational review
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
            <div className="lg:col-span-2 bg-surface-container-lowest border border-outline-variant rounded-xl p-5 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-base font-bold text-on-surface">Ask SettleSense Quick Terminal</h3>
                  <p className="text-xs text-on-surface-variant mt-0.5">
                    Query settlement records, explain holds, or trace bank UTRs with instant citations.
                  </p>
                </div>
                <span className="text-xs font-mono bg-surface-container px-2 py-1 rounded text-primary font-semibold">
                  Avg Latency: {summary?.avg_query_latency_ms || 14}ms
                </span>
              </div>

              <form onSubmit={handleQuickSubmit} className="mb-4">
                <div className="relative flex items-center">
                  <span className="material-symbols-outlined absolute left-3 text-on-surface-variant">
                    search
                  </span>
                  <input
                    type="text"
                    value={quickInput}
                    onChange={(e) => setQuickInput(e.target.value)}
                    placeholder="e.g. Why didn't order #4521 settle yesterday?"
                    className="w-full pl-10 pr-24 py-2.5 bg-surface-container-low border border-outline-variant rounded-lg text-xs text-on-surface outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                  />
                  <button
                    type="submit"
                    className="absolute right-1.5 px-3 py-1.5 bg-primary text-on-primary text-xs font-semibold rounded-md hover:bg-primary-fixed-variant"
                  >
                    Ask AI
                  </button>
                </div>
              </form>

              <div className="flex flex-wrap gap-2">
                <span className="text-[11px] text-on-surface-variant font-medium py-1">Quick Prompts:</span>
                {[
                  "Why didn't order #4521 settle?",
                  "Trace BOA-44910-YY",
                  "Pending payouts for last week",
                  "Why is ORD-9921 on hold?"
                ].map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => onNavigateToChat(q)}
                    className="text-[11px] bg-surface-container hover:bg-surface-container-high text-on-surface px-2.5 py-1 rounded-full border border-outline-variant/60 transition-colors"
                  >
                    "{q}"
                  </button>
                ))}
              </div>
            </div>

            <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-5 shadow-sm flex flex-col justify-between">
              <div>
                <h3 className="text-base font-bold text-on-surface mb-1">Reconciliation Health</h3>
                <p className="text-xs text-on-surface-variant mb-4">
                  Ledger distribution across settlement statuses
                </p>

                <div className="space-y-3 text-xs">
                  <div className="flex justify-between items-center">
                    <span className="flex items-center gap-1.5 text-on-surface">
                      <span className="w-2.5 h-2.5 rounded-full bg-secondary"></span>
                      Matched & Settled
                    </span>
                    <span className="font-semibold">{summary?.matched_count || 0}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="flex items-center gap-1.5 text-on-surface">
                      <span className="w-2.5 h-2.5 rounded-full bg-primary"></span>
                      Pending Cycle
                    </span>
                    <span className="font-semibold">
                      {(summary?.total_transactions_count || 0) - (summary?.matched_count || 0) - (summary?.exception_count || 0)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="flex items-center gap-1.5 text-on-surface">
                      <span className="w-2.5 h-2.5 rounded-full bg-error"></span>
                      Exceptions & Declines
                    </span>
                    <span className="font-semibold text-error">{summary?.exception_count || 0}</span>
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-outline-variant mt-4">
                <button
                  onClick={onNavigateToTransactions}
                  className="w-full text-center text-xs font-semibold text-primary hover:underline"
                >
                  View Full Transaction Table →
                </button>
              </div>
            </div>
          </div>

          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-5 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-base font-bold text-on-surface">Active Failure & Exception Queue</h3>
                <p className="text-xs text-on-surface-variant mt-0.5">
                  Queries and transactions flagged for finance operations review
                </p>
              </div>
              <button
                onClick={onNavigateToExceptions}
                className="text-xs font-semibold text-primary hover:underline"
              >
                View All Exceptions ({metrics?.unresolved_exception_count || 0}) →
              </button>
            </div>

            {recentExceptions.length === 0 ? (
              <p className="text-xs text-on-surface-variant py-4 text-center">No active exceptions pending review.</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {recentExceptions.map((exc) => (
                  <div
                    key={exc.id}
                    className="p-3 bg-surface-container-low border border-outline-variant rounded-lg text-xs"
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-mono font-bold text-primary">{exc.id}</span>
                      <span className="text-[10px] bg-red-500/10 text-red-600 border border-red-500/20 px-1.5 py-0.5 rounded font-semibold">
                        {exc.exception_type}
                      </span>
                    </div>
                    <p className="font-semibold text-on-surface mb-1 truncate">"{exc.query_text}"</p>
                    <p className="text-[11px] text-on-surface-variant line-clamp-2">{exc.reason}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
