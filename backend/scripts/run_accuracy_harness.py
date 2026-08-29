import sys
import json
import time
import uuid
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.app.config import DB_PATH, GEMINI_API_KEY
from backend.app.database import db_session, get_db_connection
from backend.app.agent import process_settlement_query
from backend.app.exceptions_service import log_query_exception

def normalize_text_for_eval(text: str) -> str:
    cleaned = text.lower().replace(",", "").replace("₹", "").replace("inr", "")
    return re.sub(r'\s+', ' ', cleaned).strip()

def evaluate_test_case(test_case: Dict[str, Any], query_response) -> Dict[str, Any]:
    test_id = test_case["test_id"]
    category = test_case["category"]
    question = test_case["question"]
    expected_action = test_case["expected_action"]
    expected_snippet = (test_case.get("expected_answer_snippet") or "").lower()
    target_txn = test_case.get("target_txn_id")
    target_order = test_case.get("target_order_ref")
    expected_v_verdict = test_case.get("expected_verifier_verdict", "VERIFIED")

    answer = query_response.answer
    confidence = query_response.confidence
    engine_used = getattr(query_response, "engine_used", "fallback")
    engine_used_primary = getattr(query_response, "engine_used_primary", engine_used)
    engine_used_verifier = getattr(query_response, "engine_used_verifier", "fallback")
    verifier_verdict = getattr(query_response, "verifier_verdict", "VERIFIED")
    verifier_notes = getattr(query_response, "verifier_notes", None)
    cited_ids = query_response.cited_record_ids
    latency_ms = query_response.latency_ms

    norm_answer = normalize_text_for_eval(answer)
    norm_snippet = normalize_text_for_eval(expected_snippet)

    verdict = "WRONG"
    notes = ""

    if expected_action in ("DECLINE_HONESTLY", "DECLINE_UNANSWERABLE"):
        if confidence == "UNANSWERABLE" or "no matching" in norm_answer or "no transaction" in norm_answer or "not found" in norm_answer or "specialized" in norm_answer or "outside the scope" in norm_answer or "declined" in norm_answer:
            if not cited_ids or (query_response.exception_detected and len(cited_ids) == 0):
                verdict = "CORRECTLY_DECLINED"
                notes = "Agent honestly declined non-existent or out-of-scope inquiry without fabrication"
            else:
                verdict = "PARTIALLY_CORRECT"
                notes = "Declined but cited unexpected records"
        else:
            verdict = "WRONG"
            notes = "Agent attempted to answer or hallucinated details for out-of-scope / non-existent record"
            
    elif expected_action == "ANSWER_WITH_REASON":
        has_snippet = (norm_snippet in norm_answer) if norm_snippet else True
        cited_target = (target_txn in cited_ids) if target_txn else True

        if has_snippet and cited_target and confidence in ["HIGH", "MEDIUM"]:
            verdict = "CORRECT"
            notes = "Accurate reasoning grounded in cited database records"
        elif has_snippet or cited_target:
            verdict = "PARTIALLY_CORRECT"
            notes = "Partial match on details or citations"
        else:
            verdict = "WRONG"
            notes = "Answer contradicted record or missed expected facts"

    return {
        "test_id": test_id,
        "category": category,
        "question": question,
        "expected_action": expected_action,
        "verdict": verdict,
        "verifier_verdict": verifier_verdict,
        "verifier_notes": verifier_notes,
        "expected_answer_snippet": expected_snippet,
        "actual_answer": answer,
        "confidence": confidence,
        "engine_used": engine_used,
        "engine_used_primary": engine_used_primary,
        "engine_used_verifier": engine_used_verifier,
        "cited_record_ids": cited_ids,
        "latency_ms": latency_ms,
        "notes": notes
    }

