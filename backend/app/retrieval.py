import re
import json
import sqlite3
from typing import List, Dict, Any, Optional
from pathlib import Path
import chromadb
from chromadb.config import Settings

from backend.app.config import DB_PATH, CHROMA_DIR, MERCHANT_ID
from backend.app.database import get_db_connection

def get_chroma_client():
    Path(CHROMA_DIR).mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=CHROMA_DIR,
        settings=Settings(anonymized_telemetry=False)
    )

def get_or_create_collection():
    client = get_chroma_client()
    return client.get_or_create_collection(
        name="settlements_collection",
        metadata={"hnsw:space": "cosine"}
    )

def format_transaction_document(t: Dict[str, Any]) -> str:
    parts = [
        f"Transaction ID: {t['id']}",
        f"Order Ref: {t['order_ref']}",
        f"Merchant ID: {t['merchant_id']}",
        f"Amount: INR {t['amount']:.2f}",
        f"Fee: INR {t['fee']:.2f}",
        f"Tax: INR {t['tax']:.2f}",
        f"Net Payout Amount: INR {t['net_amount']:.2f}",
        f"Status: {t['status']}",
        f"Payment Method: {t['payment_method']}",
        f"Customer: {t.get('customer_email') or 'N/A'}",
        f"Created At: {t['created_at']}",
        f"Settlement Date: {t.get('settlement_date') or 'None'}",
        f"Settlement ID: {t.get('settlement_id') or 'None'}",
        f"Bank Reference UTR: {t.get('bank_ref') or 'None'}",
        f"Failure Reason: {t.get('failure_reason') or 'None'}",
        f"Dispute Status: {t.get('dispute_status') or 'None'}",
        f"Refund Amount: INR {t.get('refund_amount', 0.0):.2f}",
        f"Notes: {t.get('notes') or 'None'}"
    ]
    return " | ".join(parts)

def format_settlement_document(s: Dict[str, Any]) -> str:
    parts = [
        f"Settlement Batch ID: {s['settlement_id']}",
        f"Merchant ID: {s['merchant_id']}",
        f"Settlement Date: {s['settlement_date']}",
        f"Total Batch Amount: INR {s['total_amount']:.2f}",
        f"Total Fees Deducted: INR {s['fees_deducted']:.2f}",
        f"Total Tax Deducted: INR {s['tax_deducted']:.2f}",
        f"Net Disbursed Payout: INR {s['net_payout']:.2f}",
        f"Settlement Status: {s['status']}",
        f"Bank UTR: {s.get('bank_utr') or 'None'}",
        f"Destination Account: {s.get('account_number') or 'None'}",
        f"Cycle: {s['cycle_type']}",
        f"Transactions Count: {s.get('transaction_count', 0)}"
    ]
    return " | ".join(parts)

def extract_query_entities(query: str) -> Dict[str, List[str]]:
    patterns = {
        "orders": [
            r'\bORD-[A-Za-z0-9-]+\b',
            r'\b#(\d{4,8})\b',
            r'\border\s+(?:#\s*)?([A-Za-z0-9-]+)\b',
            r'\border\s+number\s+([A-Za-z0-9-]+)\b',
            r'\border_ref\s*[:=]?\s*([A-Za-z0-9-]+)\b'
        ],
        "txns": [
            r'\bTXN-[A-Za-z0-9-]+\b',
            r'\btransaction\s+(?:id\s*)?([A-Za-z0-9-]+)\b',
            r'\bpayment\s+(?:id\s*)?([A-Za-z0-9-]+)\b'
        ],
        "settles": [
            r'\bSETTLE-[A-Za-z0-9-]+\b',
            r'\bsettlement\s+(?:batch\s*|id\s*)?([A-Za-z0-9-]+)\b',
            r'\bbatch\s+([A-Za-z0-9-]+)\b'
        ],
        "utrs": [
            r'\b[A-Z]{3,5}-\d{4,6}-[A-Z0-9]+\b',
            r'\butr\s*[:=]?\s*([A-Za-z0-9-]+)\b',
            r'\bbank\s+ref\s*[:=]?\s*([A-Za-z0-9-]+)\b'
        ]
    }

    found = {
        "orders": [],
        "txns": [],
        "settles": [],
        "utrs": []
    }

    for p in patterns["orders"]:
        for match in re.finditer(p, query, re.IGNORECASE):
            val = match.group(1) if match.groups() else match.group(0)
            clean_val = val.strip()
            if clean_val.isdigit() and not clean_val.startswith("ORD-"):
                clean_val = f"ORD-{clean_val}"
            if clean_val.lower() not in [x.lower() for x in found["orders"]]:
                found["orders"].append(clean_val)

    for p in patterns["txns"]:
        for match in re.finditer(p, query, re.IGNORECASE):
            val = match.group(1) if match.groups() else match.group(0)
            clean_val = val.strip()
            if clean_val.upper().startswith("TXN-") and clean_val not in found["txns"]:
                found["txns"].append(clean_val)

    for p in patterns["settles"]:
        for match in re.finditer(p, query, re.IGNORECASE):
            val = match.group(1) if match.groups() else match.group(0)
            clean_val = val.strip()
            if clean_val.upper().startswith("SETTLE-") and clean_val not in found["settles"]:
                found["settles"].append(clean_val)

    for p in patterns["utrs"]:
        for match in re.finditer(p, query, re.IGNORECASE):
            val = match.group(1) if match.groups() else match.group(0)
            clean_val = val.strip()
            if not clean_val.upper().startswith("ORD-") and not clean_val.upper().startswith("TXN-") and not clean_val.upper().startswith("SETTLE-"):
                if clean_val not in found["utrs"]:
                    found["utrs"].append(clean_val)

    return found

