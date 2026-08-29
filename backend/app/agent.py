import json
import re
import time
import os
import logging
import requests
from typing import List, Dict, Any, Optional, Tuple

from backend.app.config import GEMINI_API_KEY, GEMINI_MODEL
from backend.app.database import get_db_connection
from backend.app.retrieval import retrieve_hybrid_context, extract_query_entities, classify_query_intent
from backend.app.schemas import QueryResponse, CitedRecord
from backend.app.verifier import verify_settlement_answer

SYSTEM_PROMPT = """You are SettleSense, an AI Settlement Q&A Agent and Finance Controller.
Your mission is to answer merchant questions regarding transactions, settlements, payouts, fees, deductions, and reconciliation issues.

STRICT OPERATIONAL RULES:
1. Grounded Answering Only: Answer strictly and solely using the provided retrieved records. Never invent, hallucinate, or extrapolate transaction IDs, amounts, dates, or bank UTR numbers. Always format currency amounts using the Indian Rupee symbol '₹' (e.g. ₹1,21,561.80) rather than 'INR'.
2. Direct Citations: In your answer, explicitly cite every transaction ID (e.g. TXN-8894-4521) or settlement batch ID (e.g. SETTLE-20231024-001) that supports your findings.
3. Transparent Declines: If no relevant records exist for the query (e.g. a requested order number does not exist in the database), explicitly decline to answer with a clear explanation such as: "No transaction or settlement records found for Order #XXXXX in the settlement database." Set confidence to "UNANSWERABLE" and flag exception_detected as true.
4. Ambiguity / Conflict: If there are conflicting records or ambiguous multiple matches, state the ambiguity clearly, set confidence to "LOW", and flag exception_detected as true.
5. Response Schema: You must output ONLY a valid JSON object with the following fields:
{
  "answer": "Clear, professional, and detailed explanation for the finance controller",
  "confidence": "HIGH" | "MEDIUM" | "LOW" | "UNANSWERABLE",
  "confidence_score": 0.0 to 1.0,
  "cited_record_ids": ["TXN-xxxx", "SETTLE-xxxx"],
  "exception_detected": true | false,
  "exception_type": null | "RECORD_NOT_FOUND" | "SETTLEMENT_HOLD" | "BANK_UTR_MISMATCH" | "DISPUTE_UNDER_REVIEW" | "DATA_AMBIGUITY" | "DECLINED_TRANSACTION",
  "exception_reason": null | "Description of the exception condition"
}
"""

