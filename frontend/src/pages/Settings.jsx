import React, { useState } from 'react'

export default function Settings() {
  const [apiKey, setApiKey] = useState('')
  const [merchantId, setMerchantId] = useState('mer_rzp_live_884920')
  const [saved, setSaved] = useState(false)

  const handleSave = (e) => {
    e.preventDefault()
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  return (
    <div className="flex-1 p-gutter max-w-[1000px] mx-auto w-full overflow-y-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-on-surface">System Configuration & Integrations</h2>
        <p className="text-sm text-on-surface-variant mt-1">
          Manage Gemini AI models, ChromaDB vector indexing parameters, and Razorpay merchant credentials.
        </p>
      </div>

      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm mb-6">
        <h3 className="text-base font-bold text-on-surface mb-4 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">psychology</span>
          Google Gemini AI Reasoning Settings
        </h3>

        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-on-surface-variant mb-1">
              Gemini API Key (Optional - Fallback deterministic grounding engine active by default)
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="AIzaSy..."
              className="w-full px-3 py-2 border border-outline-variant rounded-md text-xs font-mono focus:border-primary outline-none bg-surface-container-low"
            />
            <p className="text-[11px] text-on-surface-variant mt-1">
              If left blank, SettleSense runs seamlessly in offline zero-dependency mode using deterministic grounded reasoning.
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-on-surface-variant mb-1">
              Active Merchant ID
            </label>
            <input
              type="text"
              value={merchantId}
              onChange={(e) => setMerchantId(e.target.value)}
              className="w-full px-3 py-2 border border-outline-variant rounded-md text-xs font-mono focus:border-primary outline-none bg-surface-container-low"
            />
          </div>

          <div className="pt-2">
            <button
              type="submit"
              className="bg-primary text-on-primary px-4 py-2 rounded-md text-xs font-semibold hover:bg-primary-fixed-variant transition-colors"
            >
              Save Configuration
            </button>
            {saved && (
              <span className="ml-3 text-xs text-secondary font-semibold">Settings saved!</span>
            )}
          </div>
        </form>
      </div>

      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm">
        <h3 className="text-base font-bold text-on-surface mb-4 flex items-center gap-2">
          <span className="material-symbols-outlined text-secondary">storage</span>
          Infrastructure & Data Layer Status
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div className="p-3 bg-surface-container-low rounded-lg border border-outline-variant/60">
            <p className="font-semibold text-on-surface mb-1">Structured Database</p>
            <p className="font-mono text-on-surface-variant">SQLite 3 (settlesense.db)</p>
            <span className="inline-block mt-2 text-[10px] bg-secondary/10 text-secondary px-2 py-0.5 rounded font-semibold">
              Zero-Setup Active
            </span>
          </div>

          <div className="p-3 bg-surface-container-low rounded-lg border border-outline-variant/60">
            <p className="font-semibold text-on-surface mb-1">Vector Store Engine</p>
            <p className="font-mono text-on-surface-variant">ChromaDB Persistent (Cosine)</p>
            <span className="inline-block mt-2 text-[10px] bg-secondary/10 text-secondary px-2 py-0.5 rounded font-semibold">
              Indexed
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
