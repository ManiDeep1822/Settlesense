import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from backend.app.database import get_db_connection, db_session
from backend.app.schemas import ExceptionLogItem

def log_query_exception(
    query_text: str,
    exception_type: str,
    reason: str,
    confidence_score: float,
    candidate_record_ids: Optional[List[str]] = None
) -> str:
    exc_id = f"EXC-{uuid.uuid4().hex[:8].upper()}"
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    candidate_str = ",".join(candidate_record_ids) if candidate_record_ids else None

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO exceptions_log (
                id, query_text, exception_type, reason, confidence_score,
                candidate_record_ids, timestamp, status, resolution_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'UNRESOLVED', NULL)
        """, (
            exc_id, query_text, exception_type, reason, confidence_score,
            candidate_str, timestamp_str
        ))

    return exc_id

def list_logged_exceptions(status_filter: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[ExceptionLogItem]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if status_filter and status_filter.upper() != "ALL":
        cursor.execute("""
            SELECT * FROM exceptions_log 
            WHERE UPPER(status) = UPPER(?) 
            ORDER BY timestamp DESC LIMIT ? OFFSET ?
        """, (status_filter, limit, offset))
    else:
        cursor.execute("""
            SELECT * FROM exceptions_log 
            ORDER BY timestamp DESC LIMIT ? OFFSET ?
        """, (limit, offset))
        
    rows = cursor.fetchall()
    conn.close()

    items = []
    for r in rows:
        items.append(ExceptionLogItem(
            id=r["id"],
            query_text=r["query_text"],
            exception_type=r["exception_type"],
            reason=r["reason"],
            confidence_score=float(r["confidence_score"]),
            candidate_record_ids=r["candidate_record_ids"],
            timestamp=r["timestamp"],
            status=r["status"],
            resolution_notes=r["resolution_notes"]
        ))
    return items

def update_exception_status(exception_id: str, new_status: str, notes: Optional[str] = None) -> bool:
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE exceptions_log
            SET status = ?, resolution_notes = ?
            WHERE id = ?
        """, (new_status.upper(), notes, exception_id))
        return cursor.rowcount > 0
