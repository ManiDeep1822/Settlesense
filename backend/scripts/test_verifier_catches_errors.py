import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from backend.app.database import get_db_connection
from backend.app.verifier import verify_settlement_answer

def run_wrong_answer_injection_test():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions LIMIT 5")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    if len(rows) < 5:
        print("Error: Less than 5 transactions in database.")
        sys.exit(1)

    t1, t2, t3, t4, t5 = rows[0], rows[1], rows[2], rows[3], rows[4]

    test_scenarios = [
        {
            "name": "Case 1: Fabricated Gross Amount (Injected Error)",
            "query": f"What was the amount for order {t1['order_ref']}?",
            "wrong_answer": f"Order {t1['order_ref']} (Transaction {t1['id']}) had a gross amount of INR 999,999.00 and net payout of INR 980,000.00.",
            "cited_ids": [t1["id"]],
            "raw_records": [t1],
            "expected_verdicts": ["FLAGGED", "MINOR_DISCREPANCY"]
        },
        {
            "name": "Case 2: Inverted Status Contradiction (Injected Error)",
            "query": f"Why did order {t2['order_ref']} fail?",
            "wrong_answer": f"Order {t2['order_ref']} (Transaction {t2['id']}) was successfully settled on {t2.get('settlement_date') or '2023-10-24'}.",
            "cited_ids": [t2["id"]],
            "raw_records": [{**t2, "status": "declined", "failure_reason": "Card expired"}],
            "expected_verdicts": ["FLAGGED"]
        },
        {
            "name": "Case 3: Fabricated Settlement Date (Injected Error)",
            "query": f"When did order {t3['order_ref']} settle?",
            "wrong_answer": f"Order {t3['order_ref']} (Transaction {t3['id']}) settled on 2029-12-31 with bank UTR {t3.get('bank_ref') or 'CHASE-001'}.",
            "cited_ids": [t3["id"]],
            "raw_records": [{**t3, "settlement_date": "2023-10-24"}],
            "expected_verdicts": ["FLAGGED", "MINOR_DISCREPANCY"]
        },
        {
            "name": "Case 4: Ungrounded Citation ID (Injected Error)",
            "query": f"Trace transaction for order {t4['order_ref']}",
            "wrong_answer": f"Order {t4['order_ref']} was captured under transaction TXN-9999-FAKE99.",
            "cited_ids": ["TXN-9999-FAKE99"],
            "raw_records": [t4],
            "expected_verdicts": ["FLAGGED"]
        },
        {
            "name": "Case 5: Positive Assertion on Empty Record Set (Injected Error)",
            "query": "Check status of order ORD-99999",
            "wrong_answer": "Order ORD-99999 settled successfully for INR 55,000.00 into your account.",
            "cited_ids": ["TXN-FAKE-000"],
            "raw_records": [],
            "expected_verdicts": ["FLAGGED"]
        }
    ]

    passed_count = 0
    total_count = len(test_scenarios)

    print("=" * 70)
    print("SETTLESENSE VERIFIER AGENT - DELIBERATE WRONG-ANSWER INJECTION AUDIT")
    print("Testing whether the Verifier Agent catches deliberate hand-crafted errors")
    print("=" * 70)

    for idx, sc in enumerate(test_scenarios, 1):
        print(f"\n[{idx}/{total_count}] {sc['name']}")
        print(f"  * Query: \"{sc['query']}\"")
        print(f"  * Injected Wrong Answer: \"{sc['wrong_answer']}\"")
        
        result = verify_settlement_answer(
            query=sc["query"],
            primary_answer=sc["wrong_answer"],
            cited_record_ids=sc["cited_ids"],
            retrieved_records=sc["raw_records"]
        )

        verdict = result.get("verdict")
        notes = result.get("verification_notes")
        discrepancies = result.get("discrepancies", [])
        engine_used = result.get("engine_used_verifier", "fallback")

        print(f"  * Verifier Verdict: {verdict} (Engine: {engine_used})")
        print(f"  * Verifier Notes: {notes}")
        if discrepancies:
            print(f"  * Discrepancies Caught: {discrepancies}")

        if verdict in sc["expected_verdicts"]:
            print("  + PASSED: Injected error successfully caught and audited!")
            passed_count += 1
        else:
            print("  - FAILED: Verifier erroneously passed wrong answer as VERIFIED!")

    print("\n" + "=" * 70)
    print(f"INJECTION AUDIT RESULT: {passed_count}/{total_count} Injected Errors Caught")
    print(f"Catch Rate on Injected Errors: {(passed_count / total_count) * 100:.1f}%")
    print("=" * 70)

    if passed_count == total_count:
        print("SUCCESS: Verifier Agent is proven adversarial and catches all injected errors.")
        return True
    else:
        print("WARNING: Some injected errors were not caught. Refine verifier heuristics.")
        return False

if __name__ == "__main__":
    success = run_wrong_answer_injection_test()
    sys.exit(0 if success else 1)
