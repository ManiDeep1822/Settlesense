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

    if expected_action == "DECLINE_HONESTLY":
        if confidence == "UNANSWERABLE" or "no matching" in norm_answer or "no transaction" in norm_answer or "not found" in norm_answer or "declined" in norm_answer:
            if not cited_ids or (query_response.exception_detected and len(cited_ids) == 0):
                verdict = "CORRECTLY_DECLINED"
                notes = "Agent honestly declined non-existent record without fabrication"
            else:
                verdict = "PARTIALLY_CORRECT"
                notes = "Declined but cited unexpected records"
        else:
            verdict = "WRONG"
            notes = "Agent attempted to answer or hallucinated details for non-existent record"
            
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
    engine_stats = {
        "gemini": {"total": 0, "passed": 0, "correctly_declined": 0, "failed": 0, "latencies": []},
        "fallback": {"total": 0, "passed": 0, "correctly_declined": 0, "failed": 0, "latencies": []}
    }

    verified_count = 0
    minor_discrepancy_count = 0
    flagged_count = 0
    true_positive_flags = 0
    false_positive_flags = 0

    for idx, tc in enumerate(test_cases):
        if pace_seconds > 0 and idx > 0:
            time.sleep(pace_seconds)

        res = process_settlement_query(tc["question"])
        eval_result = evaluate_test_case(tc, res)
        results.append(eval_result)

        v_verdict = eval_result["verifier_verdict"]
        if v_verdict == "VERIFIED":
            verified_count += 1
        elif v_verdict == "MINOR_DISCREPANCY":
            minor_discrepancy_count += 1
        elif v_verdict == "FLAGGED":
            flagged_count += 1

        if eval_result["verdict"] in ["CORRECT", "CORRECTLY_DECLINED"] and v_verdict == "FLAGGED":
            false_positive_flags += 1
        elif eval_result["verdict"] == "WRONG" and v_verdict == "FLAGGED":
            true_positive_flags += 1

        eng = eval_result["engine_used_primary"]
        if eng not in engine_stats:
            engine_stats[eng] = {"total": 0, "passed": 0, "correctly_declined": 0, "failed": 0, "latencies": []}
        engine_stats[eng]["total"] += 1
        engine_stats[eng]["latencies"].append(eval_result["latency_ms"])

        cat = tc["category"]
        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "passed": 0, "correctly_declined": 0, "partially_passed": 0, "failed": 0}
        category_stats[cat]["total"] += 1
        v = eval_result["verdict"]
        if v == "CORRECT":
            category_stats[cat]["passed"] += 1
            engine_stats[eng]["passed"] += 1
        elif v == "CORRECTLY_DECLINED":
            category_stats[cat]["correctly_declined"] += 1
            engine_stats[eng]["correctly_declined"] += 1
        elif v == "PARTIALLY_CORRECT":
            category_stats[cat]["partially_passed"] += 1
        else:
            category_stats[cat]["failed"] += 1
            engine_stats[eng]["failed"] += 1

    total_tests = len(results)
    passed = sum(1 for r in results if r["verdict"] == "CORRECT")
    correctly_declined = sum(1 for r in results if r["verdict"] == "CORRECTLY_DECLINED")
    partially_passed = sum(1 for r in results if r["verdict"] == "PARTIALLY_CORRECT")
    failed = sum(1 for r in results if r["verdict"] == "WRONG")

    successful = passed + correctly_declined
    accuracy_pct = round((successful / total_tests) * 100.0, 2) if total_tests > 0 else 0.0
    avg_latency = round(sum(r["latency_ms"] for r in results) / total_tests, 2) if total_tests > 0 else 0.0

    agreement_rate = round(((verified_count + minor_discrepancy_count) / total_tests) * 100.0, 2) if total_tests > 0 else 0.0
    catch_rate = 100.0 if failed == 0 else round((true_positive_flags / failed) * 100.0, 2)
    false_flag_rate = round((false_positive_flags / total_tests) * 100.0, 2) if total_tests > 0 else 0.0

    verifier_performance = {
        "total_audits": total_tests,
        "verified_count": verified_count,
        "minor_discrepancy_count": minor_discrepancy_count,
        "flagged_count": flagged_count,
        "agreement_rate_percent": agreement_rate,
        "catch_rate_percent": catch_rate,
        "false_flag_rate_percent": false_flag_rate
    }

    engine_summary = {}
    for eng_name, d in engine_stats.items():
        if d["total"] > 0:
            eng_succ = d["passed"] + d["correctly_declined"]
            eng_acc = round((eng_succ / d["total"]) * 100.0, 2)
            eng_lat = round(sum(d["latencies"]) / d["total"], 2)
            engine_summary[eng_name] = {
                "total": d["total"],
                "passed": d["passed"],
                "correctly_declined": d["correctly_declined"],
                "failed": d["failed"],
                "accuracy_percentage": eng_acc,
                "avg_latency_ms": eng_lat
            }
        else:
            engine_summary[eng_name] = {
                "total": 0,
                "passed": 0,
                "correctly_declined": 0,
                "failed": 0,
                "accuracy_percentage": 0.0,
                "avg_latency_ms": 0.0
            }

    run_id = f"RUN-{uuid.uuid4().hex[:8].upper()}"
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report_payload = {
        "id": run_id,
        "run_timestamp": timestamp_str,
        "total_tests": total_tests,
        "passed": passed,
        "correctly_declined": correctly_declined,
        "partially_passed": partially_passed,
        "failed": failed,
        "accuracy_percentage": accuracy_pct,
        "avg_latency_ms": avg_latency,
        "verifier_performance": verifier_performance,
        "engine_breakdown": engine_summary,
        "category_breakdown": category_stats,
        "test_cases": results
    }

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO accuracy_runs (
                id, run_timestamp, total_tests, passed, partially_passed,
                failed, correctly_declined, accuracy_percentage, avg_latency_ms, results_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id, timestamp_str, total_tests, passed, partially_passed,
            failed, correctly_declined, accuracy_pct, avg_latency, json.dumps(report_payload)
        ))

    report_output_path = Path(__file__).resolve().parent.parent / "data" / "latest_accuracy_report.json"
    with open(report_output_path, "w", encoding="utf-8") as f:
        json.dump(report_payload, f, indent=2)

    return report_payload

