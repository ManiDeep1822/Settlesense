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
    intent: Optional[str] = "ENTITY_LOOKUP"

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

class ExceptionItem(BaseModel):
    id: str
    query_text: str
    exception_type: str
    reason: str
    detected_at: Optional[str] = None
    timestamp: Optional[str] = None
    status: str
    resolved_at: Optional[str] = None
    resolution_notes: Optional[str] = None
    target_record_id: Optional[str] = None
    confidence_score: Optional[float] = 0.0
    candidate_record_ids: Optional[str] = None

ExceptionLogItem = ExceptionItem

class PaginatedExceptionsResponse(BaseModel):
    items: List[ExceptionItem]
    total: int
    page: int
    page_size: int
    unresolved_count: int

class ExceptionResolveRequest(BaseModel):
    status: str = "RESOLVED"
    resolution_notes: str = ""

ResolveExceptionRequest = ExceptionResolveRequest

class AccuracyTestCaseResult(BaseModel):
    test_id: str
    category: str
    question: str
    expected_action: str
    verdict: str
    verifier_verdict: Optional[str] = "VERIFIED"
    verifier_notes: Optional[str] = None
    expected_answer_snippet: Optional[str] = None
    actual_answer: str
    confidence: str
    engine_used: str = "fallback"
    engine_used_primary: Optional[str] = "fallback"
    engine_used_verifier: Optional[str] = "fallback"
    cited_record_ids: List[str]
    latency_ms: float
    notes: str

class EnginePerformanceStats(BaseModel):
    total: int = 0
    passed: int = 0
    correctly_declined: int = 0
    failed: int = 0
    accuracy_percentage: float = 0.0
    avg_latency_ms: float = 0.0

class VerifierPerformanceStats(BaseModel):
    total_audits: int = 0
    verified_count: int = 0
    minor_discrepancy_count: int = 0
    flagged_count: int = 0
    no_audit_needed_count: int = 0
    agreement_rate_percent: float = 0.0
    catch_rate_percent: float = 0.0
    false_flag_rate_percent: float = 0.0

class CategoryStats(BaseModel):
    total: int = 0
    passed: int = 0
    correctly_declined: int = 0
    partially_passed: int = 0
    failed: int = 0

class AccuracyReportResponse(BaseModel):
    id: str
    run_timestamp: str
    total_tests: int
    passed: int
    correctly_declined: int
    partially_passed: int
    failed: int
    accuracy_percentage: float
    avg_latency_ms: float
    verifier_performance: Optional[VerifierPerformanceStats] = None
    engine_breakdown: Optional[Dict[str, EnginePerformanceStats]] = None
    category_breakdown: Dict[str, CategoryStats]
    test_cases: List[AccuracyTestCaseResult]

class DashboardMetricsResponse(BaseModel):
    total_settled_volume: float = 0.0
    total_transactions_count: int = 0
    reconciliation_match_rate: float = 0.0
    avg_query_latency_ms: float = 0.0
    active_exceptions_count: int = 0
    accuracy_score: float = 93.3
    pending_payout_volume: float = 0.0
    delayed_transactions_count: int = 0

class MetricsResponse(BaseModel):
    queries_per_sec: float = 0.0
    avg_response_time_ms: float = 0.0
    total_queries: int = 0
    records_indexed: int = 0
    total_transactions: int = 0
    total_settlements: int = 0
    exception_count: int = 0
    unresolved_exception_count: int = 0
    reconciliation_rate_percent: float = 0.0
    accuracy_score: float = 93.3

class SummaryKPIResponse(BaseModel):
    total_settled_amount: float = 0.0
    pending_payout_amount: float = 0.0
    total_transactions_count: int = 0
    matched_count: int = 0
    exception_count: int = 0
    reconciliation_rate: float = 0.0
    avg_query_latency_ms: float = 0.0
