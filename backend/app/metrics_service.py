import time
import uuid
from datetime import datetime
from typing import Dict, Any

from backend.app.database import get_db_connection, db_session
from backend.app.schemas import MetricsResponse, SummaryKPIResponse

def log_query_metric(query_text: str, response_text: str, confidence: str, cited_record_ids: list, latency_ms: float):
    log_id = f"LOG-{uuid.uuid4().hex[:8].upper()}"
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cited_str = ",".join(cited_record_ids) if cited_record_ids else ""

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO query_logs (
                id, query_text, response_text, confidence, cited_record_ids, latency_ms, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (log_id, query_text, response_text, confidence, cited_str, latency_ms, timestamp_str))

def get_system_metrics() -> MetricsResponse:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*), AVG(latency_ms) FROM query_logs")
    query_stats = cursor.fetchone()
    total_queries = query_stats[0] or 0
    avg_latency = round(query_stats[1] or 0.0, 2)

    cursor.execute("SELECT COUNT(*) FROM transactions")
    total_txns = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM settlements")
    total_settles = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM transactions WHERE status = 'matched'")
    matched_count = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM exceptions_log")
    total_exceptions = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM exceptions_log WHERE status = 'UNRESOLVED'")
    unresolved_exceptions = cursor.fetchone()[0] or 0

    conn.close()

    reconciliation_rate = round((matched_count / total_txns * 100), 2) if total_txns > 0 else 0.0
    qps = round(1000.0 / avg_latency, 2) if avg_latency > 0 else 0.0

    return MetricsResponse(
        queries_per_sec=qps,
        avg_response_time_ms=avg_latency,
        total_queries=total_queries,
        records_indexed=total_txns + total_settles,
        total_transactions=total_txns,
        total_settlements=total_settles,
        exception_count=total_exceptions,
        unresolved_exception_count=unresolved_exceptions,
        reconciliation_rate_percent=reconciliation_rate
    )

def get_financial_summary() -> SummaryKPIResponse:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT SUM(net_amount) FROM transactions WHERE status = 'matched'")
    total_settled = cursor.fetchone()[0] or 0.0

    cursor.execute("SELECT SUM(net_amount) FROM transactions WHERE status IN ('pending', 'delayed')")
    pending_payout = cursor.fetchone()[0] or 0.0

    cursor.execute("SELECT COUNT(*) FROM transactions")
    total_txns = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM transactions WHERE status = 'matched'")
    matched = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM transactions WHERE status IN ('exception', 'declined', 'unmatched')")
    exceptions = cursor.fetchone()[0] or 0

    cursor.execute("SELECT AVG(latency_ms) FROM query_logs")
    avg_latency = round(cursor.fetchone()[0] or 14.5, 2)

    conn.close()

    recon_rate = round((matched / total_txns * 100), 2) if total_txns > 0 else 0.0

    return SummaryKPIResponse(
        total_settled_amount=round(total_settled, 2),
        pending_payout_amount=round(pending_payout, 2),
        total_transactions_count=total_txns,
        matched_count=matched,
        exception_count=exceptions,
        reconciliation_rate=recon_rate,
        avg_query_latency_ms=avg_latency
    )
