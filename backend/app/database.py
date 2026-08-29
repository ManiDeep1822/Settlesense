import sqlite3
from pathlib import Path
from contextlib import contextmanager
from backend.app.config import DB_PATH

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@contextmanager
def db_session():
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with db_session() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settlements (
                settlement_id TEXT PRIMARY KEY,
                merchant_id TEXT NOT NULL,
                settlement_date TEXT NOT NULL,
                total_amount REAL NOT NULL,
                fees_deducted REAL NOT NULL,
                tax_deducted REAL NOT NULL,
                net_payout REAL NOT NULL,
                status TEXT NOT NULL,
                bank_utr TEXT,
                account_number TEXT,
                cycle_type TEXT NOT NULL,
                failure_reason TEXT,
                processed_at TEXT,
                transaction_count INTEGER DEFAULT 0
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                order_ref TEXT NOT NULL,
                merchant_id TEXT NOT NULL,
                amount REAL NOT NULL,
                fee REAL NOT NULL,
                tax REAL NOT NULL,
                net_amount REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'INR',
                status TEXT NOT NULL,
                payment_method TEXT NOT NULL,
                customer_email TEXT,
                created_at TEXT NOT NULL,
                settlement_date TEXT,
                settlement_id TEXT,
                bank_ref TEXT,
                failure_reason TEXT,
                dispute_status TEXT,
                refund_amount REAL DEFAULT 0.0,
                notes TEXT,
                FOREIGN KEY (settlement_id) REFERENCES settlements(settlement_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exceptions_log (
                id TEXT PRIMARY KEY,
                query_text TEXT NOT NULL,
                exception_type TEXT NOT NULL,
                reason TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                candidate_record_ids TEXT,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'UNRESOLVED',
                resolution_notes TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accuracy_runs (
                id TEXT PRIMARY KEY,
                run_timestamp TEXT NOT NULL,
                total_tests INTEGER NOT NULL,
                passed INTEGER NOT NULL,
                partially_passed INTEGER NOT NULL,
                failed INTEGER NOT NULL,
                correctly_declined INTEGER NOT NULL,
                accuracy_percentage REAL NOT NULL,
                avg_latency_ms REAL NOT NULL,
                results_json TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_logs (
                id TEXT PRIMARY KEY,
                query_text TEXT NOT NULL,
                response_text TEXT NOT NULL,
                confidence TEXT NOT NULL,
                cited_record_ids TEXT,
                latency_ms REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_txn_order_ref ON transactions(order_ref)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_txn_status ON transactions(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_txn_created_at ON transactions(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_txn_settlement_id ON transactions(settlement_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_settle_date ON settlements(settlement_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_settle_status ON settlements(status)")
