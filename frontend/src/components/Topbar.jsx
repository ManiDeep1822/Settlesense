import React from 'react'

export default function Topbar({ title, searchTerm, onSearchChange, placeholder = "Search..." }) {
  return (
    <header className="bg-surface border-b border-outline-variant shadow-sm h-16 flex justify-between items-center px-gutter shrink-0 z-30 sticky top-0">
      <div className="flex items-center gap-4">
        {title && <h2 className="text-lg font-bold text-primary">{title}</h2>}
        <div className="flex items-center w-80 relative">
          <span className="material-symbols-outlined absolute left-3 text-on-surface-variant text-[20px]">
            search
          </span>
          <input
            type="text"
            value={searchTerm || ''}
            onChange={(e) => onSearchChange && onSearchChange(e.target.value)}
            placeholder={placeholder}
            className="w-full bg-surface-container-lowest border border-outline-variant rounded-md py-1.5 pl-10 pr-4 text-sm text-on-surface focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all shadow-[0px_1px_3px_rgba(15,23,42,0.08)]"
          />
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 bg-secondary/10 text-secondary border border-secondary/20 px-3 py-1 rounded-full text-xs font-semibold">
          <span className="w-2 h-2 rounded-full bg-secondary animate-pulse"></span>
          Live Grounding Active
        </div>
        <button className="text-on-surface-variant hover:text-primary transition-colors p-1.5 rounded-md hover:bg-surface-container">
          <span className="material-symbols-outlined text-[22px]">notifications</span>
        </button>
        <div className="w-8 h-8 rounded-full bg-primary text-on-primary flex items-center justify-center font-bold text-xs shadow-sm">
          RZ
        </div>
      </div>
    </header>
  )
}
