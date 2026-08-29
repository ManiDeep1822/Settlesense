import React from 'react'

export default function Sidebar({ activeTab, onSelectTab }) {
  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: 'dashboard' },
    { id: 'chat', label: 'Ask Settlements', icon: 'chat_bubble' },
    { id: 'transactions', label: 'Transactions', icon: 'swap_horiz' },
    { id: 'exceptions', label: 'Exceptions', icon: 'report_problem' },
    { id: 'reports', label: 'Reports & Accuracy', icon: 'analytics' },
    { id: 'settings', label: 'Settings', icon: 'settings', mtAuto: true }
  ]

  return (
    <nav className="bg-surface fixed left-0 top-0 h-full flex flex-col w-64 border-r border-outline-variant z-40">
      <div className="px-6 py-6 border-b border-outline-variant">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-on-primary font-bold">
            <span className="material-symbols-outlined text-[18px]">account_balance</span>
          </div>
          <div>
            <h1 className="font-sans text-xl font-bold text-primary leading-none">SettleSense</h1>
            <p className="font-sans text-xs text-on-surface-variant mt-1">AI Finance Controller</p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto py-4 flex flex-col gap-1">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => onSelectTab(tab.id)}
              className={`flex items-center gap-3 px-6 py-4 transition-colors text-left text-sm font-semibold ${
                tab.mtAuto ? 'mt-auto' : ''
              } ${
                isActive
                  ? 'text-primary font-bold border-r-4 border-primary bg-surface-container-low'
                  : 'text-on-surface-variant hover:bg-surface-container'
              }`}
            >
              <span
                className="material-symbols-outlined"
                style={{ fontVariationSettings: `'FILL' ${isActive ? 1 : 0}` }}
              >
                {tab.icon}
              </span>
              <span>{tab.label}</span>
            </button>
          )
        })}
      </div>
    </nav>
  )
}
