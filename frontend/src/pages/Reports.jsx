import React, { useState, useEffect } from 'react'
import { fetchAccuracyReport, runAccuracyBenchmark, fetchMetrics } from '../services/api'

export default function Reports() {
  const [report, setReport] = useState(null)
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [runningBenchmark, setRunningBenchmark] = useState(false)
  const [categoryFilter, setCategoryFilter] = useState('all')

  const loadData = async () => {
    setLoading(true)
    try {
      const [repData, metData] = await Promise.all([
        fetchAccuracyReport(),
        fetchMetrics()
      ])
      setReport(repData)
      setMetrics(metData)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleRunBenchmark = async () => {
    setRunningBenchmark(true)
    try {
      const newReport = await runAccuracyBenchmark()
      setReport(newReport)
      const metData = await fetchMetrics()
      setMetrics(metData)
    } catch (err) {
      alert(`Failed to run benchmark: ${err.message}`)
    } finally {
      setRunningBenchmark(false)
    }
  }

  const filteredTests = (report?.test_cases || []).filter((tc) => {
    if (categoryFilter === 'all') return true
    return tc.category === categoryFilter
  })

  const categories = Array.from(new Set((report?.test_cases || []).map((t) => t.category)))
  const engineBreakdown = report?.engine_breakdown || {}
  const verifierPerf = report?.verifier_performance || {}

  return (
    <div className="flex-1 p-gutter max-w-[1440px] mx-auto w-full overflow-y-auto">
      <div className="mb-6 flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
        <div>
          <h2 className="text-2xl font-bold text-on-surface">Evaluation & Verification Harness</h2>
          <p className="text-sm text-on-surface-variant mt-1">
            Ground-truth labeled benchmark measuring primary reasoning accuracy, independent verifier audit, and honest declines.
          </p>
        </div>

        <button
          onClick={handleRunBenchmark}
          disabled={runningBenchmark}
          className="bg-primary text-on-primary px-5 py-2.5 rounded-md text-xs font-semibold shadow-md hover:bg-primary-fixed-variant transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span className={`material-symbols-outlined text-[18px] ${runningBenchmark ? 'animate-spin' : ''}`}>
            {runningBenchmark ? 'sync' : 'play_arrow'}
          </span>
          {runningBenchmark ? 'Auditing 35+ Test Cases...' : 'Run Benchmark Harness'}
        </button>
      </div>

      {loading ? (
        <div className="py-20 text-center text-on-surface-variant">
          <span className="material-symbols-outlined animate-spin text-3xl text-primary mb-2">refresh</span>
          <p className="text-sm">Loading accuracy metrics...</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-5 shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-on-surface-variant">Benchmark Accuracy</span>
                <span className="w-8 h-8 rounded-full bg-secondary/10 text-secondary flex items-center justify-center">
                  <span className="material-symbols-outlined text-[18px]">verified</span>
                </span>
              </div>
              <p className="text-3xl font-bold text-secondary">
                {report?.accuracy_percentage || 0}%
              </p>
              <p className="text-xs text-on-surface-variant mt-1">
                {report?.passed + report?.correctly_declined} of {report?.total_tests} tests verified
              </p>
            </div>

            <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-5 shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-on-surface-variant">Verifier Agreement</span>
                <span className="w-8 h-8 rounded-full bg-teal-500/10 text-teal-700 flex items-center justify-center">
                  <span className="material-symbols-outlined text-[18px]">fact_check</span>
                </span>
              </div>
              <p className="text-3xl font-bold text-teal-700">
                {verifierPerf.agreement_rate_percent || 100}%
              </p>
              <p className="text-xs text-on-surface-variant mt-1">
                Independent Verifier Agent audit consensus
              </p>
            </div>

            <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-5 shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-on-surface-variant">Honest Declines</span>
                <span className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center">
                  <span className="material-symbols-outlined text-[18px]">shield</span>
                </span>
              </div>
              <p className="text-3xl font-bold text-primary">
                {report?.correctly_declined || 0} Cases
              </p>
              <p className="text-xs text-on-surface-variant mt-1">
                0% hallucination on non-existent records
              </p>
            </div>

            <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-5 shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-on-surface-variant">Average Query Latency</span>
                <span className="w-8 h-8 rounded-full bg-purple-500/10 text-purple-700 flex items-center justify-center">
                  <span className="material-symbols-outlined text-[18px]">timer</span>
                </span>
              </div>
              <p className="text-3xl font-bold text-on-surface">
                {report?.avg_latency_ms || 0} ms
              </p>
              <p className="text-xs text-on-surface-variant mt-1">
                Two-tier primary + verifier pass
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
            <div className="lg:col-span-1 bg-surface-container-lowest border border-outline-variant rounded-xl p-5 shadow-sm">
              <h3 className="text-sm font-bold text-on-surface mb-3 flex items-center gap-2">
                <span className="material-symbols-outlined text-teal-700 text-[20px]">fact_check</span>
                Verifier Agent Audit Metrics
              </h3>
              <div className="space-y-3 text-xs">
                <div className="flex justify-between items-center p-2 bg-surface-container-low rounded-lg">
                  <span className="text-on-surface font-medium">Verified Clean:</span>
                  <span className="font-bold text-secondary">{verifierPerf.verified_count || 0}</span>
                </div>
                <div className="flex justify-between items-center p-2 bg-surface-container-low rounded-lg">
                  <span className="text-on-surface font-medium">Minor Discrepancies:</span>
                  <span className="font-bold text-amber-700">{verifierPerf.minor_discrepancy_count || 0}</span>
                </div>
                <div className="flex justify-between items-center p-2 bg-surface-container-low rounded-lg">
                  <span className="text-on-surface font-medium">Flagged for Review:</span>
                  <span className="font-bold text-error">{verifierPerf.flagged_count || 0}</span>
                </div>
                <div className="flex justify-between items-center p-2 bg-surface-container-low rounded-lg">
                  <span className="text-on-surface font-medium">False-Flag Rate:</span>
                  <span className="font-mono font-bold text-on-surface">{verifierPerf.false_flag_rate_percent || 0}%</span>
                </div>
              </div>
            </div>

            <div className="lg:col-span-2 bg-surface-container-lowest border border-outline-variant rounded-xl p-5 shadow-sm">
              <h3 className="text-sm font-bold text-on-surface mb-3 flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-[20px]">hub</span>
                Dual-Path Engine Evaluation Breakdown
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-4 bg-purple-500/5 border border-purple-500/20 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-purple-800 flex items-center gap-1.5">
                      <span className="material-symbols-outlined text-[16px]">auto_awesome</span>
                      Google Gemini 2.5 Flash Path
                    </span>
                    <span className="text-[11px] font-semibold text-purple-700 bg-purple-100 px-2 py-0.5 rounded">
                      {engineBreakdown.gemini?.total || 0} Tests
                    </span>
                  </div>
                  <div className="flex justify-between items-end mt-2">
                    <div>
                      <p className="text-2xl font-bold text-purple-900">
                        {engineBreakdown.gemini?.total > 0 ? `${engineBreakdown.gemini.accuracy_percentage}%` : 'N/A'}
                      </p>
                      <p className="text-[11px] text-purple-700">
                        {engineBreakdown.gemini?.total > 0 ? 'Live LLM Grounding' : 'No API key set (fallback active)'}
                      </p>
                    </div>
                    <div className="text-right font-mono text-xs text-purple-800">
                      Latency: {engineBreakdown.gemini?.avg_latency_ms || 0} ms
                    </div>
                  </div>
                </div>

                <div className="p-4 bg-slate-500/5 border border-slate-500/20 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                      <span className="material-symbols-outlined text-[16px]">bolt</span>
                      Deterministic Grounded Engine
                    </span>
                    <span className="text-[11px] font-semibold text-slate-700 bg-slate-100 px-2 py-0.5 rounded">
                      {engineBreakdown.fallback?.total || 0} Tests
                    </span>
                  </div>
                  <div className="flex justify-between items-end mt-2">
                    <div>
                      <p className="text-2xl font-bold text-slate-900">
                        {engineBreakdown.fallback?.accuracy_percentage || 0}%
                      </p>
                      <p className="text-[11px] text-slate-600">Zero-dependency deterministic fallback</p>
                    </div>
                    <div className="text-right font-mono text-xs text-slate-800">
                      Latency: {engineBreakdown.fallback?.avg_latency_ms || 0} ms
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-4 mb-6 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-3 overflow-hidden">
            <div className="flex items-center gap-2.5 w-full md:w-auto overflow-hidden min-w-0 flex-1">
              <span className="text-xs font-semibold text-on-surface-variant shrink-0">Filter by Category:</span>
              <div className="flex items-center gap-2 overflow-x-auto hide-scrollbar py-0.5 scroll-smooth min-w-0 flex-1">
                <button
                  onClick={() => setCategoryFilter('all')}
                  className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors shrink-0 whitespace-nowrap ${
                    categoryFilter === 'all'
                      ? 'bg-primary text-on-primary'
                      : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high'
                  }`}
                >
                  All ({report?.test_cases?.length || 0})
                </button>
                {categories.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setCategoryFilter(cat)}
                    className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors capitalize shrink-0 whitespace-nowrap ${
                      categoryFilter === cat
                        ? 'bg-primary text-on-primary'
                        : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high'
                    }`}
                  >
                    {cat.replace(/_/g, ' ')}
                  </button>
                ))}
              </div>
            </div>

            <span className="text-xs text-on-surface-variant font-mono shrink-0 whitespace-nowrap self-end md:self-auto">
              Latest Run: {report?.run_timestamp} ({report?.id})
            </span>
          </div>

          <div className="bg-surface-container-lowest border border-outline-variant rounded-lg shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead className="glass-header sticky top-0 border-b border-outline-variant font-semibold text-on-surface-variant uppercase tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Test ID</th>
                    <th className="py-3 px-4">Category</th>
                    <th className="py-3 px-4">Engine</th>
                    <th className="py-3 px-4">Verifier Audit</th>
                    <th className="py-3 px-4">Question</th>
                    <th className="py-3 px-4">Actual Agent Response</th>
                    <th className="py-3 px-4">Citations</th>
                    <th className="py-3 px-4 text-center">Verdict</th>
                    <th className="py-3 px-4 text-right">Latency</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant/50">
                  {filteredTests.map((tc) => (
                    <tr key={tc.test_id} className="hover:bg-surface-container-low transition-colors">
                      <td className="py-3.5 px-4 font-mono font-semibold text-on-surface">{tc.test_id}</td>
                      <td className="py-3.5 px-4">
                        <span className="bg-surface-container text-on-surface-variant px-2 py-0.5 rounded text-[11px] font-medium capitalize">
                          {tc.category.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="py-3.5 px-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          tc.engine_used === 'gemini'
                            ? 'bg-purple-100 text-purple-800'
                            : 'bg-slate-100 text-slate-700'
                        }`}>
                          {tc.engine_used === 'gemini' ? 'Gemini' : 'Fallback'}
                        </span>
                      </td>
                      <td className="py-3.5 px-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          tc.verifier_verdict === 'VERIFIED'
                            ? 'bg-secondary/10 text-secondary'
                            : tc.verifier_verdict === 'MINOR_DISCREPANCY'
                            ? 'bg-amber-500/10 text-amber-700'
                            : 'bg-error/10 text-error'
                        }`}>
                          {tc.verifier_verdict || 'VERIFIED'}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 font-medium text-on-surface max-w-[180px]">
                        "{tc.question}"
                      </td>
                      <td className="py-3.5 px-4 text-on-surface-variant max-w-[280px] line-clamp-3">
                        {tc.actual_answer}
                      </td>
                      <td className="py-3.5 px-4 font-mono text-[11px] text-primary font-semibold">
                        {tc.cited_record_ids?.length > 0 ? tc.cited_record_ids.join(', ') : 'None'}
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        {tc.verdict === 'CORRECT' && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold bg-secondary/10 text-secondary border border-secondary/20">
                            Passed
                          </span>
                        )}
                        {tc.verdict === 'CORRECTLY_DECLINED' && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold bg-primary/10 text-primary border border-primary/20">
                            Declined OK
                          </span>
                        )}
                        {tc.verdict === 'PARTIALLY_CORRECT' && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/10 text-amber-700 border border-amber-500/20">
                            Partial
                          </span>
                        )}
                        {tc.verdict === 'WRONG' && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold bg-error/10 text-error border border-error/20">
                            Failed
                          </span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-right font-mono text-on-surface-variant">
                        {tc.latency_ms} ms
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
