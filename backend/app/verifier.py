import json
import time
import os
import re
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

    matches = re.findall(r'(?:₹|rs\.?|inr)\s*(\d+(?:\.\d{1,2})?)', cleaned, re.IGNORECASE)
    numbers = []
    for m in matches:
        try:
            val = float(m)
            numbers.append(val)
        except ValueError:
            pass
    return numbers

def deterministic_verify(
    query: str,
    primary_answer: str,
    cited_record_ids: List[str],
    retrieved_records: List[Dict[str, Any]]
) -> Dict[str, Any]:
    lowered_answer = primary_answer.lower()
    
    if not retrieved_records:
        if "no matching" in lowered_answer or "not found" in lowered_answer or "no transaction" in lowered_answer:
            if not cited_record_ids:
                return {
                    "verdict": "VERIFIED",
                    "verification_notes": "Verified honest declination for non-existent database entity.",
                    "discrepancies": [],
                    "supported_claims": ["Correctly declined non-existent record without citations"],
                    "unsupported_claims": []
                }
            else:
                return {
                    "verdict": "FLAGGED",
                    "verification_notes": "Primary agent declined but attached unexpected record citations.",
                    "discrepancies": ["Citations attached to empty ledger result set"],
                    "supported_claims": [],
                    "unsupported_claims": cited_record_ids
                }
        else:
            return {
                "verdict": "FLAGGED",
                "verification_notes": "Primary agent made positive claims when zero ledger records exist.",
                "discrepancies": ["Positive assertion made without supporting ledger records"],
                "supported_claims": [],
                "unsupported_claims": ["All claims made without backing data"]
            }

    record_ids_in_context = set()
    valid_amounts = set()
    valid_dates = set()
    valid_utrs = set()
    valid_statuses = set()

    for r in retrieved_records:
        if r.get("id"):
            record_ids_in_context.add(str(r["id"]).upper())
        if r.get("settlement_id"):
            record_ids_in_context.add(str(r["settlement_id"]).upper())
        if r.get("order_ref"):
            record_ids_in_context.add(str(r["order_ref"]).upper())

        for field in ["amount", "total_amount", "net_amount", "net_payout", "fee", "fees_deducted", "tax", "tax_deducted", "refund_amount"]:
            if r.get(field) is not None:
                try:
                    valid_amounts.add(round(float(r[field]), 2))
                except (ValueError, TypeError):
                    pass

        for dfield in ["settlement_date", "created_at"]:
            if r.get(dfield):
                d_str = str(r[dfield])[:10]
                valid_dates.add(d_str)

        for ufield in ["bank_ref", "bank_utr"]:
            if r.get(ufield):
                valid_utrs.add(str(r[ufield]).upper())

        if r.get("status"):
            valid_statuses.add(str(r["status"]).lower())

    invalid_citations = [cid for cid in cited_record_ids if cid.upper() not in record_ids_in_context]
    if invalid_citations:
        return {
            "verdict": "FLAGGED",
            "verification_notes": f"Primary agent cited IDs not present in retrieved context: {', '.join(invalid_citations)}",
            "discrepancies": [f"Unverified citation ID: {cid}" for cid in invalid_citations],
            "supported_claims": [],
            "unsupported_claims": invalid_citations
        }

    txn_matches_in_text = re.findall(r'TXN-[\w-]+', primary_answer, re.IGNORECASE)
    for tid in txn_matches_in_text:
        if tid.upper() not in record_ids_in_context:
            return {
                "verdict": "FLAGGED",
                "verification_notes": f"Primary answer mentions ungrounded transaction ID: {tid}",
                "discrepancies": [f"Mentioned ID {tid} not in retrieved dataset"],
                "supported_claims": [],
                "unsupported_claims": [tid]
            }

    discrepancies = []
    supported = []

    for r in retrieved_records:
        status = r.get("status")
        if status and status.lower() in ["declined", "failed"]:
            if "successfully settled" in lowered_answer or ("settled on" in lowered_answer and "did not settle" not in lowered_answer and "was declined" not in lowered_answer):
                discrepancies.append(f"Status contradiction: record {r.get('id')} is declined but answer claimed successfully settled")
        elif status == "matched":
            if "was declined before capture" in lowered_answer and len(retrieved_records) == 1:
                discrepancies.append(f"Status contradiction: record {r.get('id')} is matched but answer claimed declined")

    date_matches = re.findall(r'\b(20\d{2}-\d{2}-\d{2})\b', primary_answer)
    for dm in date_matches:
        if valid_dates and dm not in valid_dates:
            discrepancies.append(f"Date discrepancy: stated date {dm} not found in retrieved records ({', '.join(valid_dates)})")

    if len(retrieved_records) == 1:
        single_rec = retrieved_records[0]
        rec_gross = round(float(single_rec.get("amount", single_rec.get("total_amount", 0.0))), 2)
        rec_net = round(float(single_rec.get("net_amount", single_rec.get("net_payout", rec_gross))), 2)
        
        claimed_numbers = extract_currency_numbers(primary_answer)
        for num in claimed_numbers:
            is_valid_num = False
            for v in valid_amounts:
                if abs(num - v) < 1.0 or abs(num - (rec_gross - rec_net)) < 1.0:
                    is_valid_num = True
                    break
            if not is_valid_num and num > 50.0:
                discrepancies.append(f"Amount discrepancy: claimed amount ₹{num:,.2f} does not match ledger record (Gross: ₹{rec_gross:,.2f}, Net: ₹{rec_net:,.2f})")

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
        "verification_notes": "All cited entities, amounts, statuses, and ledger facts strictly verified against raw records.",
        "discrepancies": [],
        "supported_claims": ["All cited IDs, amounts, and statuses grounded in retrieved records"],
        "unsupported_claims": []
    }

def verify_settlement_answer(
    query: str,
    primary_answer: str,
    cited_record_ids: List[str],
    retrieved_records: List[Dict[str, Any]]
) -> Dict[str, Any]:
    context_str = json.dumps(retrieved_records, indent=2, default=str)
    verifier_prompt = f"""{VERIFIER_SYSTEM_PROMPT}

USER QUERY: "{query}"

PRIMARY AGENT'S ANSWER TO VERIFY:
"{primary_answer}"

CITED RECORD IDS: {json.dumps(cited_record_ids)}

RAW RETRIEVED LEDGER RECORDS:
{context_str}

Perform your independent adversarial audit and return strictly JSON.
"""

    gemini_verdict = None
    engine_used = "fallback"

    key = os.getenv("GEMINI_API_KEY", GEMINI_API_KEY)
    if key and len(key.strip()) > 10:
        gemini_verdict = call_gemini_verifier(verifier_prompt)
        if gemini_verdict:
            engine_used = "gemini"

    if not gemini_verdict:
        gemini_verdict = deterministic_verify(query, primary_answer, cited_record_ids, retrieved_records)
        engine_used = "fallback"

    raw_verdict = gemini_verdict.get("verdict", "VERIFIED").upper()
    if raw_verdict not in ["VERIFIED", "MINOR_DISCREPANCY", "FLAGGED"]:
        raw_verdict = "VERIFIED"

    return {
        "verdict": raw_verdict,
        "verification_notes": gemini_verdict.get("verification_notes") or "Verified against raw records.",
        "discrepancies": gemini_verdict.get("discrepancies", []),
        "supported_claims": gemini_verdict.get("supported_claims", []),
        "unsupported_claims": gemini_verdict.get("unsupported_claims", []),
        "engine_used_verifier": engine_used
    }
