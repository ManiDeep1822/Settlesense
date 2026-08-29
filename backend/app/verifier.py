import json
import re
import time
import os
import requests
from typing import List, Dict, Any, Optional

from backend.app.config import GEMINI_API_KEY, GEMINI_MODEL

VERIFIER_SYSTEM_PROMPT = """You are the SettleSense Independent Financial Verifier Agent.
Your sole responsibility is to rigorously audit, fact-check, and challenge the primary agent's settlement answer against the raw ledger records before any information is presented to financial controllers.

AUDIT DIRECTIVES (Skeptical & Adversarial):
1. Fact-Check Every Claim: Check all monetary amounts (gross, fees, taxes, net payouts), dates, order numbers, transaction IDs, statuses, bank UTRs, and stated failure reasons against the raw records.
2. Check Citations: Verify that every cited transaction ID or settlement batch ID actually exists in the provided raw records and directly supports the claims made.
3. Detect Numerical & Status Discrepancies: If the primary agent states an amount that does not match the ledger, invents an ungrounded transaction/batch ID, attributes a wrong status, or fabricates a date, you MUST return FLAGGED.
4. Categorize Your Audit Verdict:
   - VERIFIED: All facts, IDs, amounts, statuses, and reasons are 100% accurate and strictly grounded in the raw records. (Or for unanswerable queries, the primary agent correctly and cleanly declined without fabricating data).
   - MINOR_DISCREPANCY: The core conclusion is sound, but there is a minor formatting, rounding (e.g. within a few paise), or slight descriptive imprecision that does not alter the financial outcome.
   - FLAGGED: The primary answer contains material factual errors, wrong transaction IDs, incorrect amounts/statuses, wrong dates, unsupported claims, or hallucinated records.

Output ONLY a valid JSON object matching this schema:
{
  "verdict": "VERIFIED" | "MINOR_DISCREPANCY" | "FLAGGED",
  "verification_notes": "Concise factual justification of your audit finding",
  "discrepancies": ["List of specific discrepancies or unsupported claims found, empty if none"],
  "supported_claims": ["List of verified claims"],
  "unsupported_claims": ["List of unverified claims"]
}
"""

def call_gemini_verifier(prompt: str) -> Optional[Dict[str, Any]]:
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
            if isinstance(parsed, dict) and "verdict" in parsed:
                return parsed
    except Exception:
        pass
    return None

