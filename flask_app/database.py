import psycopg2
from psycopg2 import pool
import os
import time
import logging
import random
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

# Setup logging
logger = logging.getLogger('ctf-deployer')

# Global connection pool
pg_pool = None

# Initialize the connection pool
def init_db_pool():
    global pg_pool
    try:
        pg_pool = pool.ThreadedConnectionPool(
            5,  # Minimum connections
            20, # Maximum connections
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        logger.info(f"Initialized PostgreSQL connection pool to {DB_HOST}:{DB_PORT}/{DB_NAME}")
    except Exception as e:
        logger.error(f"Failed to initialize PostgreSQL connection pool: {str(e)}")
        raise RuntimeError(f"Database connection error: {str(e)}")

# Initialize database schema
def init_db():
    logger.info("Initializing database schema...")
    try:
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                # Create containers table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS containers (
                        id TEXT PRIMARY KEY,
                        port INTEGER NOT NULL,
                        start_time BIGINT NOT NULL,
                        expiration_time BIGINT NOT NULL,
                        user_uuid TEXT NOT NULL,
                        ip_address TEXT NOT NULL
                    )
                """)
                
                # Create IP rate limiting table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ip_requests (
                        ip_address TEXT NOT NULL,
                        request_time BIGINT NOT NULL,
                        PRIMARY KEY (ip_address, request_time)
                    )
                """)
                
                # Add useful indexes
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_containers_user_uuid 
                    ON containers (user_uuid)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_containers_expiration
                    ON containers (expiration_time)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_ip_requests_time
                    ON ip_requests (request_time)
                """)
                
                conn.commit()
                logger.info("Database schema initialized successfully")
        finally:
            release_connection(conn)
    except Exception as e:
        logger.error(f"Failed to initialize database schema: {str(e)}")
        raise

# Get a connection from the pool
def get_connection():
    if pg_pool is None:
        init_db_pool()
    
    try:
        return pg_pool.getconn()
    except Exception as e:
        logger.error(f"Failed to get database connection: {str(e)}")
        raise

# Release a connection back to the pool
def release_connection(conn):
    if pg_pool is not None and conn is not None:
        try:
            pg_pool.putconn(conn)
        except Exception as e:
            logger.error(f"Failed to release database connection: {str(e)}")

# Execute a query with retry logic
def execute_query(query, params=(), fetchone=False, max_retries=3):
    """Execute a PostgreSQL query with retry logic for transient errors"""
    # Convert SQLite placeholder ? to PostgreSQL %s
    query = query.replace('?', '%s')
    
    retry_count = 0
    last_error = None
    
    while retry_count <= max_retries:
        conn = None
        try:
            conn = get_connection()
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                
                # Determine if this is a SELECT query (returns data) or a modification query
                is_select_query = query.strip().upper().startswith('SELECT')
                
                if is_select_query:
                    if fetchone:
                        result = cursor.fetchone()
                    else:
                        result = cursor.fetchall()
                else:
                    # For INSERT, UPDATE, DELETE, we don't try to fetch results
                    conn.commit()
                    # Return row count for non-SELECT queries
                    result = cursor.rowcount
                    
                conn.commit()
                return result
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            last_error = e
            retry_count += 1
            
            # Only retry on specific types of errors
            if retry_count <= max_retries:
                wait_time = 0.5 * (2 ** (retry_count - 1))  # Exponential backoff
                logger.warning(f"Database error: {str(e)}. Retrying in {wait_time}s... (Attempt {retry_count}/{max_retries})")
                time.sleep(wait_time)
            else:
                logger.error(f"Database operation failed after {max_retries} retries: {str(e)}")
                raise
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            raise
        finally:
            if conn:
                release_connection(conn)

# Function for executing INSERT queries specifically - doesn't try to return data
def execute_insert(query, params=()):
    """Special case for INSERT queries that don't need to return results"""
    # Convert SQLite placeholder ? to PostgreSQL %s
    query = query.replace('?', '%s')
    
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Insert error: {str(e)}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        raise
    finally:
        if conn:
            release_connection(conn)

# Remove container from DB
def remove_container_from_db(container_id):
    execute_insert("DELETE FROM containers WHERE id = %s", (container_id,))

# Record IP request for rate limiting with better efficiency
def record_ip_request(ip_address):
    """Records an IP address's request for rate limiting purposes"""
    try:
        current_time = int(time.time())
        logger.info(f"Recording request from IP {ip_address} at {current_time}")
        
        # Use execute_insert which doesn't try to fetch results
        execute_insert(
            "INSERT INTO ip_requests (ip_address, request_time) VALUES (%s, %s)", 
            (ip_address, current_time)
        )
        return True
    except psycopg2.errors.UniqueViolation:
        # Duplicate request - safely ignore
        logger.warning(f"Duplicate request record for IP {ip_address} - ignored")
        return False
    except Exception as e:
        logger.error(f"Error recording IP request: {str(e)}")
        return False

# Improved check for IP rate limiting
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
        request_count_result = execute_query(
            "SELECT COUNT(*) FROM ip_requests WHERE ip_address = %s AND request_time > %s",
            (ip_address, cutoff_time),
            fetchone=True
        )
        
        # Count active containers from this IP
        active_count_result = execute_query(
            "SELECT COUNT(*) FROM containers WHERE ip_address = %s",
            (ip_address,),
            fetchone=True
        )
        
        request_count = request_count_result[0] if request_count_result else 0
        active_count = active_count_result[0] if active_count_result else 0
        
        total_count = request_count + active_count
        
        # Clean up old records periodically (with probabilistic approach to reduce overhead)
        if random.random() < 0.1:  # 10% chance on each check
            execute_insert("DELETE FROM ip_requests WHERE request_time <= %s", (cutoff_time,))
        
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
    return execute_query("SELECT * FROM containers WHERE user_uuid = %s", (user_uuid,), fetchone=True)

# Function to store a new container in the database
def store_container(container_id, port, user_uuid, ip_address, expiration_time):
    """Store a new container in the database with proper error handling"""
    try:
        current_time = int(time.time())
        
        # Use execute_insert which doesn't try to fetch results
        return execute_insert(
            "INSERT INTO containers (id, port, start_time, expiration_time, user_uuid, ip_address) VALUES (%s, %s, %s, %s, %s, %s)",
            (container_id, port, current_time, expiration_time, user_uuid, ip_address)
        )
    except Exception as e:
        logger.error(f"Error storing container in database: {str(e)}")
        return False
