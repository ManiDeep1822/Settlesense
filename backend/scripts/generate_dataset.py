import sys
import os
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.app.config import DB_PATH, MERCHANT_ID
from backend.app.database import init_db, db_session

def round_curr(val: float) -> float:
    return round(val, 2)

def generate_synthetic_data(seed: int = 42):
    random.seed(seed)
    init_db()

    specific_records = [
        {
            "id": "TXN-8894-4521",
            "order_ref": "ORD-4521",
            "merchant_id": MERCHANT_ID,
            "amount": 1450.00,
            "fee": 29.00,
            "tax": 5.22,
            "net_amount": 1415.78,
            "currency": "INR",
            "status": "declined",
            "payment_method": "credit_card",
            "customer_email": "rahul.sharma@example.com",
            "created_at": "2023-10-24 10:14:22",
            "settlement_date": None,
            "settlement_id": None,
            "bank_ref": None,
            "failure_reason": "Billing zip code mismatch flagged by processor; declined by issuing bank",
            "dispute_status": None,
            "refund_amount": 0.0,
            "notes": "Transaction held for manual review then rejected by issuer"
        },
        {
            "id": "TXN-849201A",
            "order_ref": "ORD-992-B",
            "merchant_id": MERCHANT_ID,
            "amount": 124500.00,
            "fee": 2490.00,
            "tax": 448.20,
            "net_amount": 121561.80,
            "currency": "INR",
            "status": "matched",
            "payment_method": "netbanking",
            "customer_email": "enterprise.buyer@acme.in",
            "created_at": "2023-10-23 09:30:00",
            "settlement_date": "2023-10-24",
            "settlement_id": "SETTLE-20231024-001",
            "bank_ref": "CHASE-88392-XX",
            "failure_reason": None,
            "dispute_status": None,
            "refund_amount": 0.0,
            "notes": "Full settlement on T+1 cycle"
        },
        {
            "id": "TXN-849202B",
            "order_ref": "ORD-104-C",
            "merchant_id": MERCHANT_ID,
            "amount": 8430.50,
            "fee": 168.61,
            "tax": 30.35,
            "net_amount": 8231.54,
            "currency": "INR",
            "status": "exception",
            "payment_method": "upi",
            "customer_email": "priya.n@techcorp.io",
            "created_at": "2023-10-23 15:45:10",
            "settlement_date": "2023-10-24",
            "settlement_id": "SETTLE-20231024-002",
            "bank_ref": "BOA-44910-YY",
            "failure_reason": "Bank UTR amount mismatch due to concurrent partial refund of INR 2000",
            "dispute_status": "under_review",
            "refund_amount": 2000.0,
            "notes": "Partial refund processed before batch settlement closure"
        },
        {
            "id": "TXN-849203C",
            "order_ref": "ORD-553-A",
            "merchant_id": MERCHANT_ID,
            "amount": 45000.00,
            "fee": 900.00,
            "tax": 162.00,
            "net_amount": 43938.00,
            "currency": "INR",
            "status": "pending",
            "payment_method": "credit_card",
            "customer_email": "ananya.patel@global.org",
            "created_at": "2023-10-24 18:20:00",
            "settlement_date": "2023-10-25",
            "settlement_id": None,
            "bank_ref": None,
            "failure_reason": "Awaiting scheduled settlement window T+1",
            "dispute_status": None,
            "refund_amount": 0.0,
            "notes": "Scheduled for payout in next morning batch"
        },
        {
            "id": "TXN-849204D",
            "order_ref": "ORD-811-F",
            "merchant_id": MERCHANT_ID,
            "amount": 9200.75,
            "fee": 184.02,
            "tax": 33.12,
            "net_amount": 8983.61,
            "currency": "INR",
            "status": "unmatched",
            "payment_method": "debit_card",
            "customer_email": "vikram.singh@venture.co",
            "created_at": "2023-10-22 11:10:00",
            "settlement_date": "2023-10-23",
            "settlement_id": "SETTLE-20231023-009",
            "bank_ref": "CITI-11234-ZZ",
            "failure_reason": "Nodal bank account credit confirmation missing in bank feed",
            "dispute_status": None,
            "refund_amount": 0.0,
            "notes": "Awaiting nodal bank MT940 statement sync"
        },
        {
            "id": "TXN-849205E",
            "order_ref": "ORD-229-K",
            "merchant_id": MERCHANT_ID,
            "amount": 210000.00,
            "fee": 4200.00,
            "tax": 756.00,
            "net_amount": 205044.00,
            "currency": "INR",
            "status": "matched",
            "payment_method": "netbanking",
            "customer_email": "payments@bigcorp.in",
            "created_at": "2023-10-22 14:05:00",
            "settlement_date": "2023-10-23",
            "settlement_id": "SETTLE-20231023-001",
            "bank_ref": "WF-99821-AA",
            "failure_reason": None,
            "dispute_status": None,
            "refund_amount": 0.0,
            "notes": "Matched and credited successfully"
        },
        {
            "id": "TXN-7701-9921",
            "order_ref": "ORD-9921",
            "merchant_id": MERCHANT_ID,
            "amount": 18500.00,
            "fee": 370.00,
            "tax": 66.60,
            "net_amount": 18063.40,
            "currency": "INR",
            "status": "delayed",
            "payment_method": "credit_card",
            "customer_email": "sanjay.m@invest.in",
            "created_at": "2023-10-20 16:30:00",
            "settlement_date": "2023-10-26",
            "settlement_id": "SETTLE-20231026-HOLD",
            "bank_ref": "HDFC-77192-HLD",
            "failure_reason": "Risk hold triggered: High velocity ticket size exceeding standard merchant threshold",
            "dispute_status": None,
            "refund_amount": 0.0,
            "notes": "Merchant ops requested to provide invoice copy before release"
        }
    ]

    settlements_dict = {}
    
    settlements_dict["SETTLE-20231024-001"] = {
        "settlement_id": "SETTLE-20231024-001",
        "merchant_id": MERCHANT_ID,
        "settlement_date": "2023-10-24",
        "total_amount": 124500.00,
        "fees_deducted": 2490.00,
        "tax_deducted": 448.20,
        "net_payout": 121561.80,
        "status": "settled",
        "bank_utr": "CHASE-88392-XX",
        "account_number": "XXXXXX4920",
        "cycle_type": "T+1",
        "failure_reason": None,
        "processed_at": "2023-10-24 06:00:00",
        "transaction_count": 1
    }

    settlements_dict["SETTLE-20231024-002"] = {
        "settlement_id": "SETTLE-20231024-002",
        "merchant_id": MERCHANT_ID,
        "settlement_date": "2023-10-24",
        "total_amount": 8430.50,
        "fees_deducted": 168.61,
        "tax_deducted": 30.35,
        "net_payout": 6231.54,
        "status": "partial_exception",
        "bank_utr": "BOA-44910-YY",
        "account_number": "XXXXXX4920",
        "cycle_type": "T+1",
        "failure_reason": "Net payout adjusted for concurrent refund",
        "processed_at": "2023-10-24 06:15:00",
        "transaction_count": 1
    }

    settlements_dict["SETTLE-20231023-001"] = {
        "settlement_id": "SETTLE-20231023-001",
        "merchant_id": MERCHANT_ID,
        "settlement_date": "2023-10-23",
        "total_amount": 210000.00,
        "fees_deducted": 4200.00,
        "tax_deducted": 756.00,
        "net_payout": 205044.00,
        "status": "settled",
        "bank_utr": "WF-99821-AA",
        "account_number": "XXXXXX4920",
        "cycle_type": "T+1",
        "failure_reason": None,
        "processed_at": "2023-10-23 06:00:00",
        "transaction_count": 1
    }

    settlements_dict["SETTLE-20231023-009"] = {
        "settlement_id": "SETTLE-20231023-009",
        "merchant_id": MERCHANT_ID,
        "settlement_date": "2023-10-23",
        "total_amount": 9200.75,
        "fees_deducted": 184.02,
        "tax_deducted": 33.12,
        "net_payout": 8983.61,
        "status": "unmatched",
        "bank_utr": "CITI-11234-ZZ",
        "account_number": "XXXXXX4920",
        "cycle_type": "T+1",
        "failure_reason": "Statement missing credit confirmation",
        "processed_at": "2023-10-23 06:30:00",
        "transaction_count": 1
    }

    settlements_dict["SETTLE-20231026-HOLD"] = {
        "settlement_id": "SETTLE-20231026-HOLD",
        "merchant_id": MERCHANT_ID,
        "settlement_date": "2023-10-26",
        "total_amount": 18500.00,
        "fees_deducted": 370.00,
        "tax_deducted": 66.60,
        "net_payout": 18063.40,
        "status": "on_hold",
        "bank_utr": "HDFC-77192-HLD",
        "account_number": "XXXXXX4920",
        "cycle_type": "T+2",
        "failure_reason": "Risk hold pending ticket size review",
        "processed_at": None,
        "transaction_count": 1
    }

    base_date = datetime(2023, 10, 1)
    payment_methods = ["credit_card", "debit_card", "upi", "netbanking"]
    bank_prefixes = ["HDFC", "ICICI", "SBIN", "UTIB", "KKBK", "CITI", "CHASE"]
    statuses = ["matched", "matched", "matched", "matched", "pending", "exception", "unmatched", "declined", "delayed"]
    domains = ["gmail.com", "outlook.com", "yahoo.co.in", "company.in", "corp.org"]

    transactions_list = list(specific_records)
    current_settlement_batches = {}

    for i in range(100, 750):
        day_offset = random.randint(0, 30)
        txn_time = base_date + timedelta(days=day_offset, hours=random.randint(8, 22), minutes=random.randint(0, 59))
        created_at_str = txn_time.strftime("%Y-%m-%d %H:%M:%S")
        
        status = random.choice(statuses)
        amount = round_curr(random.choice([
            random.uniform(250.0, 2500.0),
            random.uniform(3000.0, 15000.0),
            random.uniform(20000.0, 150000.0)
        ]))

        fee_rate = 0.02 if random.random() > 0.3 else 0.015
        fee = round_curr(amount * fee_rate)
        tax = round_curr(fee * 0.18)
        net_amount = round_curr(amount - fee - tax)
        
        order_num = 10000 + i
        order_ref = f"ORD-{order_num}"
        txn_id = f"TXN-{random.randint(1000, 9999)}-{order_num}"
        
        email_prefix = f"user.{i}.{random.choice(['kumar', 'sharma', 'patel', 'singh', 'gupta', 'reddy', 'nair'])}"
        customer_email = f"{email_prefix}@{random.choice(domains)}"
        payment_method = random.choice(payment_methods)

        settlement_id = None
        settlement_date_str = None
        bank_ref = None
        failure_reason = None
        dispute_status = None
        refund_amount = 0.0
        notes = None

        if status == "matched":
            settle_date = txn_time + timedelta(days=1)
            settlement_date_str = settle_date.strftime("%Y-%m-%d")
            settle_key = f"SETTLE-{settle_date.strftime('%Y%m%d')}-BATCH{random.randint(10, 99)}"
            settlement_id = settle_key
            bank_ref = f"{random.choice(bank_prefixes)}-{random.randint(10000, 99999)}-{random.choice(['XX', 'YY', 'ZZ', 'AA'])}"
            notes = "Standard automated reconciliation"

            if settle_key not in current_settlement_batches:
                current_settlement_batches[settle_key] = {
                    "settlement_id": settle_key,
                    "merchant_id": MERCHANT_ID,
                    "settlement_date": settlement_date_str,
                    "total_amount": 0.0,
                    "fees_deducted": 0.0,
                    "tax_deducted": 0.0,
                    "net_payout": 0.0,
                    "status": "settled",
                    "bank_utr": bank_ref,
                    "account_number": "XXXXXX4920",
                    "cycle_type": "T+1",
                    "failure_reason": None,
                    "processed_at": f"{settlement_date_str} 06:00:00",
                    "transaction_count": 0
                }
            current_settlement_batches[settle_key]["total_amount"] += amount
            current_settlement_batches[settle_key]["fees_deducted"] += fee
            current_settlement_batches[settle_key]["tax_deducted"] += tax
            current_settlement_batches[settle_key]["net_payout"] += net_amount
            current_settlement_batches[settle_key]["transaction_count"] += 1

        elif status == "pending":
            settle_date = txn_time + timedelta(days=1)
            settlement_date_str = settle_date.strftime("%Y-%m-%d")
            failure_reason = "Awaiting settlement window cutoff"
            notes = "In settlement pipeline for next cycle"

        elif status == "declined":
            reasons = [
                "Card issuing bank network timeout during 3DS challenge",
                "Insufficient account balance at customer issuing bank",
                "Card international transactions not enabled by cardholder",
                "Risk engine flagged suspicious IP velocity"
            ]
            failure_reason = random.choice(reasons)
            notes = "Payment declined before capture"

        elif status == "exception":
            reasons = [
                "Mismatched bank UTR confirmation amount with nodal bank credit",
                "Partial refund executed after settlement batch calculation",
                "Duplicate bank reference received from secondary acquiring switch",
                "Merchant GSTIN verification discrepancy"
            ]
            failure_reason = random.choice(reasons)
            if "refund" in failure_reason:
                refund_amount = round_curr(amount * random.choice([0.25, 0.5, 0.75]))
            notes = "Flagged for manual finance ops review"

        elif status == "delayed":
            settle_date = txn_time + timedelta(days=4)
            settlement_date_str = settle_date.strftime("%Y-%m-%d")
            failure_reason = random.choice([
                "Scheduled bank maintenance window at partner nodal bank",
                "Statutory holiday delay in RTGS/NEFT settlement rails",
                "High value volume threshold review by risk compliance"
            ])
            notes = "Expected settlement deferred"

        elif status == "unmatched":
            failure_reason = "No matching bank credit record found in daily MT940 statement"
            notes = "Unreconciled bank ledger discrepancy"

        transactions_list.append({
            "id": txn_id,
            "order_ref": order_ref,
            "merchant_id": MERCHANT_ID,
            "amount": amount,
            "fee": fee,
            "tax": tax,
            "net_amount": net_amount,
            "currency": "INR",
            "status": status,
            "payment_method": payment_method,
            "customer_email": customer_email,
            "created_at": created_at_str,
            "settlement_date": settlement_date_str,
            "settlement_id": settlement_id,
            "bank_ref": bank_ref,
            "failure_reason": failure_reason,
            "dispute_status": dispute_status,
            "refund_amount": refund_amount,
            "notes": notes
        })

    for key, batch in current_settlement_batches.items():
        batch["total_amount"] = round_curr(batch["total_amount"])
        batch["fees_deducted"] = round_curr(batch["fees_deducted"])
        batch["tax_deducted"] = round_curr(batch["tax_deducted"])
        batch["net_payout"] = round_curr(batch["net_payout"])
        settlements_dict[key] = batch

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transactions")
        cursor.execute("DELETE FROM settlements")
        cursor.execute("DELETE FROM exceptions_log")
        cursor.execute("DELETE FROM accuracy_runs")
        cursor.execute("DELETE FROM query_logs")

        for s in settlements_dict.values():
            cursor.execute("""
                INSERT INTO settlements (
                    settlement_id, merchant_id, settlement_date, total_amount,
                    fees_deducted, tax_deducted, net_payout, status, bank_utr,
                    account_number, cycle_type, failure_reason, processed_at, transaction_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                s["settlement_id"], s["merchant_id"], s["settlement_date"], s["total_amount"],
                s["fees_deducted"], s["tax_deducted"], s["net_payout"], s["status"], s["bank_utr"],
                s["account_number"], s["cycle_type"], s["failure_reason"], s["processed_at"], s["transaction_count"]
            ))

        for t in transactions_list:
            cursor.execute("""
                INSERT INTO transactions (
                    id, order_ref, merchant_id, amount, fee, tax, net_amount,
                    currency, status, payment_method, customer_email, created_at,
                    settlement_date, settlement_id, bank_ref, failure_reason,
                    dispute_status, refund_amount, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                t["id"], t["order_ref"], t["merchant_id"], t["amount"], t["fee"], t["tax"], t["net_amount"],
                t["currency"], t["status"], t["payment_method"], t["customer_email"], t["created_at"],
                t["settlement_date"], t["settlement_id"], t["bank_ref"], t["failure_reason"],
                t["dispute_status"], t["refund_amount"], t["notes"]
            ))

    print(f"Generated {len(transactions_list)} transactions and {len(settlements_dict)} settlements in {DB_PATH}")

if __name__ == "__main__":
    generate_synthetic_data()
