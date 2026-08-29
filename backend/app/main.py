import json
import math
from typing import Optional
from fastapi import FastAPI, Query as FastQuery, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.app.database import init_db, get_db_connection
from backend.app.schemas import (
    QueryRequest, QueryResponse, PaginatedTransactionsResponse, TransactionItem,
    ExceptionLogItem, ExceptionResolveRequest, AccuracyReportResponse, MetricsResponse, SummaryKPIResponse
)
from backend.app.agent import process_settlement_query
from backend.app.exceptions_service import log_query_exception, list_logged_exceptions, update_exception_status
from backend.app.metrics_service import log_query_metric, get_system_metrics, get_financial_summary
from backend.scripts.run_accuracy_harness import run_benchmark

app = FastAPI(title="SettleSense API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

@app.post("/query", response_model=QueryResponse)
def handle_query(payload: QueryRequest):
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")
        
    result = process_settlement_query(payload.query, payload.merchant_id)
    
    log_query_metric(
        query_text=payload.query,
        response_text=result.answer,
        confidence=result.confidence,
        cited_record_ids=result.cited_record_ids,
        latency_ms=result.latency_ms
    )

    if result.exception_detected or result.confidence in ["LOW", "UNANSWERABLE"]:
        log_query_exception(
            query_text=payload.query,
            exception_type=result.exception_type or "LOW_CONFIDENCE_QUERY",
            reason=result.exception_reason or "System unable to establish direct grounded match.",
            confidence_score=result.confidence_score,
            candidate_record_ids=result.cited_record_ids
        )

    return result

@app.get("/transactions", response_model=PaginatedTransactionsResponse)
def get_transactions(
    page: int = FastQuery(1, ge=1),
    page_size: int = FastQuery(10, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    conn = get_db_connection()
    cursor = conn.cursor()

    query_parts = ["SELECT * FROM transactions WHERE 1=1"]
    count_parts = ["SELECT COUNT(*) FROM transactions WHERE 1=1"]
    params = []

    if status and status.lower() != "all":
        query_parts.append("AND LOWER(status) = LOWER(?)")
        count_parts.append("AND LOWER(status) = LOWER(?)")
        params.append(status)

    if search:
        search_wild = f"%{search}%"
        query_parts.append("AND (id LIKE ? OR order_ref LIKE ? OR bank_ref LIKE ? OR customer_email LIKE ?)")
        count_parts.append("AND (id LIKE ? OR order_ref LIKE ? OR bank_ref LIKE ? OR customer_email LIKE ?)")
        params.extend([search_wild, search_wild, search_wild, search_wild])

    if min_amount is not None:
        query_parts.append("AND amount >= ?")
        count_parts.append("AND amount >= ?")
        params.append(min_amount)

    if max_amount is not None:
        query_parts.append("AND amount <= ?")
        count_parts.append("AND amount <= ?")
        params.append(max_amount)

    if start_date:
        query_parts.append("AND DATE(created_at) >= DATE(?)")
        count_parts.append("AND DATE(created_at) >= DATE(?)")
        params.append(start_date)

    if end_date:
        query_parts.append("AND DATE(created_at) <= DATE(?)")
        count_parts.append("AND DATE(created_at) <= DATE(?)")
        params.append(end_date)

    cursor.execute(" ".join(count_parts), params)
    total_count = cursor.fetchone()[0]

    offset = (page - 1) * page_size
    query_parts.append("ORDER BY created_at DESC LIMIT ? OFFSET ?")
    params.extend([page_size, offset])

    cursor.execute(" ".join(query_parts), params)
    rows = cursor.fetchall()
    conn.close()

    items = [
        TransactionItem(
            id=r["id"],
            order_ref=r["order_ref"],
            merchant_id=r["merchant_id"],
            amount=float(r["amount"]),
            fee=float(r["fee"]),
            tax=float(r["tax"]),
            net_amount=float(r["net_amount"]),
            currency=r["currency"],
            status=r["status"],
            payment_method=r["payment_method"],
            customer_email=r["customer_email"],
            created_at=r["created_at"],
            settlement_date=r["settlement_date"],
            settlement_id=r["settlement_id"],
            bank_ref=r["bank_ref"],
            failure_reason=r["failure_reason"],
            dispute_status=r["dispute_status"],
            refund_amount=float(r["refund_amount"] or 0.0),
            notes=r["notes"]
        ) for r in rows
    ]

    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1

    return PaginatedTransactionsResponse(
        items=items,
        total=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

@app.get("/exceptions")
def get_exceptions(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    return list_logged_exceptions(status_filter=status, limit=limit, offset=offset)

@app.post("/exceptions/{exception_id}/resolve")
def resolve_exception_endpoint(exception_id: str, payload: ExceptionResolveRequest):
    success = update_exception_status(exception_id, payload.status, payload.resolution_notes)
    if not success:
        raise HTTPException(status_code=404, detail="Exception record not found.")
    return {"status": "success", "id": exception_id, "new_status": payload.status}

@app.get("/accuracy-report", response_model=AccuracyReportResponse)
def get_latest_accuracy_report():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT results_json FROM accuracy_runs ORDER BY run_timestamp DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()

    if row:
        return json.loads(row["results_json"])
    
    report = run_benchmark()
    return report

@app.post("/accuracy-report/run", response_model=AccuracyReportResponse)
def trigger_accuracy_benchmark():
    return run_benchmark()

@app.get("/metrics", response_model=MetricsResponse)
def get_metrics_endpoint():
    return get_system_metrics()

@app.get("/summary", response_model=SummaryKPIResponse)
def get_financial_summary_endpoint():
    return get_financial_summary()