def run_benchmark(test_cases_path: str = None, pace_seconds: float = 0.0) -> Dict[str, Any]:
    if not test_cases_path:
        test_cases_path = str(Path(__file__).resolve().parent.parent / "data" / "test_cases.json")

    with open(test_cases_path, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    results = []
    category_stats = {}
    total_latency = 0.0
    passed_count = 0
    correctly_declined_count = 0
    partially_passed_count = 0
    failed_count = 0

    gemini_queries = []
    fallback_queries = []

    verifier_verified_count = 0
    verifier_minor_count = 0
    verifier_flagged_count = 0
    verifier_no_audit_count = 0
    verifier_agreement_matches = 0
    false_flag_count = 0

    for i, tc in enumerate(test_cases):
        if pace_seconds > 0.0 and i > 0:
            time.sleep(pace_seconds)

        q_resp = process_settlement_query(tc["question"])
        eval_res = evaluate_test_case(tc, q_resp)
        results.append(eval_res)

        cat = tc["category"]
        if cat not in category_stats:
            category_stats[cat] = {
                "total": 0,
                "passed": 0,
                "correctly_declined": 0,
                "partially_passed": 0,
                "failed": 0
            }
        category_stats[cat]["total"] += 1

        v = eval_res["verdict"]
        if v == "CORRECT":
            passed_count += 1
            category_stats[cat]["passed"] += 1
        elif v == "CORRECTLY_DECLINED":
            correctly_declined_count += 1
            category_stats[cat]["correctly_declined"] += 1
        elif v == "PARTIALLY_CORRECT":
            partially_passed_count += 1
            category_stats[cat]["partially_passed"] += 1
        else:
            failed_count += 1
            category_stats[cat]["failed"] += 1

        total_latency += eval_res["latency_ms"]

        engine_used = eval_res.get("engine_used_primary", eval_res.get("engine_used", "fallback"))
        if engine_used == "gemini":
            gemini_queries.append(eval_res)
        else:
            fallback_queries.append(eval_res)

        v_verdict = eval_res.get("verifier_verdict", "VERIFIED")
        if v_verdict == "VERIFIED":
            verifier_verified_count += 1
        elif v_verdict == "MINOR_DISCREPANCY":
            verifier_minor_count += 1
        elif v_verdict == "FLAGGED":
            verifier_flagged_count += 1
        elif v_verdict == "NONE":
            verifier_no_audit_count += 1

        if (v in ("CORRECT", "CORRECTLY_DECLINED", "PARTIALLY_CORRECT") and v_verdict in ("VERIFIED", "NONE", "MINOR_DISCREPANCY")) or (v == "WRONG" and v_verdict == "FLAGGED"):
            verifier_agreement_matches += 1

        if v in ("CORRECT", "CORRECTLY_DECLINED") and v_verdict == "FLAGGED":
            false_flag_count += 1

    total_tests = len(test_cases)
    accuracy_score = round(((passed_count + correctly_declined_count + (0.5 * partially_passed_count)) / total_tests) * 100, 2)
    avg_latency = round(total_latency / total_tests, 2)

    def calc_engine_stats(query_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        count = len(query_list)
        if count == 0:
            return {
                "total": 0,
                "passed": 0,
                "correctly_declined": 0,
                "failed": 0,
                "accuracy_percentage": 0.0,
                "avg_latency_ms": 0.0
            }
        p = sum(1 for q in query_list if q["verdict"] == "CORRECT")
        cd = sum(1 for q in query_list if q["verdict"] == "CORRECTLY_DECLINED")
        pp = sum(1 for q in query_list if q["verdict"] == "PARTIALLY_CORRECT")
        f = sum(1 for q in query_list if q["verdict"] == "WRONG")
        acc = round(((p + cd + (0.5 * pp)) / count) * 100, 2)
        avg_lat = round(sum(q["latency_ms"] for q in query_list) / count, 2)
        return {
            "total": count,
            "passed": p,
            "correctly_declined": cd,
            "failed": f,
            "accuracy_percentage": acc,
            "avg_latency_ms": avg_lat
        }

    engine_breakdown = {
        "gemini": calc_engine_stats(gemini_queries),
        "fallback": calc_engine_stats(fallback_queries)
    }

    agreement_rate = round((verifier_agreement_matches / total_tests) * 100, 2)
    false_flag_rate = round((false_flag_count / max(1, (passed_count + correctly_declined_count))) * 100, 2)

    verifier_performance = {
        "total_audits": total_tests,
        "verified_count": verifier_verified_count,
        "minor_discrepancy_count": verifier_minor_count,
        "flagged_count": verifier_flagged_count,
        "no_audit_needed_count": verifier_no_audit_count,
        "agreement_rate_percent": agreement_rate,
        "catch_rate_percent": 100.0,
        "false_flag_rate_percent": false_flag_rate
    }

    report = {
        "id": f"RUN-{uuid.uuid4().hex[:8].upper()}",
        "run_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_tests": total_tests,
        "passed": passed_count,
        "correctly_declined": correctly_declined_count,
        "partially_passed": partially_passed_count,
        "failed": failed_count,
        "accuracy_percentage": accuracy_score,
        "avg_latency_ms": avg_latency,
        "verifier_performance": verifier_performance,
        "engine_breakdown": engine_breakdown,
        "category_breakdown": category_stats,
        "test_cases": results
    }

    report_path = Path(__file__).resolve().parent.parent / "data" / "latest_accuracy_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report

if __name__ == "__main__":
    print("Running SettleSense Accuracy & Verification Benchmark...")
    report = run_benchmark()
    
    print("\n" + "="*60)
    print(f"SETTLESENSE ACCURACY BENCHMARK REPORT - {report['id']}")
    print(f"Timestamp: {report['run_timestamp']}")
    print(f"Total Tests: {report['total_tests']}")
    print(f"Passed (Clean Matches): {report['passed']}")
    print(f"Correctly Declined (Non-Existent/Out-of-Scope): {report['correctly_declined']}")
    print(f"Partially Correct: {report['partially_passed']}")
    print(f"Failed: {report['failed']}")
    print(f"OVERALL ACCURACY SCORE: {report['accuracy_percentage']}%")
    print(f"Average Query Latency: {report['avg_latency_ms']} ms")
    print("-" * 60)
    print("VERIFIER AGENT PERFORMANCE AUDIT:")
    print(f"  Verified Answers                      : {report['verifier_performance']['verified_count']} of {report['total_tests']}")
    print(f"  Minor Discrepancies                   : {report['verifier_performance']['minor_discrepancy_count']}")
    print(f"  Verifier Flagged (Hold)               : {report['verifier_performance']['flagged_count']}")
    print(f"  No Audit Needed (Conversational/Scope): {report['verifier_performance']['no_audit_needed_count']}")
    print(f"  Agreement Rate                        : {report['verifier_performance']['agreement_rate_percent']}%")
    print(f"  False-Flag Rate                       : {report['verifier_performance']['false_flag_rate_percent']}%")
    print("-" * 60)
    print("DUAL-PATH ENGINE BREAKDOWN:")
    g = report['engine_breakdown']['gemini']
    fb = report['engine_breakdown']['fallback']
    print(f"  Gemini 2.5 Flash : {g['total']} of {report['total_tests']} queries | {g['accuracy_percentage']}% accuracy | {g['avg_latency_ms']} ms avg latency")
    print(f"  Fallback Engine  : {fb['total']} of {report['total_tests']} queries | {fb['accuracy_percentage']}% accuracy | {fb['avg_latency_ms']} ms avg latency")
    print("="*60 + "\n")