def classify_query_intent(query: str) -> str:
    cleaned = query.strip()
    lowered = cleaned.lower()

    entities = extract_query_entities(query)
    if entities["orders"] or entities["txns"] or entities["settles"] or entities["utrs"]:
        return "ENTITY_LOOKUP"

    if re.search(r'#\d+|ord[-\s]?\d+|txn[-\s]?\d+|settle[-\s]?\d+', lowered):
        return "ENTITY_LOOKUP"

    greetings = {
        "hello", "hi", "hey", "hola", "greetings", "good morning", "good afternoon",
        "good evening", "thanks", "thank you", "help", "who are you", "what can you do",
        "what are you", "test", "testing", "hi there", "hello there", "can you help me",
        "hey there", "good day", "sup", "yo"
    }

    finance_keywords = [
        "settle", "transaction", "payout", "deposit", "fee", "tax", "refund", "hold",
        "decline", "utr", "bank", "dispute", "order", "batch", "ledger", "gross",
        "net", "amount", "chargeback", "balance", "reconciliation", "volume", "matched"
    ]
    has_finance_terms = any(fk in lowered for fk in finance_keywords)

    stripped_punct = re.sub(r'[^\w\s]', '', lowered).strip()
    if (stripped_punct in greetings or any(lowered.startswith(g) for g in ["hello", "hi ", "hey ", "thanks", "thank you"])) and not has_finance_terms:
        return "GREETING_OR_SMALL_TALK"

    aggregate_patterns = [
        r'\bhow many\b',
        r'\bhow much (?:did we|was|is|have been|were)\b',
        r'\bcount (?:of )?',
        r'\bgive me a count\b',
        r'\bsum (?:up |of )?',
        r'\btotal (?:of )?',
        r'\bwhat(?: is|\'s)? (?:the |our |my )?total\b',
        r'\bwhat(?: is|\'s)? (?:the |our |my )?pending\b',
        r'\bpending payout\b',
        r'\bsummarize\b',
        r'\baverage\b',
        r'\breconciliation rate\b',
        r'\boverall (?:count|volume|settlement|transactions)\b',
        r'\btotally\b',
        r'\bin total\b'
    ]
    
    is_aggregate = any(re.search(pat, lowered) for pat in aggregate_patterns)
    if is_aggregate and has_finance_terms:
        return "AGGREGATE_QUERY"
    if is_aggregate and not any(ook in lowered for ook in ["weather", "president", "recipe", "joke", "code"]):
        return "AGGREGATE_QUERY"

    out_of_scope_keywords = [
        "weather", "president", "recipe", "joke", "movie", "song", "sports",
        "cricket", "football", "capital of", "python code", "write a code",
        "translate", "crypto price", "bitcoin", "stock market", "who won", "news"
    ]
    if any(ook in lowered for ook in out_of_scope_keywords) and not has_finance_terms:
        return "OUT_OF_SCOPE"

    if has_finance_terms:
        return "ENTITY_LOOKUP"

    if len(cleaned.split()) <= 3 and not has_finance_terms:
        return "GREETING_OR_SMALL_TALK"

    return "OUT_OF_SCOPE"