if __name__ == "__main__":
    pace = 0.0
    if len(sys.argv) > 1:
        try:
            pace = float(sys.argv[1])
        except ValueError:
            pass

    report = run_benchmark(pace_seconds=pace)
    print("=" * 60)
    print(f"SETTLESENSE ACCURACY BENCHMARK REPORT - {report['id']}")
    print(f"Timestamp: {report['run_timestamp']}")
    print(f"Total Tests: {report['total_tests']}")
    print(f"Passed (Clean Matches): {report['passed']}")
    print(f"Correctly Declined (Non-Existent): {report['correctly_declined']}")
    print(f"Partially Correct: {report['partially_passed']}")
    print(f"Failed: {report['failed']}")
    print(f"OVERALL ACCURACY SCORE: {report['accuracy_percentage']}%")
    print(f"Average Query Latency: {report['avg_latency_ms']} ms")
    print("-" * 60)
    print("VERIFIER AGENT PERFORMANCE AUDIT:")
    vp = report.get("verifier_performance", {})
    print(f" • Verified Answers      : {vp.get('verified_count', 0)} of {report['total_tests']}")
    print(f" • Minor Discrepancies   : {vp.get('minor_discrepancy_count', 0)}")
    print(f" • Verifier Flagged (Hold): {vp.get('flagged_count', 0)}")
    print(f" • Agreement Rate        : {vp.get('agreement_rate_percent', 0)}%")
    print(f" • False-Flag Rate       : {vp.get('false_flag_rate_percent', 0)}%")
    print("-" * 60)
    print("DUAL-PATH ENGINE BREAKDOWN:")
    gem = report.get("engine_breakdown", {}).get("gemini", {})
    fb = report.get("engine_breakdown", {}).get("fallback", {})
    print(f" • Gemini 2.5 Flash : {gem.get('total', 0)} of {report['total_tests']} queries | {gem.get('accuracy_percentage', 0)}% accuracy | {gem.get('avg_latency_ms', 0)} ms avg latency")
    print(f" • Fallback Engine  : {fb.get('total', 0)} of {report['total_tests']} queries | {fb.get('accuracy_percentage', 0)}% accuracy | {fb.get('avg_latency_ms', 0)} ms avg latency")
    print("=" * 60)
