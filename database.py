import sqlite3
import os
import time
from config import DB_PATH

# Ensure the directory exists
def ensure_db_dir():
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)

# Initialization of the database
def init_db():
    ensure_db_dir()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        
        # Create containers table if not exists
        c.execute("""
            CREATE TABLE IF NOT EXISTS containers (
                id TEXT PRIMARY KEY,
                port INTEGER,
                start_time INTEGER,
                expiration_time INTEGER,
                user_uuid TEXT,
                ip_address TEXT
            )
        """)
        
        # Add IP column if it doesn't exist (for backward compatibility)
        try:
            c.execute("SELECT ip_address FROM containers LIMIT 1")
        except sqlite3.OperationalError:
            print("Adding ip_address column to containers table")
            c.execute("ALTER TABLE containers ADD COLUMN ip_address TEXT")
        
        # Create IP rate limiting table
        c.execute("""
            CREATE TABLE IF NOT EXISTS ip_requests (
                ip_address TEXT,
                request_time INTEGER,
                PRIMARY KEY (ip_address, request_time)
            )
        """)
        conn.commit()

# Function for executing SQL queries
def execute_query(query, params=(), fetchone=False):
    ensure_db_dir()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()
        return c.fetchone() if fetchone else c.fetchall()

# Remove container from DB
def remove_container_from_db(container_id):
    execute_query("DELETE FROM containers WHERE id = ?", (container_id,))

# Record IP request for rate limiting
def record_ip_request(ip_address):
    """Records an IP address's request for rate limiting purposes"""
    try:
        execute_query("INSERT INTO ip_requests (ip_address, request_time) VALUES (?, ?)", 
                      (ip_address, int(time.time())))
    except sqlite3.IntegrityError:
        # If there's a primary key violation, just ignore
        pass

# Check if IP has exceeded request limits
def check_ip_rate_limit(ip_address, time_window=3600, max_requests=5):
    """
    Check if an IP has made too many container requests within a time window
    
    Args:
        ip_address: The IP address to check
        time_window: Time window in seconds (default: 1 hour)
        max_requests: Maximum allowed requests in the time window
        
    Returns:
        Boolean: True if rate limit exceeded, False otherwise
    """
    if not ip_address or ip_address == "127.0.0.1":
        # Skip rate limiting for localhost
        return False
        
    current_time = int(time.time())
    cutoff_time = current_time - time_window
    
    # Count requests from this IP in the time window
    count = execute_query(
        "SELECT COUNT(*) FROM ip_requests WHERE ip_address = ? AND request_time > ?", 
        (ip_address, cutoff_time), 
        fetchone=True
    )[0]
    
    # Also count active containers from this IP
    try:
        active_count = execute_query(
            "SELECT COUNT(*) FROM containers WHERE ip_address = ?", 
            (ip_address,), 
            fetchone=True
        )[0]
    except Exception:
        # If there's an error (e.g., column doesn't exist), assume 0
        active_count = 0
    
    # Clean up old records
    execute_query("DELETE FROM ip_requests WHERE request_time <= ?", (cutoff_time,))
    
    return (count + active_count) >= max_requests
