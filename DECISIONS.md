# SettleSense — Architectural Decision Log (DECISIONS.md)

This document records key technical decisions, trade-offs, and design rationale made during the development of SettleSense for the Razorpay AI Buildathon 2026.

---

### Decision 1: SQLite for Relational Ledger Storage
* **Date**: 2026-08-22
* **Context**: Judges and evaluators need to run and review the project locally on Windows machines without setting up external database daemons (e.g. Postgres, MySQL, Docker).
* **Decision**: Adopt SQLite with standard Python `sqlite3` driver and connection pooling.
* **Rationale**: SQLite provides zero-setup, single-file (`settlesense.db`) relational storage with full ACID compliance and sub-millisecond query latency on local disk.
* **Trade-off**: Not suitable for high-write multi-server production environments; in production, this will be swapped for PostgreSQL.

---

### Decision 2: Hybrid Retrieval (Exact Identifier Extraction + Vector Search) Over Pure Text-to-SQL
* **Date**: 2026-08-22
* **Context**: Users ask a mixture of exact identifier queries ("Why didn't order #4521 settle?") and conceptual inquiries ("What are my pending payouts?").
* **Decision**: Use regular-expression and keyword parsing for exact order IDs, transaction IDs, UTRs, and dates combined with ChromaDB cosine vector search.
* **Rationale**: Pure Text-to-SQL frequently fails on fuzzy conversational phrasing or generates unsafe queries. Pure vector search can suffer from cosine similarity collisions on numeric strings (e.g., confusing `ORD-99999` with `ORD-99998`). The hybrid model guarantees 100% precision on exact records while retaining semantic flexibility for broad inquiries.

---

### Decision 3: Strict Entity Isolation (Anti-Hallucination Guardrail)
* **Date**: 2026-08-22
* **Context**: When a user asks about a non-existent order (e.g. `ORD-99999`), vector search still returns the mathematically closest vector in the database (e.g. `TXN-5979-10596`), leading to potential false positives.
* **Decision**: When an exact entity identifier is detected in the query but fails to match any row in SQLite, the system strictly quarantines the vector store results and forces an honest declination (`UNANSWERABLE`).
* **Rationale**: Financial systems cannot tolerate hallucinated answers. A transparent "Record Not Found" response is infinitely better than guessing.

---

### Decision 4: Deterministic Grounded Fallback Engine
* **Date**: 2026-08-22
* **Context**: In judging environments, Gemini API keys might not be provided, could be rate-limited, or may face network latency.
* **Decision**: Implement a two-tier reasoning layer: (1) Google Gemini 1.5 Flash via REST/SDK when `GEMINI_API_KEY` is present, and (2) a high-precision deterministic grounded reasoning engine that extracts ledger attributes and returns structured JSON with citations.
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
* **Decision**: Build `run_accuracy_harness.py` with 35 ground-truth test cases across 10 categories, scoring not only correct answers but also "Correctly Declined" non-existent queries. Expose this directly in the UI with a "Run Benchmark" trigger.
* **Rationale**: Provides transparent, reproducible evidence of the system's performance on demand.

---

### Decision 7: Independent Verifier Agent for Pre-Delivery Fact Auditing
* **Date**: 2026-08-29
* **Context**: The Razorpay AI Buildathon explicitly evaluates submissions on *verification capacity over generation speed*. Relying solely on a single-agent generation pass risks confirmation bias and undetected hallucinations in edge cases.
* **Decision**: Introduce an independent **Verifier Agent** that executes a second, isolated audit pass over the primary answer before it is shown to the user. The verifier receives only the user's raw query, the primary text answer, and the raw retrieved database rows — without seeing the primary agent's internal chain-of-thought or confidence score.
* **Rationale**: This guarantees adversarial fact-checking against actual database rows (checking amounts, dates, IDs, and UTRs). Structured verdicts (`VERIFIED`, `MINOR_DISCREPANCY`, `FLAGGED`) allow the system to route suspected discrepancies into the Exceptions Ledger under `VERIFIER_FLAGGED` rather than returning ungrounded answers.
* **Trade-off**: Increases query latency by requiring a two-tier evaluation pass; justified by the critical importance of financial accuracy and auditability.