def handle_aggregate_query(query: str) -> Dict[str, Any]:
    lowered = query.lower()
    conn = get_db_connection()
    cursor = conn.cursor()

    if "how many transaction" in lowered or "count of transaction" in lowered or "total transactions" in lowered or "in the database" in lowered:
        cursor.execute("SELECT COUNT(*) as total_count, SUM(amount) as total_gross, SUM(fee) as total_fees, SUM(tax) as total_tax, SUM(net_amount) as total_net FROM transactions")
        row = cursor.fetchone()
        t_count = row["total_count"] or 0
        t_gross = row["total_gross"] or 0.0
        t_fees = row["total_fees"] or 0.0
        t_tax = row["total_tax"] or 0.0
        t_net = row["total_net"] or 0.0
        conn.close()

        return {
            "answer": f"There are currently {t_count} transactions recorded in the settlement database, with a total gross volume of ₹{t_gross:,.2f} (Total MDR fees deducted: ₹{t_fees:,.2f}, Total GST: ₹{t_tax:,.2f}, Net volume: ₹{t_net:,.2f}).",
            "confidence": "HIGH",
            "confidence_score": 1.0,
            "cited_record_ids": [],
            "exception_detected": False,
            "exception_type": None,
            "exception_reason": None
        }

    if "pending payout" in lowered or "pending settlement" in lowered or "total pending" in lowered:
        cursor.execute("""
            SELECT COUNT(*) as p_count, SUM(amount) as p_gross, SUM(fee) as p_fees, SUM(tax) as p_tax, SUM(net_amount) as p_net 
            FROM transactions 
            WHERE status IN ('pending', 'delayed', 'hold')
        """)
        row = cursor.fetchone()
        p_count = row["p_count"] or 0
        p_gross = row["p_gross"] or 0.0
        p_fees = row["p_fees"] or 0.0
        p_tax = row["p_tax"] or 0.0
        p_net = row["p_net"] or 0.0
        conn.close()

        return {
            "answer": f"Your total pending payout across all un-settled transactions (pending, delayed, and risk-hold) is ₹{p_net:,.2f} across {p_count} transactions (Gross pending volume: ₹{p_gross:,.2f}, estimated MDR fees: ₹{p_fees:,.2f}, GST: ₹{p_tax:,.2f}).",
            "confidence": "HIGH",
            "confidence_score": 0.99,
            "cited_record_ids": [],
            "exception_detected": False,
            "exception_type": None,
            "exception_reason": None
        }

    if "matched deposit" in lowered or "summarize deposits" in lowered or "total settled volume" in lowered or "settled payout across all batches" in lowered:
        cursor.execute("SELECT COUNT(*) as s_count, SUM(total_amount) as s_gross, SUM(fees_deducted) as s_fees, SUM(tax_deducted) as s_tax, SUM(net_payout) as s_net FROM settlements WHERE status = 'settled'")
        srow = cursor.fetchone()
        cursor.execute("SELECT COUNT(*) as t_count FROM transactions WHERE status = 'settled'")
        trow = cursor.fetchone()
        s_count = srow["s_count"] or 0
        s_gross = srow["s_gross"] or 0.0
        s_fees = srow["s_fees"] or 0.0
        s_tax = srow["s_tax"] or 0.0
        s_net = srow["s_net"] or 0.0
        t_count = trow["t_count"] or 0
        conn.close()

        return {
            "answer": f"Matched deposit summary: {s_count} settlement batches ({t_count} transactions) have successfully settled. Total gross volume: ₹{s_gross:,.2f}, MDR fees deducted: ₹{s_fees:,.2f}, GST tax: ₹{s_tax:,.2f}, and total net disbursed payout: ₹{s_net:,.2f}.",
            "confidence": "HIGH",
            "confidence_score": 0.99,
            "cited_record_ids": [],
            "exception_detected": False,
            "exception_type": None,
            "exception_reason": None
        }

    if "exception" in lowered:
        cursor.execute("SELECT COUNT(*) as exc_count FROM exceptions_log WHERE status = 'UNRESOLVED'")
        row = cursor.fetchone()
        exc_count = row["exc_count"] or 0
        conn.close()

        return {
            "answer": f"There are currently {exc_count} active, unresolved anomalies recorded in the Exceptions Ledger requiring finance ops attention.",
            "confidence": "HIGH",
            "confidence_score": 1.0,
            "cited_record_ids": [],
            "exception_detected": False,
            "exception_type": None,
            "exception_reason": None
        }

    cursor.execute("SELECT COUNT(*) as total_txns, SUM(amount) as total_vol FROM transactions")
    row = cursor.fetchone()
    conn.close()
    return {
        "answer": f"Settlement ledger aggregate summary: {row['total_txns']} transactions recorded with ₹{row['total_vol'] or 0.0:,.2f} total gross volume.",
        "confidence": "HIGH",
        "confidence_score": 0.95,
        "cited_record_ids": [],
        "exception_detected": False,
        "exception_type": None,
        "exception_reason": None
    }

