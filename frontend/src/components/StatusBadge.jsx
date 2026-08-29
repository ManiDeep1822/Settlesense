import React from 'react'

export default function StatusBadge({ status, icon = true }) {
  const normalized = (status || '').toLowerCase()

  let colorClasses = 'bg-outline/10 text-on-surface-variant border-outline/20'
  let iconName = 'help_outline'
  let label = status || 'Unknown'

  if (normalized === 'matched' || normalized === 'settled') {
    colorClasses = 'bg-secondary/10 text-secondary border-secondary/20'
    iconName = 'check_circle'
    label = 'Matched'
  } else if (normalized === 'declined' || normalized === 'failed') {
    colorClasses = 'bg-error/10 text-error border-error/20'
    iconName = 'cancel'
    label = 'Declined'
  } else if (normalized === 'exception' || normalized === 'partial_exception') {
    colorClasses = 'bg-tertiary/10 text-tertiary border-tertiary/20'
    iconName = 'report_problem'
    label = 'Exception'
  } else if (normalized === 'pending') {
    colorClasses = 'bg-outline/10 text-on-surface-variant border-outline/20'
    iconName = 'schedule'
    label = 'Pending'
  } else if (normalized === 'delayed' || normalized === 'on_hold') {
    colorClasses = 'bg-amber-500/10 text-amber-700 border-amber-500/20'
    iconName = 'hourglass_empty'
    label = 'Delayed'
  } else if (normalized === 'unmatched') {
    colorClasses = 'bg-red-500/10 text-red-600 border-red-500/20'
    iconName = 'link_off'
    label = 'Unmatched'
  }

  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full font-sans text-xs font-semibold border ${colorClasses}`}>
      {icon && <span className="material-symbols-outlined text-[14px] mr-1.5">{iconName}</span>}
      {label}
    </span>
  )
}
