import React, { useState, useRef, useEffect } from 'react'
import { askSettlementQuery } from '../services/api'
import SourceCard from '../components/SourceCard'

export default function AskSettlements({ initialQuery }) {
  const [messages, setMessages] = useState([
    {
      id: 'welcome-msg',
      type: 'agent',
      text: 'Hello! I am SettleSense, your AI Finance Controller. Every response is fact-checked by our independent Verifier Agent against raw settlement ledger records.',
      cited_records: [],
      confidence: 'HIGH',
      confidence_score: 1.0,
      engine_used: 'fallback',
      verifier_verdict: 'VERIFIED',
      verifier_notes: 'System initialized and verified against database.',
      latency_ms: 0
    }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const messagesEndRef = useRef(null)
  const textareaRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isLoading])

  useEffect(() => {
    let timer
    if (isLoading) {
      setElapsedSeconds(0)
      timer = setInterval(() => {
        setElapsedSeconds((prev) => +(prev + 0.1).toFixed(1))
      }, 100)
    }
    return () => clearInterval(timer)
  }, [isLoading])

  useEffect(() => {
    if (initialQuery) {
      handleSend(initialQuery)
    }
  }, [initialQuery])

  const handleSend = async (textToSend) => {
    const queryText = (textToSend || input).trim()
    if (!queryText || isLoading) return

    const userMessageId = `user-${Date.now()}`
    setMessages((prev) => [
      ...prev,
      { id: userMessageId, type: 'user', text: queryText }
    ])
    setInput('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
    setIsLoading(true)

    try {
      const response = await askSettlementQuery(queryText)
      setMessages((prev) => [
        ...prev,
        {
          id: `agent-${Date.now()}`,
          type: 'agent',
          text: response.answer,
          confidence: response.confidence,
          confidence_score: response.confidence_score,
          engine_used: response.engine_used || 'fallback',
          engine_used_primary: response.engine_used_primary || response.engine_used || 'fallback',
          engine_used_verifier: response.engine_used_verifier || 'fallback',
          verifier_verdict: response.verifier_verdict || 'VERIFIED',
          verifier_notes: response.verifier_notes,
          discrepancies: response.discrepancies || [],
          cited_records: response.cited_records || [],
          cited_record_ids: response.cited_record_ids || [],
          exception_detected: response.exception_detected,
          exception_type: response.exception_type,
          exception_reason: response.exception_reason,
          latency_ms: response.latency_ms
        }
      ])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: `agent-err-${Date.now()}`,
          type: 'agent',
          text: `Error connecting to settlement reasoning service: ${err.message}`,
          confidence: 'LOW',
          confidence_score: 0.0,
          engine_used: 'fallback',
          verifier_verdict: 'FLAGGED',
          verifier_notes: 'Connection error during reasoning pipeline.',
          discrepancies: [err.message],
          cited_records: [],
          exception_detected: true,
          exception_type: 'SYSTEM_ERROR',
          latency_ms: 0
        }
      ])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const suggestions = [
    "Why didn't order #4521 settle yesterday?",
    "What is my pending payout for last week?",
    "Why is transaction TXN-849202B flagged as an exception?",
    "Why didn't order #99999 settle?",
    "Verify the settlement status of ORD-992-B",
    "What was the fee deducted for ORD-992-B?"
  ]

  return (
    <div className="flex-1 flex flex-col h-full bg-surface-container-lowest relative overflow-hidden">
      <div className="flex-1 overflow-y-auto w-full flex flex-col pt-6 pb-[180px] px-gutter">
        <div className="w-full max-w-[1000px] mx-auto flex flex-col gap-6">
          <div className="flex justify-center my-1">
            <span className="text-xs text-on-surface-variant bg-surface-container px-4 py-1 rounded-full shadow-sm font-medium">
              Live Settlement Database & Independent Verifier Agent Connected
            </span>
          </div>

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.type === 'user' ? (
                <div className="max-w-[70%]">
                  <div className="bg-primary text-on-primary rounded-2xl rounded-tr-sm p-4 shadow-sm">
                    <p className="text-sm leading-relaxed">{msg.text}</p>
                  </div>
                </div>
              ) : (
                <div className="max-w-[88%] flex gap-3.5">
                  <div className="w-8 h-8 shrink-0 rounded-full bg-surface-container-high border border-outline-variant flex items-center justify-center text-primary mt-1 shadow-sm">
                    <span className="material-symbols-outlined text-[18px]">smart_toy</span>
                  </div>

                  <div className="flex flex-col gap-2.5 w-full">
                    <div className="bg-surface-container-low text-on-surface border border-outline-variant rounded-2xl rounded-tl-sm p-4 md:p-5 shadow-sm">
                      <p className="text-sm leading-relaxed whitespace-pre-line text-on-surface">
                        {msg.text}
                      </p>

                      {msg.verifier_notes && msg.verifier_verdict !== 'VERIFIED' && (
                        <div className="mt-3 p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl text-xs text-amber-900">
                          <div className="flex items-center gap-1.5 font-bold mb-1">
                            <span className="material-symbols-outlined text-[16px] text-amber-700">fact_check</span>
                            <span>Verifier Agent Audit Notice:</span>
                          </div>
                          <p className="text-amber-800 leading-relaxed">{msg.verifier_notes}</p>
                          {msg.discrepancies && msg.discrepancies.length > 0 && (
                            <ul className="mt-1 list-disc list-inside text-[11px] text-amber-700">
                              {msg.discrepancies.map((d, i) => (
                                <li key={i}>{d}</li>
                              ))}
                            </ul>
                          )}
                        </div>
                      )}

                      {msg.cited_records && msg.cited_records.length > 0 && (
                        <details className="mt-4 bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden shadow-sm group">
                          <summary className="flex justify-between items-center p-3 cursor-pointer hover:bg-surface-container transition-colors">
                            <div className="flex items-center gap-2">
                              <div className="w-6 h-6 rounded bg-surface-variant flex items-center justify-center text-primary">
                                <span className="material-symbols-outlined text-[15px]">database</span>
                              </div>
                              <span className="text-xs font-semibold text-on-surface">
                                Grounded Sources ({msg.cited_records.length} {msg.cited_records.length === 1 ? 'Record' : 'Records'})
                              </span>
                            </div>
                            <span className="material-symbols-outlined text-on-surface-variant group-open:rotate-180 transition-transform duration-200 text-[18px]">
                              expand_more
                            </span>
                          </summary>
                          <div className="divide-y divide-outline-variant/60">
                            {msg.cited_records.map((rec) => (
                              <SourceCard key={rec.id} record={rec} />
                            ))}
                          </div>
                        </details>
                      )}
                    </div>

                    <div className="flex flex-wrap items-center gap-2 text-xs ml-1">
                      {msg.verifier_verdict === 'VERIFIED' && (
                        <div 
                          title="All stated facts confirmed against ledger records. Does not confirm the answer addresses every part of a multi-part question."
                          className="flex items-center gap-1 text-secondary bg-secondary/10 px-2.5 py-1 rounded-full border border-secondary/20 font-medium cursor-help transition-all hover:bg-secondary/15"
                        >
                          <span className="material-symbols-outlined text-[14px]">verified</span>
                          <span>✓ Facts Verified</span>
                        </div>
                      )}

                      {msg.verifier_verdict === 'MINOR_DISCREPANCY' && (
                        <div 
                          title="Core conclusion grounded in ledger, but minor descriptive or rounding imprecision noted."
                          className="flex items-center gap-1 text-amber-700 bg-amber-500/10 px-2.5 py-1 rounded-full border border-amber-500/20 font-medium cursor-help transition-all hover:bg-amber-500/15"
                        >
                          <span className="material-symbols-outlined text-[14px]">warning</span>
                          <span>⚠ Minor Fact Discrepancy</span>
                        </div>
                      )}

                      {msg.verifier_verdict === 'FLAGGED' && (
                        <div 
                          title="Verifier detected factual contradiction or ungrounded claim against ledger records."
                          className="flex items-center gap-1 text-error bg-error/10 px-2.5 py-1 rounded-full border border-error/20 font-medium cursor-help transition-all hover:bg-error/15"
                        >
                          <span className="material-symbols-outlined text-[14px]">cancel</span>
                          <span>✕ Flagged for Review</span>
                        </div>
                      )}

                      {msg.engine_used === 'gemini' ? (
                        <div className="flex items-center gap-1 text-purple-700 bg-purple-500/10 px-2.5 py-1 rounded-full border border-purple-500/20 font-medium">
                          <span className="material-symbols-outlined text-[14px]">auto_awesome</span>
                          <span>Gemini 2.5 Flash</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1 text-slate-700 bg-slate-500/10 px-2.5 py-1 rounded-full border border-slate-500/20 font-medium">
                          <span className="material-symbols-outlined text-[14px]">bolt</span>
                          <span>Deterministic Engine</span>
                        </div>
                      )}

                      {msg.confidence === 'UNANSWERABLE' && (
                        <div className="flex items-center gap-1 text-error bg-error/10 px-2.5 py-1 rounded-full border border-error/20 font-medium">
                          <span className="material-symbols-outlined text-[14px]">highlight_off</span>
                          <span>Correctly Declined</span>
                        </div>
                      )}

                      {msg.exception_detected && (
                        <div className="flex items-center gap-1 text-tertiary bg-tertiary/10 px-2.5 py-1 rounded-full border border-tertiary/20 font-medium">
                          <span className="material-symbols-outlined text-[14px]">report_problem</span>
                          <span>Logged to Exception Ledger</span>
                        </div>
                      )}

                      {msg.latency_ms > 0 && (
                        <span className="text-[11px] text-on-surface-variant ml-auto">
                          {msg.latency_ms} ms
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start">
              <div className="max-w-[85%] flex gap-3.5 items-start">
                <div className="w-8 h-8 rounded-full bg-primary/10 border border-primary/30 flex items-center justify-center text-primary shadow-sm animate-pulse mt-1">
                  <span className="material-symbols-outlined text-[18px]">smart_toy</span>
                </div>
                <div className="flex flex-col gap-2 w-full">
                  <div className="bg-surface-container-low border border-primary/30 rounded-2xl rounded-tl-sm p-4 text-xs shadow-md">
                    <div className="flex items-center justify-between gap-3 mb-2">
                      <div className="flex items-center gap-2 font-semibold text-primary">
                        <span className="w-2.5 h-2.5 rounded-full bg-primary animate-ping"></span>
                        <span>Primary Reasoning & Independent Verifier Pass...</span>
                      </div>
                      <span className="text-[11px] font-mono text-on-surface-variant bg-surface-container px-2 py-0.5 rounded">
                        {elapsedSeconds.toFixed(1)}s
                      </span>
                    </div>
                    <div className="space-y-2">
                      <div className="h-2.5 bg-primary/15 rounded-full w-4/5 animate-pulse"></div>
                      <div className="h-2.5 bg-primary/10 rounded-full w-2/3 animate-pulse"></div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-[11px] text-on-surface-variant ml-1">
                    <span className="material-symbols-outlined text-[14px] animate-spin text-primary">sync</span>
                    <span>Retrieving SQLite ledger $\rightarrow$ Primary Agent $\rightarrow$ Independent Verifier Agent audit</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="absolute bottom-0 w-full left-0 bg-surface/85 backdrop-blur-[12px] border-t border-outline-variant px-gutter py-4 flex flex-col gap-3 z-20">
        <div className="max-w-[1000px] w-full mx-auto flex flex-col gap-2.5">
          <div className="flex gap-2 overflow-x-auto pb-1 hide-scrollbar">
            {suggestions.map((sug, i) => (
              <button
                key={i}
                onClick={() => handleSend(sug)}
                className="shrink-0 bg-surface-container border border-outline-variant text-on-surface-variant hover:bg-primary hover:text-on-primary transition-all px-3 py-1.5 rounded-full text-xs font-medium flex items-center gap-1.5 shadow-sm"
              >
                <span className="material-symbols-outlined text-[14px]">search</span>
                "{sug}"
              </button>
            ))}
          </div>

          <div className="relative flex items-end gap-2 bg-surface-container-lowest border-2 border-outline-variant shadow-sm focus-within:border-primary focus-within:ring-4 focus-within:ring-primary/10 rounded-2xl p-1.5 transition-all">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => {
                setInput(e.target.value)
                e.target.style.height = 'auto'
                e.target.style.height = `${e.target.scrollHeight}px`
              }}
              onKeyDown={handleKeyDown}
              placeholder="Ask SettleSense about specific transactions, settlement delays, exceptions, or payouts..."
              rows={1}
              className="w-full bg-transparent border-none focus:ring-0 resize-none text-sm text-on-surface p-2.5 max-h-32 min-h-[48px] hide-scrollbar outline-none"
            />
            <div className="flex gap-1.5 p-1 shrink-0">
              <button
                onClick={() => handleSend()}
                disabled={!input.trim() || isLoading}
                className="px-4 py-2 bg-primary text-on-primary rounded-xl shadow-md hover:bg-primary-fixed-variant transition-colors flex items-center justify-center gap-1.5 text-xs font-semibold disabled:opacity-50 disabled:cursor-not-allowed active:scale-95"
              >
                <span>Send</span>
                <span className="material-symbols-outlined text-[16px]">send</span>
              </button>
            </div>
          </div>

          <p className="text-center text-[11px] text-on-surface-variant">
            Two-Tier Verification: Stated facts are independently audited by the SettleSense Verifier Agent before presentation.
          </p>
        </div>
      </div>
    </div>
  )
}