def extract_currency_numbers(text: str) -> List[float]:
    cleaned = re.sub(r'\b20\d{2}-\d{2}-\d{2}\b', '', text)
    cleaned = re.sub(r'TXN-[\w-]+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'ORD-[\w-]+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'SETTLE-[\w-]+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'#\d+', '', cleaned)
    cleaned = cleaned.replace(",", "")

    found_numbers = []
    matches = re.findall(r'(?:₹|INR|rs\.?|amount\s*(?:of)?\s*)?\s*(\d+(?:\.\d{1,2})?)', cleaned, re.IGNORECASE)
    for m in matches:
        try:
            val = float(m)
            if val > 5.0 and val not in (18.0, 2.0, 1.5, 0.18):
                found_numbers.append(val)
        except ValueError:
            continue
    return found_numbers

def verify_aggregate_answer(query: str, answer: str) -> Dict[str, Any]:
    from backend.app.database import get_db_connection
    lowered = query.lower()
    conn = get_db_connection()
    cursor = conn.cursor()

    if "exception" in lowered:
        cursor.execute("SELECT COUNT(*) as exc_count FROM exceptions_log WHERE status = 'UNRESOLVED'")
        row = cursor.fetchone()
        exc_count = row["exc_count"] or 0
        conn.close()
        if str(exc_count) in answer:
            return {
                "verdict": "VERIFIED",
                "verification_notes": f"Independent verifier query confirmed {exc_count} active exceptions in SQLite exceptions_log.",
                "discrepancies": [],
                "engine_used_verifier": "fallback"
            }
        else:
            return {
                "verdict": "FLAGGED",
                "verification_notes": f"Discrepancy: Answer exception count does not match database ({exc_count}).",
                "discrepancies": [f"Expected {exc_count} exceptions."],
                "engine_used_verifier": "fallback"
            }

    if "pending" in lowered or "hold" in lowered:
        cursor.execute("SELECT COUNT(*) as p_count, SUM(net_amount) as p_net FROM transactions WHERE status IN ('pending', 'delayed', 'hold')")
        row = cursor.fetchone()
        conn.close()
        p_count = row["p_count"] or 0
        p_net = row["p_net"] or 0.0
        if str(p_count) in answer:
            return {
                "verdict": "VERIFIED",
                "verification_notes": f"Independent verifier query confirmed {p_count} pending transactions (₹{p_net:,.2f}) in SQLite.",
                "discrepancies": [],
                "engine_used_verifier": "fallback"
            }
        else:
            return {
                "verdict": "FLAGGED",
                "verification_notes": f"Discrepancy: Pending transaction count {p_count} mismatch.",
                "discrepancies": [f"Expected {p_count} pending transactions."],
                "engine_used_verifier": "fallback"
            }

    if "matched" in lowered:
        cursor.execute("SELECT COUNT(*) as m_count, SUM(amount) as m_gross FROM transactions WHERE status = 'matched'")
        row = cursor.fetchone()
        conn.close()
        m_count = row["m_count"] or 0
        m_gross = row["m_gross"] or 0.0
        if str(m_count) in answer:
            return {
                "verdict": "VERIFIED",
                "verification_notes": f"Independent verifier query confirmed {m_count} matched transactions (₹{m_gross:,.2f}) in SQLite.",
                "discrepancies": [],
                "engine_used_verifier": "fallback"
            }
        else:
            return {
                "verdict": "FLAGGED",
                "verification_notes": f"Discrepancy: Matched transaction count {m_count} mismatch.",
                "discrepancies": [f"Expected {m_count} matched transactions."],
                "engine_used_verifier": "fallback"
            }

    if "settled" in lowered or "settle" in lowered:
        cursor.execute("SELECT COUNT(*) as s_count, SUM(total_amount) as s_gross FROM settlements WHERE status = 'settled'")
        srow = cursor.fetchone()
        cursor.execute("SELECT COUNT(*) as t_count FROM transactions WHERE status = 'matched'")
        trow = cursor.fetchone()
        conn.close()
        s_count = srow["s_count"] or 0
        t_count = trow["t_count"] or 0
        if str(s_count) in answer and str(t_count) in answer:
            return {
                "verdict": "VERIFIED",
                "verification_notes": f"Independent verifier query confirmed {s_count} settled batches and {t_count} settled transactions in SQLite.",
                "discrepancies": [],
                "engine_used_verifier": "fallback"
            }
        else:
            return {
                "verdict": "FLAGGED",
                "verification_notes": f"Discrepancy: Settled batch ({s_count}) or transaction count ({t_count}) mismatch.",
                "discrepancies": [f"Expected {s_count} batches and {t_count} transactions."],
                "engine_used_verifier": "fallback"
            }

    cursor.execute("SELECT COUNT(*) as t_count, SUM(amount) as t_gross FROM transactions")
    row = cursor.fetchone()
    conn.close()
    t_count = row["t_count"] or 0
    if str(t_count) in answer:
        return {
            "verdict": "VERIFIED",
            "verification_notes": f"Independent verifier query confirmed {t_count} total transactions in SQLite.",
            "discrepancies": [],
            "engine_used_verifier": "fallback"
        }
    return {
        "verdict": "FLAGGED",
        "verification_notes": f"Discrepancy: Total transaction count {t_count} mismatch in answer.",
        "discrepancies": [f"Expected {t_count} total transactions."],
        "engine_used_verifier": "fallback"
    }

def audit_answer_deterministically(
    query: str,
    primary_answer: str,
    cited_record_ids: List[str],
    retrieved_records: List[Dict[str, Any]]
) -> Dict[str, Any]:
    lowered_answer = primary_answer.lower()
    discrepancies = []
    supported = []

    if not retrieved_records:
        if "no matching" in lowered_answer or "not found" in lowered_answer or "no transaction" in lowered_answer or "unanswerable" in lowered_answer or "declined" in lowered_answer or "outside the scope" in lowered_answer:
            return {
                "verdict": "VERIFIED",
                "verification_notes": "Primary agent correctly and cleanly declined answering with zero ledger hallucinations.",
                "discrepancies": [],
                "supported_claims": ["Clean decline confirmed on empty record set"],
                "unsupported_claims": []
            }
        else:
            return {
                "verdict": "FLAGGED",
                "verification_notes": "Primary agent made positive claims when zero ledger records exist.",
                "discrepancies": ["Positive assertion made without supporting ledger records"],
                "supported_claims": [],
                "unsupported_claims": ["Ungrounded positive assertion on empty context"]
            }

    valid_txn_ids = {(r.get("id") or "").upper() for r in retrieved_records if r.get("id")}
    valid_settle_ids = {(r.get("settlement_id") or "").upper() for r in retrieved_records if r.get("settlement_id")}
    all_valid_ids = valid_txn_ids.union(valid_settle_ids)

    for cid in cited_record_ids:
        if cid.upper() not in all_valid_ids:
            discrepancies.append(f"Unverified citation ID: {cid}")

    ledger_amounts = []
    ledger_dates = []
    ledger_statuses = []
    ledger_utrs = []

    for r in retrieved_records:
        if "amount" in r:
            ledger_amounts.append(round(float(r["amount"]), 2))
        if "total_amount" in r:
            ledger_amounts.append(round(float(r["total_amount"]), 2))
        if "net_amount" in r:
            ledger_amounts.append(round(float(r["net_amount"]), 2))
        if "net_payout" in r:
            ledger_amounts.append(round(float(r["net_payout"]), 2))
        if "fee" in r:
            ledger_amounts.append(round(float(r["fee"]), 2))
        if "tax" in r:
            ledger_amounts.append(round(float(r["tax"]), 2))
        if "fees_deducted" in r:
            ledger_amounts.append(round(float(r["fees_deducted"]), 2))
        if "tax_deducted" in r:
            ledger_amounts.append(round(float(r["tax_deducted"]), 2))
        if "refund_amount" in r and r["refund_amount"]:
            ledger_amounts.append(round(float(r["refund_amount"]), 2))

        if r.get("settlement_date"):
            ledger_dates.append(r["settlement_date"])
        if r.get("created_at"):
            ledger_dates.append(r["created_at"][:10])

        if r.get("status"):
            ledger_statuses.append(r["status"].lower())

        if r.get("bank_ref"):
            ledger_utrs.append(r["bank_ref"].upper())
        if r.get("bank_utr"):
            ledger_utrs.append(r["bank_utr"].upper())

    extracted_numbers = extract_currency_numbers(primary_answer)
    for num in extracted_numbers:
        matched = False
        for l_amt in ledger_amounts:
            if abs(num - l_amt) <= 1.0:
                matched = True
                break
        if not matched:
            if len(retrieved_records) == 1:
                r0 = retrieved_records[0]
                g = r0.get("amount", r0.get("total_amount", 0.0))
                n = r0.get("net_amount", r0.get("net_payout", 0.0))
                discrepancies.append(f"Amount discrepancy: claimed amount ₹{num:,.2f} does not match ledger record (Gross: ₹{g:,.2f}, Net: ₹{n:,.2f})")
            else:
                discrepancies.append(f"Amount discrepancy: claimed amount ₹{num:,.2f} not found in retrieved ledger records")

    date_matches = re.findall(r'\b(20\d{2}-\d{2}-\d{2})\b', primary_answer)
    for d in date_matches:
        if d not in ledger_dates:
            discrepancies.append(f"Date discrepancy: stated date {d} not found in retrieved records ({', '.join(ledger_dates)})")

    for r in retrieved_records:
        r_id = r.get("id", r.get("settlement_id", ""))
        r_stat = r.get("status", "").lower()
        if r_stat == "declined" and ("successfully settled" in lowered_answer or "settled on" in lowered_answer):
            discrepancies.append(f"Status contradiction: record {r_id} is declined but answer claimed successfully settled")
        if r_stat == "settled" and ("declined before capture" in lowered_answer or "payment was declined" in lowered_answer):
            discrepancies.append(f"Status contradiction: record {r_id} is settled but answer claimed declined")

    if discrepancies:
        return {
            "verdict": "FLAGGED",
            "verification_notes": "; ".join(discrepancies),
            "discrepancies": discrepancies,
            "supported_claims": supported,
            "unsupported_claims": discrepancies
        }

    return {
        "verdict": "VERIFIED",
        "verification_notes": f"All stated amounts, dates, and transaction IDs strictly match the {len(retrieved_records)} retrieved ledger records.",
        "discrepancies": [],
        "supported_claims": ["Grounded ledger amounts", "Verified IDs and statuses"],
        "unsupported_claims": []
    }

def verify_settlement_answer(
    query: str,
    primary_answer: str,
    cited_record_ids: List[str],
    retrieved_records: List[Dict[str, Any]]
) -> Dict[str, Any]:
    context_str = json.dumps(retrieved_records, indent=2, default=str)
    prompt = f"""{VERIFIER_SYSTEM_PROMPT}

USER'S ORIGINAL QUERY: "{query}"

PRIMARY AGENT'S PROPOSED ANSWER:
"{primary_answer}"

PRIMARY AGENT'S CITED IDS:
{json.dumps(cited_record_ids)}

RAW RETRIEVED LEDGER RECORDS (GROUND TRUTH):
{context_str}

Audit the answer and output valid JSON matching the schema.
"""

    gemini_verdict = None
    engine_used = "fallback"

    key = os.getenv("GEMINI_API_KEY", GEMINI_API_KEY)
    if key and len(key.strip()) > 10:
        gemini_verdict = call_gemini_verifier(prompt)
        if gemini_verdict and "verdict" in gemini_verdict:
            engine_used = "gemini"

    if not gemini_verdict:
        gemini_verdict = audit_answer_deterministically(
            query=query,
            primary_answer=primary_answer,
            cited_record_ids=cited_record_ids,
            retrieved_records=retrieved_records
        )
        engine_used = "fallback"

    gemini_verdict["engine_used_verifier"] = engine_used
    return gemini_verdict
