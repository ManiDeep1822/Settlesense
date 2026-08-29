import React, { useState } from 'react'
import Sidebar from './components/Sidebar'
import Topbar from './components/Topbar'
import Dashboard from './pages/Dashboard'
import AskSettlements from './pages/AskSettlements'
import Transactions from './pages/Transactions'
import Exceptions from './pages/Exceptions'
import Reports from './pages/Reports'
import Settings from './pages/Settings'

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [initialChatQuery, setInitialChatQuery] = useState('')
  const [globalSearch, setGlobalSearch] = useState('')

  const handleNavigateToChat = (queryText) => {
    setInitialChatQuery(queryText)
    setActiveTab('chat')
  }

  const handleGlobalSearch = (val) => {
    setGlobalSearch(val)
    if (val.trim() && activeTab !== 'transactions' && activeTab !== 'chat') {
      setActiveTab('transactions')
    }
  }

  return (
    <div className="flex bg-background text-on-background min-h-screen antialiased">
      <Sidebar activeTab={activeTab} onSelectTab={setActiveTab} />

      <div className="flex-1 ml-64 flex flex-col h-screen overflow-hidden">
        <Topbar
          searchTerm={globalSearch}
          onSearchChange={handleGlobalSearch}
          placeholder="Search transactions, UTRs, exceptions..."
        />

        <main className="flex-1 overflow-hidden flex flex-col">
          {activeTab === 'dashboard' && (
            <Dashboard
              onNavigateToChat={handleNavigateToChat}
              onNavigateToTransactions={() => setActiveTab('transactions')}
              onNavigateToExceptions={() => setActiveTab('exceptions')}
            />
          )}

          {activeTab === 'chat' && (
            <AskSettlements initialQuery={initialChatQuery} />
          )}

          {activeTab === 'transactions' && (
            <Transactions onAskAboutTransaction={handleNavigateToChat} />
          )}

          {activeTab === 'exceptions' && (
            <Exceptions onAskAboutException={handleNavigateToChat} />
          )}

          {activeTab === 'reports' && <Reports />}

          {activeTab === 'settings' && <Settings />}
        </main>
      </div>
    </div>
  )
}
