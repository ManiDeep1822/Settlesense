from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    query: str
    merchant_id: Optional[str] = None

class CitedRecord(BaseModel):
    id: str
    order_ref: str
    amount: float
    status: str
    settlement_date: Optional[str] = None
    bank_ref: Optional[str] = None
    settlement_id: Optional[str] = None
    fee: Optional[float] = 0.0
    tax: Optional[float] = 0.0
    net_amount: Optional[float] = 0.0
    failure_reason: Optional[str] = None
    refund_amount: Optional[float] = 0.0

class QueryResponse(BaseModel):
    answer: str
    confidence: str
    confidence_score: float
    engine_used: str = "fallback"
    engine_used_primary: str = "fallback"
    engine_used_verifier: str = "fallback"
    verifier_verdict: str = "VERIFIED"
    verifier_notes: Optional[str] = None
    discrepancies: List[str] = []
    cited_records: List[CitedRecord] = []
    cited_record_ids: List[str] = []
    exception_detected: bool = False
    exception_type: Optional[str] = None
    exception_reason: Optional[str] = None
    latency_ms: float = 0.0

class TransactionItem(BaseModel):
    id: str
    order_ref: str
    merchant_id: str
    amount: float
    fee: float
    tax: float
    net_amount: float
    currency: str
    status: str
    payment_method: str
    customer_email: Optional[str] = None
    created_at: str
    settlement_date: Optional[str] = None
    settlement_id: Optional[str] = None
    bank_ref: Optional[str] = None
    failure_reason: Optional[str] = None
    dispute_status: Optional[str] = None
    refund_amount: float = 0.0
    notes: Optional[str] = None

class PaginatedTransactionsResponse(BaseModel):
    items: List[TransactionItem]
    total: int
    page: int
    page_size: int
    total_pages: int

class ExceptionLogItem(BaseModel):
    id: str
    query_text: str
    exception_type: str
    reason: str
    confidence_score: float
    candidate_record_ids: Optional[str] = None
    timestamp: str
    status: str
    resolution_notes: Optional[str] = None

class ExceptionResolveRequest(BaseModel):
    status: str
    resolution_notes: Optional[str] = None

class AccuracyTestCaseResult(BaseModel):
    test_id: str
    category: str
    question: str
    expected_action: str
    verdict: str
    verifier_verdict: str = "VERIFIED"
    verifier_notes: Optional[str] = None
    expected_answer_snippet: Optional[str] = None
    actual_answer: str
    confidence: str
    engine_used: str = "fallback"
    engine_used_primary: str = "fallback"
    engine_used_verifier: str = "fallback"
    cited_record_ids: List[str]
    latency_ms: float
    notes: Optional[str] = None

class AccuracyReportResponse(BaseModel):
    id: str
    run_timestamp: str
    total_tests: int
    passed: int
    partially_passed: int
    failed: int
    correctly_declined: int
    accuracy_percentage: float
    avg_latency_ms: float
    verifier_performance: Dict[str, Any] = {}
    engine_breakdown: Dict[str, Any] = {}
    category_breakdown: Dict[str, Dict[str, Any]] = {}
    test_cases: List[AccuracyTestCaseResult] = []

class MetricsResponse(BaseModel):
    queries_per_sec: float
    avg_response_time_ms: float
    total_queries: int
    records_indexed: int
    total_transactions: int
    total_settlements: int
    exception_count: int
    unresolved_exception_count: int
    reconciliation_rate_percent: float

class SummaryKPIResponse(BaseModel):
    total_settled_amount: float
    pending_payout_amount: float
    total_transactions_count: int
    matched_count: int
    exception_count: int
    reconciliation_rate: float
    avg_query_latency_ms: float