def generate_offline_deterministic_answer(query: str, retrieved_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    entities = extract_query_entities(query)
    lowered = query.lower()

    if not retrieved_records:
        target_entity = ""
        if entities["orders"]:
            target_entity = f"Order {entities['orders'][0]}"
        elif entities["txns"]:
            target_entity = f"Transaction {entities['txns'][0]}"
        elif entities["settles"]:
            target_entity = f"Settlement {entities['settles'][0]}"
        elif entities["utrs"]:
            target_entity = f"Bank reference {entities['utrs'][0]}"
        else:
            target_entity = "the requested entity"

        return {
            "answer": f"I reviewed the settlement database but found no matching entry for {target_entity}. Please verify the identifier or check if the transaction is pending ingestion.",
            "confidence": "UNANSWERABLE",
            "confidence_score": 0.0,
            "cited_record_ids": [],
            "exception_detected": True,
            "exception_type": "RECORD_NOT_FOUND",
            "exception_reason": f"No transaction or settlement record matching {target_entity} exists in the ledger."
        }

    target_txn = None
    target_order_ref = entities["orders"][0] if entities["orders"] else None
    target_txn_id = entities["txns"][0] if entities["txns"] else None
    target_settle_id = entities["settles"][0] if entities["settles"] else None
    target_utr = entities["utrs"][0] if entities["utrs"] else None

    for r in retrieved_records:
        if target_order_ref and (r.get("order_ref", "").upper() == target_order_ref.upper() or target_order_ref.upper() in r.get("order_ref", "").upper()):
            target_txn = r
            break
        if target_txn_id and r.get("id", "").upper() == target_txn_id.upper():
            target_txn = r
            break
        if target_settle_id and (r.get("settlement_id", "").upper() == target_settle_id.upper() or r.get("id", "").upper() == target_settle_id.upper()):
            target_txn = r
            break
        if target_utr and (r.get("bank_ref", "").upper() == target_utr.upper() or r.get("bank_utr", "").upper() == target_utr.upper()):
            target_txn = r
            break

    if not target_txn and len(retrieved_records) == 1:
        target_txn = retrieved_records[0]

    if target_txn:
        is_settle_batch = "total_amount" in target_txn and "settlement_id" in target_txn
        
        if is_settle_batch:
            settle_id = target_txn["settlement_id"]
            tot = target_txn["total_amount"]
            net = target_txn["net_payout"]
            fees = target_txn["fees_deducted"]
            tax = target_txn["tax_deducted"]
            stat = target_txn["status"]
            sdate = target_txn["settlement_date"]
            utr = target_txn.get("bank_utr", "N/A")

            return {
                "answer": f"Settlement Batch {settle_id} was processed on {sdate} with status '{stat}'. Total batch gross: ₹{tot:,.2f}, MDR fees: ₹{fees:,.2f}, GST tax: ₹{tax:,.2f}, Net disbursed payout: ₹{net:,.2f}. Bank UTR: {utr}.",
                "confidence": "HIGH",
                "confidence_score": 0.99,
                "cited_record_ids": [settle_id],
                "exception_detected": False,
                "exception_type": None,
                "exception_reason": None
            }

        txn_id = target_txn["id"]
        order_ref = target_txn["order_ref"]
        amount = target_txn["amount"]
        fee = target_txn.get("fee", 0.0)
        tax = target_txn.get("tax", 0.0)
        net_amount = target_txn.get("net_amount", amount)
        status = target_txn["status"]
        failure_reason = target_txn.get("failure_reason")
        settlement_date = target_txn.get("settlement_date")
        bank_ref = target_txn.get("bank_ref")
        refund_amount = target_txn.get("refund_amount", 0.0)
        payment_method = target_txn.get("payment_method", "card")

        if "fee" in lowered or "tax" in lowered or "deduct" in lowered:
            return {
                "answer": f"For Order {order_ref} (Transaction {txn_id}, Gross: ₹{amount:,.2f}), the MDR fee deducted is ₹{fee:,.2f} plus 18% GST tax of ₹{tax:,.2f}, resulting in a net payout of ₹{net_amount:,.2f}.",
                "confidence": "HIGH",
                "confidence_score": 0.98,
                "cited_record_ids": [txn_id],
                "exception_detected": False,
                "exception_type": None,
                "exception_reason": None
            }

        if "utr" in lowered or "bank" in lowered:
            if bank_ref:
                return {
                    "answer": f"Order {order_ref} (Transaction {txn_id}, ₹{amount:,.2f}) was settled to your registered bank account under Bank Reference / UTR: {bank_ref} on {settlement_date}.",
                    "confidence": "HIGH",
                    "confidence_score": 0.99,
                    "cited_record_ids": [txn_id],
                    "exception_detected": False,
                    "exception_type": None,
                    "exception_reason": None
                }
            else:
                return {
                    "answer": f"Order {order_ref} (Transaction {txn_id}, ₹{amount:,.2f}) currently has no bank UTR assigned because its status is '{status}'.",
                    "confidence": "HIGH",
                    "confidence_score": 0.95,
                    "cited_record_ids": [txn_id],
                    "exception_detected": status != "settled",
                    "exception_type": "SETTLEMENT_HOLD" if status in ("delayed", "pending", "hold") else None,
                    "exception_reason": failure_reason
                }

        if status == "declined":
            reason_text = failure_reason or "Payment was declined by issuing bank or risk filter"
            return {
                "answer": f"Order {order_ref} (Transaction {txn_id}, ₹{amount:,.2f}) did not settle because it was declined before capture. Reason: {reason_text}. No settlement funds were collected or queued for disbursement.",
                "confidence": "HIGH",
                "confidence_score": 0.98,
                "cited_record_ids": [txn_id],
                "exception_detected": True,
                "exception_type": "DECLINED_TRANSACTION",
                "exception_reason": reason_text
            }

        if status == "delayed" or status == "hold":
            reason_text = failure_reason or "Transaction is pending risk verification or nodal bank settlement queue"
            sdate_text = f"Expected settlement date is deferred to {settlement_date}." if settlement_date else "Settlement date is pending clearance."
            return {
                "answer": f"Order {order_ref} (Transaction {txn_id}, ₹{amount:,.2f}) is currently delayed. Failure reason / hold: {reason_text}. {sdate_text}",
                "confidence": "HIGH",
                "confidence_score": 0.95,
                "cited_record_ids": [txn_id],
                "exception_detected": True,
                "exception_type": "SETTLEMENT_HOLD",
                "exception_reason": reason_text
            }

        if status == "settled":
            utr_text = f"under Bank UTR {bank_ref}" if bank_ref else "to nodal account"
            sdate_text = f"on {settlement_date}" if settlement_date else "in recent batch"
            return {
                "answer": f"Order {order_ref} (Transaction {txn_id}) was successfully settled {sdate_text} {utr_text}. Gross: ₹{amount:,.2f}, MDR Fee: ₹{fee:,.2f}, GST: ₹{tax:,.2f}, Net Disbursed: ₹{net_amount:,.2f}.",
                "confidence": "HIGH",
                "confidence_score": 0.99,
                "cited_record_ids": [txn_id],
                "exception_detected": False,
                "exception_type": None,
                "exception_reason": None
            }

        if status == "refunded":
            ref_text = f"₹{refund_amount:,.2f}" if refund_amount else f"₹{amount:,.2f}"
            return {
                "answer": f"Order {order_ref} (Transaction {txn_id}, ₹{amount:,.2f}) had a refund processed for {ref_text}. Net settlement adjustments have been applied to your ledger balance.",
                "confidence": "HIGH",
                "confidence_score": 0.95,
                "cited_record_ids": [txn_id],
                "exception_detected": False,
                "exception_type": None,
                "exception_reason": "Refund processed"
            }

        if status == "disputed":
            disp_reason = failure_reason or "Customer chargeback filed with card issuer"
            return {
                "answer": f"Order {order_ref} (Transaction {txn_id}, ₹{amount:,.2f}) settlement is withheld due to an active payment dispute / chargeback. Reason: {disp_reason}. Funds will remain on hold until dispute resolution.",
                "confidence": "HIGH",
                "confidence_score": 0.95,
                "cited_record_ids": [txn_id],
                "exception_detected": True,
                "exception_type": "DISPUTE_UNDER_REVIEW",
                "exception_reason": disp_reason
            }

        if status == "unmatched":
            return {
                "answer": f"Order {order_ref} (Transaction {txn_id}, ₹{amount:,.2f}) is flagged as unmatched. Nodal bank statement shows amount mismatch or missing payment capture record.",
                "confidence": "MEDIUM",
                "confidence_score": 0.85,
                "cited_record_ids": [txn_id],
                "exception_detected": True,
                "exception_type": "BANK_UTR_MISMATCH",
                "exception_reason": failure_reason or "Amount mismatch during automatic bank reconciliation"
            }

    first = retrieved_records[0]
    rec_id = first.get("id", first.get("settlement_id", "REC-001"))
    return {
        "answer": f"Based on retrieved record {rec_id}, amount is ₹{first.get('amount', first.get('total_amount', 0.0)):,.2f} with status '{first.get('status')}'.",
        "confidence": "MEDIUM",
        "confidence_score": 0.80,
        "cited_record_ids": [rec_id],
        "exception_detected": False,
        "exception_type": None,
        "exception_reason": None
    }

def call_gemini_api(prompt: str) -> Optional[Dict[str, Any]]:
    key = os.getenv("GEMINI_API_KEY", GEMINI_API_KEY)
    if not key:
        return None
        
    model_name = os.getenv("GEMINI_MODEL", GEMINI_MODEL)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.0,
            "responseMimeType": "application/json"
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=12)
        if response.status_code == 200:
            data = response.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            cleaned = raw_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            parsed = json.loads(cleaned.strip())
            if isinstance(parsed, dict) and "answer" in parsed:
                return parsed
    except Exception:
        pass
    return None

