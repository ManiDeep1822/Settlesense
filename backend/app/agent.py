import json
import re
import time
import os
import requests
from typing import List, Dict, Any, Optional, Tuple

from backend.app.config import GEMINI_API_KEY, GEMINI_MODEL
from backend.app.retrieval import retrieve_hybrid_context, extract_query_entities
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
                "confidence_score": 0.99,
                "cited_record_ids": [txn_id],
                "exception_detected": False,
                "exception_type": None,
                "exception_reason": None
            }

        if "payment method" in lowered or "method" in lowered:
            return {
                "answer": f"Order {order_ref} (Transaction {txn_id}) was authorized via {payment_method}. Gross amount: ₹{amount:,.2f}, Status: {status}.",
                "confidence": "HIGH",
                "confidence_score": 0.99,
                "cited_record_ids": [txn_id],
                "exception_detected": False,
                "exception_type": None,
                "exception_reason": None
            }

        if "date" in lowered and settlement_date:
            return {
                "answer": f"The settlement date for Order {order_ref} (Transaction {txn_id}) was {settlement_date}. Gross amount: ₹{amount:,.2f}, Net payout: ₹{net_amount:,.2f}.",
                "confidence": "HIGH",
                "confidence_score": 0.99,
                "cited_record_ids": [txn_id],
                "exception_detected": False,
                "exception_type": None,
                "exception_reason": None
            }

        if status == "declined":
            reason_text = failure_reason or "Payment declined by issuing bank or processor"
            return {
                "answer": f"Order {order_ref} (Transaction {txn_id}, ₹{amount:,.2f}) did not settle because it was declined before capture. Reason: {reason_text}. No settlement funds were collected or queued for disbursement.",
                "confidence": "HIGH",
                "confidence_score": 0.98,
                "cited_record_ids": [txn_id],
                "exception_detected": True,
                "exception_type": "DECLINED_TRANSACTION",
                "exception_reason": reason_text
            }
        elif status == "delayed":
            reason_text = failure_reason or "Settlement deferred due to risk or banking rail hold"
            return {
                "answer": f"Order {order_ref} (Transaction {txn_id}, ₹{amount:,.2f}) is currently delayed. Failure reason / hold: {reason_text}. Expected settlement date is deferred to {settlement_date or 'under review'}.",
                "confidence": "HIGH",
                "confidence_score": 0.95,
                "cited_record_ids": [txn_id],
                "exception_detected": True,
                "exception_type": "SETTLEMENT_HOLD",
                "exception_reason": reason_text
            }
        elif status == "exception":
            reason_text = failure_reason or "Discrepancy detected in bank UTR or settlement batch calculation"
            extra = f" A partial refund of ₹{refund_amount:,.2f} was recorded." if refund_amount > 0 else ""
            return {
                "answer": f"Order {order_ref} (Transaction {txn_id}, ₹{amount:,.2f}) is flagged with an exception status.{extra} Root cause: {reason_text}. The transaction is currently held in the exception queue for manual finance ops review.",
                "confidence": "HIGH",
                "confidence_score": 0.94,
                "cited_record_ids": [txn_id],
                "exception_detected": True,
                "exception_type": "BANK_UTR_MISMATCH" if "UTR" in reason_text else "DATA_AMBIGUITY",
                "exception_reason": reason_text
            }
        elif status == "pending":
            return {
                "answer": f"Order {order_ref} (Transaction {txn_id}, ₹{amount:,.2f}) is pending normal batch settlement. Expected settlement date is {settlement_date or 'T+1 morning cutoff'}. Net payout after fees of ₹{fee:,.2f} will be ₹{net_amount:,.2f}.",
                "confidence": "HIGH",
                "confidence_score": 0.96,
                "cited_record_ids": [txn_id],
                "exception_detected": False,
                "exception_type": None,
                "exception_reason": None
            }
        elif status == "matched":
            return {
                "answer": f"Order {order_ref} (Transaction {txn_id}) of ₹{amount:,.2f} was successfully settled on {settlement_date or 'scheduled cycle'} under settlement batch {target_txn.get('settlement_id') or 'N/A'}. Bank reference UTR: {bank_ref or 'Confirmed'}. Net amount credited: ₹{net_amount:,.2f}.",
                "confidence": "HIGH",
                "confidence_score": 0.99,
                "cited_record_ids": [txn_id],
                "exception_detected": False,
                "exception_type": None,
                "exception_reason": None
            }
        elif status == "unmatched":
            reason_text = failure_reason or "Nodal bank credit confirmation missing in statement feed"
            return {
                "answer": f"Order {order_ref} (Transaction {txn_id}, ₹{amount:,.2f}) is unmatched in bank reconciliation. Reason: {reason_text}. Bank reference {bank_ref or 'N/A'} was not confirmed in MT940 statement.",
                "confidence": "HIGH",
                "confidence_score": 0.92,
                "cited_record_ids": [txn_id],
                "exception_detected": True,
                "exception_type": "BANK_UTR_MISMATCH",
                "exception_reason": reason_text
            }

    if "pending payout" in lowered or "pending" in lowered or "last week" in lowered:
        pending_txns = [r for r in retrieved_records if r.get("status") in ["pending", "delayed"]]
        if pending_txns:
            total_pending = sum(r.get("net_amount", r.get("amount", 0.0)) for r in pending_txns)
            cited_ids = [r["id"] for r in pending_txns[:5] if "id" in r]
            return {
                "answer": f"You have {len(pending_txns)} pending or delayed transactions in the current pipeline totaling approximately ₹{total_pending:,.2f} in net payouts scheduled across upcoming settlement windows.",
                "confidence": "HIGH",
                "confidence_score": 0.95,
                "cited_record_ids": cited_ids,
                "exception_detected": False,
                "exception_type": None,
                "exception_reason": None
            }

    if "matched" in lowered or "summarize" in lowered or "today" in lowered:
        matched_txns = [r for r in retrieved_records if r.get("status") == "matched"]
        if matched_txns:
            total_matched = sum(r.get("net_amount", r.get("amount", 0.0)) for r in matched_txns)
            cited_ids = [r["id"] for r in matched_txns[:5] if "id" in r]
            return {
                "answer": f"Found {len(matched_txns)} matched and reconciled settlement records totaling ₹{total_matched:,.2f} net payout credited to your nodal account.",
                "confidence": "HIGH",
                "confidence_score": 0.95,
                "cited_record_ids": cited_ids,
                "exception_detected": False,
                "exception_type": None,
                "exception_reason": None
            }

    first = retrieved_records[0]
    rec_id = first.get("id") or first.get("settlement_id", "RECORD-1")
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
        response = requests.post(url, headers=headers, json=payload, timeout=15)
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
        latency_ms=latency_ms
    )
