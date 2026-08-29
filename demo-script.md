# SettleSense — 5-Minute Pitch Video & Demo Script

This script provides a concise, high-impact 5-minute walkthrough for the Razorpay AI Buildathon 2026 pitch video and live presentation.

---

## Pitch Video Structure (5 Minutes)

### Phase 1: Problem & System Overview (0:00 – 0:45)
* **Visual**: Show SettleSense Dashboard with KPI cards (₹2.4M Settled Volume, Reconciliation Match Rate 98%, Active Exceptions).
* **Script**:
  > *"Every merchant and finance operations team knows the pain of settlement discrepancies: Why didn't an order settle? What caused an amount mismatch? What's my pending payout?*
  > 
  > *Traditional dashboards show static tables, while standard LLMs hallucinate numbers. Today, we introduce **SettleSense** — an AI-powered Finance Controller that delivers natural language answers with 100% provenance, grounded citations to source ledger rows, and an **Independent Two-Agent Verification Architecture** targeting the buildathon's core criteria: verification over generation."*

---

### Phase 2: Clean Query 1 — Specific Dispute & Decline Investigation (0:45 – 1:30)
* **Action**: In the **Ask Settlements** chat, type or click prompt:
  ```
  Why didn't order #4521 settle yesterday?
  ```
* **Visual**: Watch response render with citations and verifier badge.
* **Key Elements to Highlight**:
  1. **Narrative Explanation**: Agent clearly explains that order `ORD-4521` (Transaction `TXN-8894-4521`) was declined before capture due to a billing ZIP code mismatch flagged by the processor.
  2. **Independent Verifier Badge**: Point out the teal **`✓ Verified by Verifier Agent`** badge, proving that an independent second pass audited every ID and status before presentation.
  3. **Grounded Source Accordion**: Expand the *"Grounded Sources (1 Record)"* accordion to reveal the raw transaction table row: Gross ₹1,450.00, Status: Declined, Failure Reason attached.

---

### Phase 3: The Standout Demo Moment — Independent Verifier Audit & Ledger Reconciliation (1:30 – 2:30)
* **Action**: In chat, enter:
  ```
  Verify the gross amount, MDR fee, and settlement cycle for order ORD-992-B
  ```
* **Visual**: 
  1. Primary Agent synthesizes the transaction record (`TXN-849201A`) and settlement batch (`SETTLE-20231024-001`).
  2. Verifier Agent audits all numbers: Gross ₹1,24,500.00, MDR fee ₹2,490.00, GST tax ₹448.20, and net payout ₹1,21,561.80.
  3. Badge displays: **`✓ Facts Verified`** with direct citations and hover tooltip.
* **Script**:
  > *"Notice what just happened behind the scenes: our primary agent generated the response, but before showing it to the user, an independent Verifier Agent fact-checked every number, fee calculation, and bank UTR against the raw SQLite ledger. 
  > 
  > We label this specifically as **'Facts Verified'** because our rigorous stress-testing proved that factual grounding and multi-part query completeness are two distinct jobs: the Verifier guarantees zero hallucinated numbers, while our 38-case test harness independently evaluates question completeness."*

---

### Phase 4: Honest Exception Handling — Non-Existent Record (2:30 – 3:30)
* **Action**: In chat, enter a non-existent order:
  ```
  Why didn't order #99999 settle?
  ```
* **Visual**:
  1. Agent **honestly declines**: *"I reviewed the settlement database but found no matching entry for Order ORD-99999. Please verify the identifier or check if the transaction is pending ingestion."*
  2. Verifier confirms: **Honest Declination Verified (No Grounding Data)**.
  3. Status indicates: **Logged to Exception Ledger**.
* **Action**: Click on the **Exceptions** tab in the sidebar.
* **Visual**: Show the newly logged entry in the Exceptions Ledger (`RECORD_NOT_FOUND` / `VERIFIER_FLAGGED`), query text, root cause, and status: `UNRESOLVED`. Click **"Resolve Exception"** and add an audit note.

---

### Phase 5: Live 35-Case Verification Benchmark (3:30 – 4:30)
* **Action**: Click on the **Reports & Accuracy** tab in the sidebar.
* **Visual**: 
  1. Highlight the **Verifier Agent Performance Audit Panel**:
     - **100% Agreement Rate Consensus**
     - **0.0% False-Flag Rate**
     - **8 / 8 Non-Existent Cases Correctly Declined (0% Hallucinations)**
  2. Highlight the **Dual-Path Engine Architecture**:
     - **Cloud AI Path (Google Gemini 2.5 Flash)**: Complex generative reasoning.
     - **Edge Deterministic Path**: Sub-25ms offline engine guaranteeing 100% hackathon judging reproducibility.
  3. Click **"Run Benchmark Harness"** live in the UI. Watch all 35 tests verify in real-time.

---

### Phase 6: Conclusion & Defense Readiness (4:30 – 5:00)
* **Script**:
  > *"SettleSense delivers financial rigor: zero hallucinations, instant citations, two-tier independent verification, honest failure handling, and measurable accuracy. It is production-ready, reproducible with zero external setup, and built for the future of fintech intelligence. Thank you!"*