def process_settlement_query(query: str, merchant_id: Optional[str] = None) -> QueryResponse:
    start_time = time.time()
    intent = classify_query_intent(query)

    if intent == "GREETING_OR_SMALL_TALK":
        latency_ms = round((time.time() - start_time) * 1000, 2)
        return QueryResponse(
            answer="Hello! I am SettleSense, your AI Settlement Finance Controller. I can help you investigate transaction statuses, explain settlement delays or risk holds, calculate MDR fee and GST deductions, reconcile bank UTR numbers, and summarize payout batches.\n\nTo get started, please ask a question with an Order ID (e.g. #4521), Transaction ID (e.g. TXN-8894-4521), Settlement Batch ID (e.g. SETTLE-20231024-001), or an aggregate question like 'What is my total pending payout?'.",
            confidence="HIGH",
            confidence_score=1.0,
            engine_used="fallback",
            engine_used_primary="fallback",
            engine_used_verifier="fallback",
            verifier_verdict="NONE",
            verifier_notes="Greeting/conversational query. No factual ledger claims made.",
            discrepancies=[],
            cited_records=[],
            cited_record_ids=[],
            exception_detected=False,
            exception_type=None,
            exception_reason=None,
            latency_ms=latency_ms,
            intent=intent
        )

    if intent == "OUT_OF_SCOPE":
        latency_ms = round((time.time() - start_time) * 1000, 2)
        return QueryResponse(
            answer="I am specialized specifically as a Payment Settlement Q&A Agent and Finance Controller. I can only assist with payment transactions, settlement payouts, fee deductions, and ledger reconciliation. Please ask a settlement-related question.",
            confidence="UNANSWERABLE",
            confidence_score=0.0,
            engine_used="fallback",
            engine_used_primary="fallback",
            engine_used_verifier="fallback",
            verifier_verdict="NONE",
            verifier_notes="Out-of-scope inquiry. No factual ledger claims made.",
            discrepancies=[],
            cited_records=[],
            cited_record_ids=[],
            exception_detected=True,
            exception_type="OUT_OF_SCOPE",
            exception_reason="Query is outside the scope of settlement and payment ledger operations.",
            latency_ms=latency_ms,
            intent=intent
        )

    if intent == "AGGREGATE_QUERY":
        agg_result = handle_aggregate_query(query)
        latency_ms = round((time.time() - start_time) * 1000, 2)
        return QueryResponse(
            answer=agg_result["answer"],
            confidence=agg_result.get("confidence", "HIGH"),
            confidence_score=agg_result.get("confidence_score", 0.99),
            engine_used="fallback",
            engine_used_primary="fallback",
            engine_used_verifier="fallback",
            verifier_verdict="VERIFIED",
            verifier_notes="Deterministic SQL aggregation verified against live SQLite database.",
            discrepancies=[],
            cited_records=[],
            cited_record_ids=[],
            exception_detected=agg_result.get("exception_detected", False),
            exception_type=agg_result.get("exception_type"),
            exception_reason=agg_result.get("exception_reason"),
            latency_ms=latency_ms,
            intent=intent
        )

    retrieved_records = retrieve_hybrid_context(query, top_k=6)
    
    context_str = json.dumps(retrieved_records, indent=2, default=str)
    user_prompt = f"""{SYSTEM_PROMPT}

USER QUERY: "{query}"

RETRIEVED LEDGER & SETTLEMENT RECORDS:
{context_str}

Respond with valid JSON following the schema specified.
"""

    gemini_result = None
    engine_used_primary = "fallback"

    key = os.getenv("GEMINI_API_KEY", GEMINI_API_KEY)
    if key and len(key.strip()) > 10:
        gemini_result = call_gemini_api(user_prompt)
        if gemini_result:
            engine_used_primary = "gemini"

    if not gemini_result:
        gemini_result = generate_offline_deterministic_answer(query, retrieved_records)
        engine_used_primary = "fallback"

    primary_answer = gemini_result.get("answer", "No answer generated.")
    cited_ids = gemini_result.get("cited_record_ids", [])
    if isinstance(cited_ids, str):
        cited_ids = [cited_ids]

    verifier_result = verify_settlement_answer(
        query=query,
        primary_answer=primary_answer,
        cited_record_ids=cited_ids,
        retrieved_records=retrieved_records
    )

    verifier_verdict = verifier_result.get("verdict", "VERIFIED")
    verifier_notes = verifier_result.get("verification_notes")
    discrepancies = verifier_result.get("discrepancies", [])
    engine_used_verifier = verifier_result.get("engine_used_verifier", "fallback")

    exception_detected = bool(gemini_result.get("exception_detected", False))
    exception_type = gemini_result.get("exception_type")
    exception_reason = gemini_result.get("exception_reason")
    confidence_str = gemini_result.get("confidence", "MEDIUM").upper()
    confidence_val = float(gemini_result.get("confidence_score", 0.85))
    final_answer = primary_answer

    if verifier_verdict == "FLAGGED":
        exception_detected = True
        exception_type = "VERIFIER_FLAGGED"
        exception_reason = verifier_notes or "Discrepancy identified by Verifier Agent."
        confidence_str = "LOW"
        confidence_val = min(confidence_val, 0.40)
        final_answer = f"⚠ Verification Notice: The independent Verifier Agent flagged a potential ledger inconsistency ({verifier_notes}). This inquiry has been routed to the Exceptions Ledger for manual finance ops review."

    latency_ms = round((time.time() - start_time) * 1000, 2)

    if engine_used_primary == "fallback" and latency_ms > 200.0:
        logging.warning(f"Engine latency anomaly: engine is '{engine_used_primary}' but latency was {latency_ms}ms (Gemini API network call failed or rate-limited).")

    valid_cited_records = []
    record_map = {r.get("id"): r for r in retrieved_records if "id" in r}
    settle_map = {r.get("settlement_id"): r for r in retrieved_records if "settlement_id" in r}

    final_cited_ids = []
    for cid in cited_ids:
        if cid in record_map:
            t = record_map[cid]
            final_cited_ids.append(cid)
            valid_cited_records.append(CitedRecord(
                id=t["id"],
                order_ref=t.get("order_ref", ""),
                amount=float(t.get("amount", 0.0)),
                status=t.get("status", "unknown"),
                settlement_date=t.get("settlement_date"),
                bank_ref=t.get("bank_ref"),
                settlement_id=t.get("settlement_id"),
                fee=float(t.get("fee", 0.0)),
                tax=float(t.get("tax", 0.0)),
                net_amount=float(t.get("net_amount", 0.0)),
                failure_reason=t.get("failure_reason"),
                refund_amount=float(t.get("refund_amount", 0.0))
            ))
        elif cid in settle_map:
            s = settle_map[cid]
            final_cited_ids.append(cid)
            valid_cited_records.append(CitedRecord(
                id=s["settlement_id"],
                order_ref=s.get("settlement_id", ""),
                amount=float(s.get("total_amount", 0.0)),
                status=s.get("status", "unknown"),
                settlement_date=s.get("settlement_date"),
                bank_ref=s.get("bank_utr"),
                settlement_id=s.get("settlement_id"),
                fee=float(s.get("fees_deducted", 0.0)),
                tax=float(s.get("tax_deducted", 0.0)),
                net_amount=float(s.get("net_payout", 0.0)),
                failure_reason=s.get("failure_reason"),
                refund_amount=0.0
            ))

    return QueryResponse(
        answer=final_answer,
        confidence=confidence_str,
        confidence_score=confidence_val,
        engine_used=engine_used_primary,
        engine_used_primary=engine_used_primary,
        engine_used_verifier=engine_used_verifier,
        verifier_verdict=verifier_verdict,
        verifier_notes=verifier_notes,
        discrepancies=discrepancies,
        cited_records=valid_cited_records,
        cited_record_ids=final_cited_ids,
        exception_detected=exception_detected,
        exception_type=exception_type,
        exception_reason=exception_reason,
        latency_ms=latency_ms,
        intent=intent
    )
