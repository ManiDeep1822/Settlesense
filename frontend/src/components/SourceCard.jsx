import React from 'react'
import StatusBadge from './StatusBadge'

export default function SourceCard({ record }) {
  if (!record) return null

  const isBatch = record.id && record.id.startsWith('SETTLE-')

  return (
    <div className="p-3 border-t border-outline-variant/60 bg-surface-container-lowest text-xs">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 items-center">
        <div>
          <p className="text-[11px] text-on-surface-variant font-medium mb-0.5">
            {isBatch ? 'Settlement Batch' : 'Transaction ID'}
          </p>
          <p className="font-mono font-semibold text-on-surface">{record.id}</p>
          {record.order_ref && !isBatch && (
            <p className="text-[11px] text-on-surface-variant font-mono">{record.order_ref}</p>
          )}
        </div>

        <div>
          <p className="text-[11px] text-on-surface-variant font-medium mb-0.5">Gross Amount</p>
          <p className="font-semibold text-on-surface">₹{Number(record.amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</p>
          {record.fee > 0 && (
            <p className="text-[10px] text-on-surface-variant">Fee: ₹{record.fee.toFixed(2)}</p>
          )}
        </div>

        <div>
          <p className="text-[11px] text-on-surface-variant font-medium mb-0.5">Settlement Date</p>
          <p className="text-on-surface">{record.settlement_date || 'Awaiting Cycle'}</p>
          {record.bank_ref && (
            <p className="font-mono text-[10px] text-on-surface-variant truncate max-w-[130px]" title={record.bank_ref}>
              UTR: {record.bank_ref}
            </p>
          )}
        </div>

        <div className="flex flex-col items-end justify-center">
          <StatusBadge status={record.status} />
          {record.refund_amount > 0 && (
            <span className="text-[10px] text-tertiary font-semibold mt-1">
              Refund: ₹{record.refund_amount.toFixed(2)}
            </span>
          )}
        </div>
      </div>

      {record.failure_reason && (
        <div className="mt-2.5 pt-2 border-t border-dashed border-outline-variant/60 flex items-start gap-1.5 text-error">
          <span className="material-symbols-outlined text-[15px] shrink-0 mt-0.5">info</span>
          <span className="text-[11px] leading-tight font-medium">{record.failure_reason}</span>
        </div>
      )}
    </div>
  )
}
