# SettleSense — AI Settlement Q&A Agent & Finance Controller

**Razorpay AI Buildathon 2026 Submission (AI Finance Controller Track)**  
GitHub Repository: [https://github.com/ManiDeep1822/Settlesense.git](https://github.com/ManiDeep1822/Settlesense.git)

SettleSense is an AI-powered Settlement Q&A Agent and Finance Controller that enables merchants and finance operations teams to ask natural language questions about payment settlements, fee deductions, delayed payouts, and reconciliation discrepancies with 100% provenance, source citations, and an independent Two-Tier Verifier Agent.

---

## Key Highlights

- **Two-Tier Independent Verifier Agent**: Every primary answer is fact-checked by an independent, adversarial Verifier Agent against raw SQLite ledger rows before presentation.
- **100% Grounded Answers**: Direct citations to transaction IDs (`TXN-xxxx`), settlement batches (`SETTLE-xxxx`), and bank UTRs.
- **Honest Exception Logging**: If an order does not exist or data is ambiguous, SettleSense honestly declines (`UNANSWERABLE`) and automatically logs the anomaly in the **Exceptions Ledger**.
- **Empirical 38-Case Benchmark Harness**: Built-in evaluation test suite with live verification metrics (Agreement Rate, Catch Rate, False-Flag Rate).
- **Dual-Path Engine Resilience**: Seamlessly operates on **Google Gemini 2.5 Flash** when an API key is present, and falls back to an embedded deterministic grounding engine (sub-25ms latency) if offline or rate-limited.
- **Zero-Setup Reproducibility**: Uses embedded SQLite (`settlesense.db`) and local ChromaDB — zero external databases or Docker containers required.
- **Modern React UI**: Interactive chat canvas, transactions table, exceptions resolution workflow, and live benchmark execution.

---

## Documentation Index

- **[ARCHITECTURE.md](ARCHITECTURE.md)**: Technical architecture reference, RAG vs. Text-to-SQL comparison, two-agent verification design, and the Grounding vs. Completeness boundary.
- **[DECISIONS.md](DECISIONS.md)**: Architectural decision log covering 7 key engineering decisions and trade-offs.
- **[demo-script.md](demo-script.md)**: 5-minute pitch video walkthrough script highlighting clean queries, exception handling, and the live verifier audit.

---

## Quick Start Guide (Windows PowerShell)

All commands below are formatted for **Windows PowerShell**.

### Prerequisites
- Python 3.10+ installed
- Node.js 18+ and npm installed

---

### Step 1: Clone & Setup Environment

```powershell
# Clone the repository
git clone https://github.com/ManiDeep1822/Settlesense.git
cd Settlesense

# Install Python dependencies
pip install -r requirements.txt

# Install Frontend dependencies
cd frontend
npm install
cd ..
```

---

### Step 2: (Optional) Configure Gemini API Key

Copy the example environment file:
```powershell
Copy-Item .env.example .env
```

Open `.env` and add your Google Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey):
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

> **Zero-Setup Note**: If `GEMINI_API_KEY` is left blank, SettleSense automatically operates on its high-precision deterministic grounded engine with sub-25ms latency and full citation support.

---

### Step 3: Generate Dataset & Index Vectors

Before launching the app for the first time, generate the synthetic settlement database and vector index:

```powershell
# 1. Generate realistic settlement records in SQLite (settlesense.db)
python backend/scripts/generate_dataset.py

# 2. Index records into ChromaDB vector store
python backend/scripts/index_vectors.py
```

---

### Step 4: Run the Accuracy & Verification Harness

To verify system correctness and verifier audit metrics:

```powershell
# Run the 38-case ground-truth benchmark
python backend/scripts/run_accuracy_harness.py

# Run the deliberate wrong-answer injection stress-test
python backend/scripts/test_verifier_catches_errors.py
```

---

### Step 5: Start Backend & Frontend

#### Option A: One-Click Startup (PowerShell)
```powershell
.\start_settlesense.ps1
```

#### Option B: Separate Terminals
**Terminal 1 — Backend (Port 8000)**:
```powershell
python run_backend.py
```

**Terminal 2 — Frontend (Port 5173)**:
```powershell
cd frontend
npm run dev
```

- **Frontend Application**: `http://localhost:5173`
- **FastAPI Interactive Docs**: `http://localhost:8000/docs`

---

## Project Structure

```text
RAZORPAY/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI endpoints (/query, /transactions, /exceptions, /accuracy-report)
│   │   ├── agent.py             # Primary reasoning engine (Gemini + Deterministic Fallback)
│   │   ├── verifier.py          # Independent Verifier Agent (adversarial fact-checking)
│   │   ├── retrieval.py         # Hybrid SQLite entity extraction + ChromaDB vector search
│   │   ├── database.py          # SQLite schema, connections, and tables
│   │   ├── schemas.py           # Pydantic data models & response schemas
│   │   ├── exceptions_service.py # Exception ledger logging & status resolution
│   │   ├── metrics_service.py   # Latency, QPS, and KPI metrics tracking
│   │   └── config.py            # Environment configuration & path resolution
│   ├── data/
│   │   ├── test_cases.json      # 38 labeled ground-truth benchmark test cases
│   │   └── latest_accuracy_report.json # Scored evaluation metrics
│   └── scripts/
│       ├── generate_dataset.py  # Populates SQLite with 650+ transactions & settlement batches
│       ├── index_vectors.py     # Indexes ledger entries into ChromaDB
│       ├── run_accuracy_harness.py # 38-case accuracy & verifier benchmark runner
│       └── test_verifier_catches_errors.py # Deliberate wrong-answer injection stress-test
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx    # Financial KPIs, reconciliation rate, and quick queries
│   │   │   ├── AskSettlements.jsx # Chat canvas with '✓ Facts Verified' badge and thinking state
│   │   │   ├── Transactions.jsx # Tabular ledger with status filters and CSV export
│   │   │   ├── Exceptions.jsx   # Unresolved anomaly queue with resolution modal
│   │   │   ├── Reports.jsx      # Dual-path engine breakdown & verifier performance audit
│   │   │   └── Settings.jsx     # API configuration & system health indicators
│   │   ├── components/          # Topbar, Sidebar, SourceCard, KPI cards
│   │   └── services/api.js      # Axios client for backend endpoints
│   ├── package.json
│   └── tailwind.config.js
├── ARCHITECTURE.md              # Technical defense & system architecture reference
├── DECISIONS.md                 # Architectural decision log (7 logged decisions)
├── demo-script.md               # 5-minute video pitch & presentation guide
├── start_settlesense.ps1        # PowerShell one-click startup script
├── run_backend.py               # Standalone backend launcher
├── requirements.txt             # Root Python dependencies
├── .env.example                 # Environment variables template (safe placeholders)
├── .gitignore                   # Comprehensive gitignore (ignores secrets, DB, and node_modules)
└── README.md                    # Project documentation & quick start guide
```
