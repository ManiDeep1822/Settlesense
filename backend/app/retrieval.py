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
        f"Cycle Type: {s['cycle_type']}",
        f"Failure Reason: {s.get('failure_reason') or 'None'}",
        f"Processed At: {s.get('processed_at') or 'Pending'}",
        f"Transactions In Batch: {s.get('transaction_count', 0)}"
    ]
    return " | ".join(parts)

def index_all_records():
    conn = get_db_connection()
    collection = get_or_create_collection()
    
    try:
        existing = collection.get()
        if existing and existing.get("ids"):
            collection.delete(ids=existing["ids"])
    except Exception:
        pass

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions")
    txns = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM settlements")
    settles = [dict(row) for row in cursor.fetchall()]
    conn.close()

    documents = []
    ids = []
    metadatas = []

    for t in txns:
        doc = format_transaction_document(t)
        documents.append(doc)
        ids.append(f"doc_{t['id']}")
        metadatas.append({
            "type": "transaction",
            "id": t["id"],
            "order_ref": t["order_ref"],
            "status": t["status"],
            "amount": float(t["amount"]),
            "settlement_date": t["settlement_date"] or ""
        })

    for s in settles:
        doc = format_settlement_document(s)
        documents.append(doc)
        ids.append(f"doc_{s['settlement_id']}")
        metadatas.append({
            "type": "settlement",
            "id": s["settlement_id"],
            "order_ref": s["settlement_id"],
            "status": s["status"],
            "amount": float(s["total_amount"]),
            "settlement_date": s["settlement_date"] or ""
        })

    batch_size = 100
    for i in range(0, len(documents), batch_size):
        end = min(i + batch_size, len(documents))
        collection.add(
            documents=documents[i:end],
            ids=ids[i:end],
            metadatas=metadatas[i:end]
        )

    return len(documents)

def extract_query_entities(query: str) -> Dict[str, Any]:
    orders = []
    
    for m in re.finditer(r'ORD-[\w-]+', query, re.IGNORECASE):
        orders.append(m.group(0).upper())

    for m in re.finditer(r'(?:order\s*#?\s*|#\s*)(\d+[\w-]*)', query, re.IGNORECASE):
        val = m.group(1).upper()
        if not val.startswith("ORD-"):
            orders.append(f"ORD-{val}")
        else:
            orders.append(val)

    txns = [m.group(0).upper() for m in re.finditer(r'TXN-[\w-]+', query, re.IGNORECASE)]
    settles = [m.group(0).upper() for m in re.finditer(r'SETTLE-[\w-]+', query, re.IGNORECASE)]
    utrs = [m.group(0).upper() for m in re.finditer(r'(?:[A-Z]{3,5}-\d{4,6}-[A-Z]{2}|CITIN\d+|HDFC\d+|ICIC\d+)', query, re.IGNORECASE)]

    status_keywords = []
    lowered = query.lower()
    for s in ["declined", "failed", "pending", "exception", "matched", "unmatched", "delayed", "refund", "hold", "dispute"]:
        if s in lowered:
            status_keywords.append(s)

    return {
        "orders": list(set(orders)),
        "txns": list(set(txns)),
        "settles": list(set(settles)),
        "utrs": list(set(utrs)),
        "status_keywords": list(set(status_keywords))
    }

def retrieve_hybrid_context(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    entities = extract_query_entities(query)
    conn = get_db_connection()
    cursor = conn.cursor()

    exact_matched_records = []
    seen_ids = set()

    has_specific_entity = bool(entities["orders"] or entities["txns"] or entities["settles"] or entities["utrs"])

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