def retrieve_hybrid_context(query: str, top_k: int = 6) -> List[Dict[str, Any]]:
    intent = classify_query_intent(query)
    if intent in ("GREETING_OR_SMALL_TALK", "OUT_OF_SCOPE"):
        return []

    entities = extract_query_entities(query)
    has_specific_entity = bool(entities["orders"] or entities["txns"] or entities["settles"] or entities["utrs"])

    exact_matched_records = []
    seen_ids = set()

    conn = get_db_connection()
    cursor = conn.cursor()

    for order_ref in entities["orders"]:
        cursor.execute("SELECT * FROM transactions WHERE UPPER(order_ref) = UPPER(?)", (order_ref,))
        for row in cursor.fetchall():
            d = dict(row)
            if d["id"] not in seen_ids:
                seen_ids.add(d["id"])
                exact_matched_records.append(d)

        if len(exact_matched_records) == 0:
            cursor.execute("SELECT * FROM transactions WHERE UPPER(order_ref) LIKE UPPER(?)", (f"%{order_ref}%",))
            for row in cursor.fetchall():
                d = dict(row)
                if d["id"] not in seen_ids:
                    seen_ids.add(d["id"])
                    exact_matched_records.append(d)

    for txn_id in entities["txns"]:
        cursor.execute("SELECT * FROM transactions WHERE UPPER(id) = UPPER(?)", (txn_id,))
        for row in cursor.fetchall():
            d = dict(row)
            if d["id"] not in seen_ids:
                seen_ids.add(d["id"])
                exact_matched_records.append(d)

    for settle_id in entities["settles"]:
        cursor.execute("SELECT * FROM settlements WHERE UPPER(settlement_id) = UPPER(?)", (settle_id,))
        for row in cursor.fetchall():
            d = dict(row)
            if d["settlement_id"] not in seen_ids:
                seen_ids.add(d["settlement_id"])
                exact_matched_records.append(d)

    for utr in entities["utrs"]:
        cursor.execute("SELECT * FROM transactions WHERE UPPER(bank_ref) = UPPER(?)", (utr,))
        for row in cursor.fetchall():
            d = dict(row)
            if d["id"] not in seen_ids:
                seen_ids.add(d["id"])
                exact_matched_records.append(d)
                
        cursor.execute("SELECT * FROM settlements WHERE UPPER(bank_utr) = UPPER(?)", (utr,))
        for row in cursor.fetchall():
            d = dict(row)
            if d["settlement_id"] not in seen_ids:
                seen_ids.add(d["settlement_id"])
                exact_matched_records.append(d)

    if has_specific_entity and len(exact_matched_records) == 0:
        conn.close()
        return []

    lowered_query = query.lower()
    if ("pending payout" in lowered_query or "pending settlement" in lowered_query or "last week" in lowered_query or "yesterday" in lowered_query or "today" in lowered_query) and len(exact_matched_records) == 0:
        cursor.execute("""
            SELECT * FROM transactions 
            WHERE status IN ('pending', 'delayed', 'exception') 
            ORDER BY created_at DESC LIMIT 10
        """)
        for row in cursor.fetchall():
            d = dict(row)
            if d["id"] not in seen_ids:
                seen_ids.add(d["id"])
                exact_matched_records.append(d)

        cursor.execute("""
            SELECT * FROM settlements 
            WHERE status IN ('settled', 'on_hold', 'partial_exception') 
            ORDER BY settlement_date DESC LIMIT 5
        """)
        for row in cursor.fetchall():
            d = dict(row)
            if d["settlement_id"] not in seen_ids:
                seen_ids.add(d["settlement_id"])
                exact_matched_records.append(d)

    if ("exception" in lowered_query or "failed" in lowered_query or "unmatched" in lowered_query) and len(exact_matched_records) == 0:
        cursor.execute("""
            SELECT * FROM transactions 
            WHERE status IN ('exception', 'unmatched', 'declined') 
            ORDER BY created_at DESC LIMIT 5
        """)
        for row in cursor.fetchall():
            d = dict(row)
            if d["id"] not in seen_ids:
                seen_ids.add(d["id"])
                exact_matched_records.append(d)

    conn.close()

    if has_specific_entity:
        return exact_matched_records

    vector_records = []
    try:
        collection = get_or_create_collection()
        results = collection.query(
            query_texts=[query],
            n_results=top_k
        )
        if results and results.get("metadatas") and len(results["metadatas"]) > 0:
            metas = results["metadatas"][0]
            conn2 = get_db_connection()
            c2 = conn2.cursor()
            for meta in metas:
                rec_id = meta.get("id")
                rec_type = meta.get("type")
                if rec_id and rec_id not in seen_ids:
                    seen_ids.add(rec_id)
                    if rec_type == "settlement":
                        c2.execute("SELECT * FROM settlements WHERE settlement_id = ?", (rec_id,))
                        row = c2.fetchone()
                        if row:
                            vector_records.append(dict(row))
                    else:
                        c2.execute("SELECT * FROM transactions WHERE id = ?", (rec_id,))
                        row = c2.fetchone()
                        if row:
                            vector_records.append(dict(row))
            conn2.close()
    except Exception:
        pass

    combined = exact_matched_records + vector_records
    return combined[:max(top_k, len(exact_matched_records))]
