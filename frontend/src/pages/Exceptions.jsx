import React, { useState, useEffect } from 'react'
import { fetchExceptions, resolveException } from '../services/api'

export default function Exceptions({ onAskAboutException }) {
  const [exceptions, setExceptions] = useState([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('all')
  const [selectedException, setSelectedException] = useState(null)
  const [resolutionNotes, setResolutionNotes] = useState('')

  const loadExceptions = async () => {
    setLoading(true)
    try {
      const data = await fetchExceptions(statusFilter)
      setExceptions(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadExceptions()
  }, [statusFilter])

  const handleResolve = async (id, newStatus) => {
    try {
      await resolveException(id, newStatus, resolutionNotes || 'Reviewed by Finance Controller')
      setSelectedException(null)
      setResolutionNotes('')
      loadExceptions()
    } catch (err) {
      alert(`Failed to update exception: ${err.message}`)
    }
  }

  const getTypeBadge = (type) => {
    const t = (type || '').toUpperCase()
    if (t === 'RECORD_NOT_FOUND') {
      return (
        <span className="bg-red-500/10 text-red-600 border border-red-500/20 px-2 py-0.5 rounded text-[11px] font-semibold">
          Record Not Found
        </span>
      )
    }
    if (t === 'SETTLEMENT_HOLD') {
      return (
        <span className="bg-amber-500/10 text-amber-700 border border-amber-500/20 px-2 py-0.5 rounded text-[11px] font-semibold">
          Settlement Hold
        </span>
      )
    }
    if (t === 'BANK_UTR_MISMATCH') {
      return (
        <span className="bg-purple-500/10 text-purple-700 border border-purple-500/20 px-2 py-0.5 rounded text-[11px] font-semibold">
          Bank UTR Mismatch
        </span>
      )
    }
    if (t === 'VERIFIER_FLAGGED') {
      return (
        <span className="bg-red-500/15 text-red-700 border border-red-500/30 px-2 py-0.5 rounded text-[11px] font-bold flex items-center gap-1">
          <span className="material-symbols-outlined text-[13px]">gavel</span>
          Verifier Flagged
        </span>
      )
    }
    if (t === 'DECLINED_TRANSACTION') {
      return (
        <span className="bg-error/10 text-error border border-error/20 px-2 py-0.5 rounded text-[11px] font-semibold">
          Declined Payment
        </span>
      )
    }
    return (
      <span className="bg-outline/10 text-on-surface-variant border border-outline/20 px-2 py-0.5 rounded text-[11px] font-semibold">
        {type}
      </span>
    )
  }

  return (
    <div className="flex-1 p-gutter max-w-[1440px] mx-auto w-full overflow-y-auto">
      <div className="mb-6 flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
        <div>
          <h2 className="text-2xl font-bold text-on-surface">Exceptions & Failure Ledger</h2>
          <p className="text-sm text-on-surface-variant mt-1">
            Transparent log of unanswerable queries, non-existent orders, mismatched bank references, and reconciliation anomalies.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 border border-outline-variant rounded-md text-xs font-semibold focus:border-primary outline-none bg-surface-container-lowest"
          >
            <option value="all">All Exceptions</option>
            <option value="UNRESOLVED">Unresolved</option>
            <option value="RESOLVED">Resolved</option>
          </select>
          <button
            onClick={loadExceptions}
            className="p-1.5 border border-outline-variant rounded-md hover:bg-surface-container text-on-surface-variant"
            title="Refresh Exceptions"
          >
            <span className="material-symbols-outlined text-[18px]">refresh</span>
          </button>
        </div>
      </div>

      {loading ? (
        <div className="py-20 text-center text-on-surface-variant">
          <span className="material-symbols-outlined animate-spin text-3xl text-primary mb-2">refresh</span>
          <p className="text-sm">Loading exceptions ledger...</p>
        </div>
      ) : exceptions.length === 0 ? (
        <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-12 text-center">
          <div className="w-12 h-12 rounded-full bg-secondary/10 text-secondary flex items-center justify-center mx-auto mb-3">
            <span className="material-symbols-outlined text-2xl">check_circle</span>
          </div>
          <h3 className="text-base font-bold text-on-surface">No Exceptions Logged</h3>
          <p className="text-xs text-on-surface-variant mt-1">
            When queries encounter missing data or ambiguity, they are automatically logged here for finance operations review.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {exceptions.map((exc) => (
            <div
              key={exc.id}
              className="bg-surface-container-lowest border border-outline-variant rounded-lg p-4 shadow-sm hover:border-primary/40 transition-colors"
            >
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 mb-3">
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-xs text-on-surface">{exc.id}</span>
                  {getTypeBadge(exc.exception_type)}
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      exc.status === 'UNRESOLVED'
                        ? 'bg-amber-500/10 text-amber-700 border border-amber-500/20'
                        : 'bg-secondary/10 text-secondary border border-secondary/20'
                    }`}
                  >
                    {exc.status}
                  </span>
                </div>
                <span className="text-[11px] text-on-surface-variant">{exc.timestamp}</span>
              </div>

              <div className="bg-surface-container-low p-3 rounded-md mb-3">
                <p className="text-xs text-on-surface-variant font-medium mb-0.5">User Query:</p>
                <p className="text-sm font-semibold text-on-surface">"{exc.query_text}"</p>
              </div>

              <div className="mb-3">
                <p className="text-xs text-on-surface-variant font-medium mb-0.5">Root Cause / Declination Reason:</p>
                <p className="text-xs text-on-surface leading-relaxed">{exc.reason}</p>
              </div>

              {exc.candidate_record_ids && (
                <div className="mb-3 flex items-center gap-2 text-xs">
                  <span className="text-on-surface-variant font-medium">Candidate IDs:</span>
                  <span className="font-mono text-primary font-semibold">{exc.candidate_record_ids}</span>
                </div>
              )}

              {exc.resolution_notes && (
                <div className="mb-3 p-2 bg-surface-container rounded text-xs text-on-surface">
                  <span className="font-semibold text-secondary">Resolution Notes: </span>
                  {exc.resolution_notes}
                </div>
              )}

              <div className="flex items-center justify-between pt-3 border-t border-outline-variant/60">
                <button
                  onClick={() => onAskAboutException && onAskAboutException(exc.query_text)}
                  className="text-primary hover:underline text-xs font-semibold flex items-center gap-1"
                >
                  <span className="material-symbols-outlined text-[14px]">replay</span>
                  Re-evaluate in Chat
                </button>

                {exc.status === 'UNRESOLVED' ? (
                  <button
                    onClick={() => setSelectedException(exc)}
                    className="bg-primary text-on-primary px-3 py-1 rounded text-xs font-semibold hover:bg-primary-fixed-variant transition-colors"
                  >
                    Resolve Exception
                  </button>
                ) : (
                  <button
                    onClick={() => handleResolve(exc.id, 'UNRESOLVED')}
                    className="text-xs text-on-surface-variant hover:text-primary font-semibold"
                  >
                    Reopen
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedException && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-surface-container-lowest rounded-xl max-w-lg w-full p-6 border border-outline-variant shadow-2xl">
            <h3 className="text-lg font-bold text-on-surface mb-2">Resolve Exception {selectedException.id}</h3>
            <p className="text-xs text-on-surface-variant mb-4">
              Enter operational audit notes regarding how this exception or unanswerable query was addressed.
            </p>

            <textarea
              value={resolutionNotes}
              onChange={(e) => setResolutionNotes(e.target.value)}
              placeholder="e.g. Verified with merchant operations team; transaction order #99999 was never created in payment gateway."
              rows={3}
              className="w-full p-3 border border-outline-variant rounded-md text-xs text-on-surface outline-none focus:border-primary mb-4"
            />

            <div className="flex justify-end gap-2">
              <button
                onClick={() => setSelectedException(null)}
                className="px-4 py-2 border border-outline-variant rounded-md text-xs font-semibold text-on-surface hover:bg-surface-container"
              >
                Cancel
              </button>
              <button
                onClick={() => handleResolve(selectedException.id, 'RESOLVED')}
                className="px-4 py-2 bg-secondary text-on-primary rounded-md text-xs font-semibold hover:opacity-90"
              >
                Mark as Resolved
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
