# SettleSense — Key Architectural Decisions

### Decision 1: Hybrid Retrieval over Pure Vector Search or Pure Text-to-SQL
* **Date**: 2026-08-22
* **Context**: Financial settlement questions range from exact entity lookups ("Why did order #4521 fail?") to semantic inquiries ("Show delayed transactions from yesterday"). Pure vector search fails on exact numerical order IDs, while pure Text-to-SQL fails on fuzzy descriptions and natural language policy inquiries.
* **Decision**: Implement a two-tier hybrid retrieval architecture:
  1. Regex-based entity extractor for order refs (`ORD-xxxx`, `#xxxx`), transaction IDs (`TXN-xxxx`), batch IDs (`SETTLE-xxxx`), and bank UTRs (`CHASE-xxxx-XX`), querying SQLite with parameterized exact/LIKE matches.
  2. ChromaDB vector search with cosine distance for semantic context retrieval.
  3. Combined deduplicated context passed into the reasoning agent.
* **Rationale**: Guarantees deterministic precision for exact ledger IDs while retaining semantic understanding for descriptive financial inquiries.

---

### Decision 2: Local SQLite + Local ChromaDB Architecture
* **Date**: 2026-08-22
* **Context**: Need a database and vector store that can run frictionlessly on any machine (macOS/Windows/Linux) with zero cloud infrastructure setup, Docker dependencies, or external database credentials.
* **Decision**: Use Python's built-in `sqlite3` for structured transactions/settlements and ChromaDB in persistent local client mode (`backend/chroma_db`).
* **Rationale**: 100% reproducible by judges via simple `pip install` and script execution.

---

### Decision 3: Entity Isolation Guardrail
* **Date**: 2026-08-22
* **Context**: A critical vulnerability in RAG systems is semantic vector search returning nearest-neighbor records for non-existent queries (e.g. querying "Order #99999" returns "Order #4521" because it's semantically close).
* **Decision**: Implement a strict post-extraction guardrail: if the user's prompt contains a specific entity identifier (order ID, txn ID, batch ID) and that exact identifier does not exist in the SQLite database, the system immediately returns an empty context (`[]`), completely bypassing vector similarity search.
* **Rationale**: Prevents hallucinated responses for fake/non-existent orders, driving the system to honestly decline with `RECORD_NOT_FOUND` and log the anomaly.

---

### Decision 4: Deterministic Grounded Fallback Engine
* **Date**: 2026-08-22
* **Context**: In judging environments, Gemini API keys might not be provided, could be rate-limited, or may face network latency.
* **Decision**: Implement a two-tier reasoning layer: (1) Google Gemini 2.5 Flash via REST/SDK when `GEMINI_API_KEY` is present, and (2) a high-precision deterministic grounded reasoning engine that extracts ledger attributes and returns structured JSON with citations.
* **Rationale**: Ensures the test harness and evaluation dashboard run with 100% reliability, sub-25ms latency, and zero dependency blockers during live judging.

---

### Decision 5: First-Class Exceptions Ledger
* **Date**: 2026-08-22
* **Context**: Buildathon requirements state that unanswerable queries and anomalies must be logged rather than concealed.
* **Decision**: Create an `exceptions_log` table and dedicated UI screen. Automatically log any low-confidence query, non-existent record inquiry, or settlement hold.
* **Rationale**: Transforms error handling from a hidden failure mode into an audit trail for finance operations.

---

### Decision 6: Automated Accuracy Benchmark Test Harness
* **Date**: 2026-08-22
* **Context**: Judges require empirical proof of accuracy across a labeled test suite.
* **Decision**: Build `run_accuracy_harness.py` with 42 ground-truth test cases across 14 categories, scoring not only correct answers but also "Correctly Declined" non-existent and out-of-scope queries. Expose this directly in the UI with a "Run Benchmark" trigger.
* **Rationale**: Provides transparent, reproducible evidence of the system's performance on demand.

---

### Decision 7: Independent Verifier Agent for Pre-Delivery Fact Auditing
* **Date**: 2026-08-29
* **Context**: The Razorpay AI Buildathon explicitly evaluates submissions on *verification capacity over generation speed*. Relying solely on a single-agent generation pass risks confirmation bias and undetected hallucinations in edge cases.
* **Decision**: Introduce an independent **Verifier Agent** that executes a second, isolated audit pass over the primary answer before it is shown to the user. The verifier receives only the user's raw query, the primary text answer, and the raw retrieved database rows — without seeing the primary agent's internal chain-of-thought or confidence score.
* **Rationale**: This guarantees adversarial fact-checking against actual database rows (checking amounts, dates, IDs, and UTRs). Structured verdicts (`VERIFIED`, `MINOR_DISCREPANCY`, `FLAGGED`) allow the system to route suspected discrepancies into the Exceptions Ledger under `VERIFIER_FLAGGED` rather than returning ungrounded answers.
* **Trade-off**: Increases query latency by requiring a two-tier evaluation pass; justified by the critical importance of financial accuracy and auditability.

---

### Decision 8: Query Intent Classification & Dedicated SQL Aggregation Routing
* **Date**: 2026-08-29
* **Context**: Live manual testing revealed two edge cases: (1) Off-topic greetings or small-talk queries ("Hello?", "Hello, I need some help") caused ChromaDB vector search to return arbitrary nearest-neighbor transactions, describing a random order with a "Facts Verified" badge, and (2) Aggregate/count queries ("How many transactions are there in the database?", "What's my total pending payout?") were answered by describing a single retrieved row rather than performing a database calculation.
* **Discovery Note**: This failure mode was discovered through live manual interaction rather than the automated test suite, because the test suite initially focused on specific entity lookups and declined queries.
* **Decision**: Implement a pre-retrieval **Query Intent Classification** step that categorizes queries into `GREETING_OR_SMALL_TALK`, `OUT_OF_SCOPE`, `AGGREGATE_QUERY`, or `ENTITY_LOOKUP`:
  1. `GREETING_OR_SMALL_TALK` and `OUT_OF_SCOPE`: Bypass database retrieval entirely; return a clear informational response or polite scope boundary without citations or a verified badge.
  2. `AGGREGATE_QUERY`: Route directly to deterministic SQL aggregate queries (`COUNT(*)`, `SUM(amount)`, `SUM(net_payout)`) against SQLite to return mathematically exact counts and volumes across batches.
  3. `ENTITY_LOOKUP`: Proceed with exact entity extraction + hybrid vector search.
* **Rationale**: Prevents hallucinated transaction citations on general conversational inputs while ensuring financial aggregation questions are answered with mathematical exactness from SQLite ledger tables.
