import sqlite3
import os
import time
import logging
from config import DB_PATH

# Setup logging
logger = logging.getLogger('ctf-deployer')

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
        current_time = int(time.time())
        logger.info(f"Recording request from IP {ip_address} at {current_time}")
        execute_query("INSERT INTO ip_requests (ip_address, request_time) VALUES (?, ?)", 
                      (ip_address, current_time))
    except sqlite3.IntegrityError:
        # If there's a primary key violation, just ignore
        logger.warning(f"Duplicate request record for IP {ip_address} - ignored")
        pass
    except Exception as e:
        logger.error(f"Error recording IP request: {str(e)}")

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
    try:
        if not ip_address or ip_address == "127.0.0.1":
            # Skip rate limiting for localhost
            logger.info("Skipping rate limit for localhost")
            return False
            
        current_time = int(time.time())
        cutoff_time = current_time - time_window
        
        # Count requests from this IP in the time window
        count_result = execute_query(
            "SELECT COUNT(*) FROM ip_requests WHERE ip_address = ? AND request_time > ?", 
            (ip_address, cutoff_time), 
            fetchone=True
        )
        
        if not count_result:
            logger.warning(f"Failed to get count for IP {ip_address}")
            return False
            
        request_count = count_result[0]
        
        # Also count active containers from this IP
        active_count_result = execute_query(
            "SELECT COUNT(*) FROM containers WHERE ip_address = ?", 
            (ip_address,), 
            fetchone=True
        )
        
        if not active_count_result:
            logger.warning(f"Failed to get active container count for IP {ip_address}")
            return False
            
        active_count = active_count_result[0]
        
        total_count = request_count + active_count
        
        # Clean up old records
        execute_query("DELETE FROM ip_requests WHERE request_time <= ?", (cutoff_time,))
        
        # Log rate limit values for debugging
        logger.info(f"IP: {ip_address}, Recent requests: {request_count}, Active containers: {active_count}, Total: {total_count}, Limit: {max_requests}")
        
        # Check if limit exceeded
        return total_count >= max_requests
        
    except Exception as e:
        logger.error(f"Error checking rate limit: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        # In case of error, allow the request to proceed
        return False

# Get all active containers
def get_all_active_containers():
    return execute_query("SELECT * FROM containers")

# Get container by user UUID
def get_container_by_uuid(user_uuid):
    return execute_query("SELECT * FROM containers WHERE user_uuid = ?", (user_uuid,), fetchone=True)
