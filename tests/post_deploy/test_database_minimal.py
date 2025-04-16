"""
Database connection tests for CTF Deployer (Post-Deployment Version)

This module validates that the database is properly running and accessible.
These tests should be run AFTER the database has been deployed.
"""
import os
import sys
import logging
import psycopg2
import time
from dotenv import load_dotenv

# Setup logging
logger = logging.getLogger('test-database-post')

# Load environment variables
load_dotenv()

def test_database_connection(verbose=False):
    """Test that the database server is accessible"""
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    
    if not all([db_host, db_port, db_name, db_user, db_password]):
        logger.error("Database connection parameters are not fully set")
        return False
    
    if verbose:
        logger.info(f"Testing connection to {db_host}:{db_port}/{db_name} as {db_user}")
    
    # When running tests outside of Docker, "postgres" hostname is not resolvable.
    # We'll try "localhost" as a fallback for test environments.
    hosts_to_try = [db_host]
    if db_host == "postgres":
        hosts_to_try.append("localhost")
        if verbose:
            logger.info("Will also try 'localhost' as fallback for Docker hostname 'postgres'")
    
    for host in hosts_to_try:
        try:
            # Try to connect to the database
            conn = psycopg2.connect(
                host=host,
                port=db_port,
                dbname=db_name,
                user=db_user,
                password=db_password,
                connect_timeout=5  # Timeout after 5 seconds
            )
            
            # Check if connection is active
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
                if result and result[0] == 1:
                    if verbose:
                        logger.info(f"Database connection successful to {host}")
                else:
                    logger.error(f"Database connection test to {host} failed")
                    continue  # Try next host if available
            
            conn.close()
            return True
        except psycopg2.OperationalError as e:
            error_str = str(e).lower()
            if host == hosts_to_try[-1]:  # Only log error on the last attempt
                logger.error(f"Database connection error to {host}: {e}")
                
                # Provide more helpful information based on the error
                if "could not connect to server" in error_str:
                    logger.error(f"Could not connect to PostgreSQL server at {host}:{db_port}")
                    logger.error("Make sure the PostgreSQL server is running and accessible")
                elif "password authentication failed" in error_str:
                    logger.error(f"Authentication failed for user '{db_user}'")
                    logger.error("Check that the DB_USER and DB_PASSWORD are correct")
                elif "database" in error_str and "does not exist" in error_str:
                    logger.error(f"Database '{db_name}' does not exist")
                    logger.error("You need to create the database before starting the deployer")
            elif verbose:
                logger.info(f"Could not connect to {host}, trying next host...")
        except Exception as e:
            if host == hosts_to_try[-1]:  # Only log error on the last attempt
                logger.error(f"Unexpected database error: {e}")
    
    return False

def test_database_tables(verbose=False):
    """Test that the required database tables exist and have the correct structure"""
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    
    hosts_to_try = [db_host]
    if db_host == "postgres":
        hosts_to_try.append("localhost")
    
    for host in hosts_to_try:
        try:
            conn = psycopg2.connect(
                host=host,
                port=db_port,
                dbname=db_name,
                user=db_user,
                password=db_password,
                connect_timeout=5
            )
            
            # Get list of tables in the database
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
                # Check required tables
                required_tables = ['containers', 'ip_requests', 'port_allocations']
                missing_tables = [table for table in required_tables if table not in tables]
                
                if missing_tables:
                    logger.error(f"Missing required tables: {', '.join(missing_tables)}")
                    conn.close()
                    continue  # Try next host
                    
                if verbose:
                    logger.info(f"Found required tables: {', '.join(required_tables)}")
                    logger.info(f"All database tables: {', '.join(tables)}")
                
                # Check the structure of each required table
                # In this simplified version, we just check if the tables exist
                # You could expand this to check specific columns if needed
            
            conn.close()
            return True
        except Exception as e:
            if host == hosts_to_try[-1]:  # Only log error on the last attempt
                logger.error(f"Error checking database tables: {e}")
    
    return False

def test_database_permissions(verbose=False):
    """Test that the database user has the necessary permissions"""
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    
    if not all([db_host, db_port, db_name, db_user, db_password]):
        logger.error("Database connection parameters are not fully set")
        return False
    
    # Try connecting to different host options
    hosts_to_try = [db_host]
    if db_host == "postgres":
        hosts_to_try.append("localhost")
        if verbose:
            logger.info("Will also try 'localhost' as fallback for Docker hostname 'postgres'")
    
    for host in hosts_to_try:
        try:
            # Connect to the database
            conn = psycopg2.connect(
                host=host,
                port=db_port,
                dbname=db_name,
                user=db_user,
                password=db_password,
                connect_timeout=5
            )
            
            # Test if we can create a table
            with conn.cursor() as cursor:
                # Create a temporary table
                try:
                    cursor.execute("""
                        CREATE TEMPORARY TABLE _test_permissions (
                            id SERIAL PRIMARY KEY,
                            test_value TEXT
                        )
                    """)
                    
                    # Insert a row
                    cursor.execute("INSERT INTO _test_permissions (test_value) VALUES (%s)", ("test",))
                    
                    # Query the row
                    cursor.execute("SELECT test_value FROM _test_permissions")
                    result = cursor.fetchone()
                    
                    if not result or result[0] != "test":
                        logger.error("Failed to query test table")
                        continue  # Try next host if available
                    
                    if verbose:
                        logger.info(f"Database user has CREATE TABLE, INSERT, and SELECT permissions on {host}")
                except psycopg2.Error as e:
                    logger.error(f"Permission test failed on {host}: {e}")
                    continue  # Try next host if available
                finally:
                    conn.rollback()  # Clean up the transaction
            
            conn.close()
            return True
        except Exception as e:
            if host == hosts_to_try[-1]:  # Only log error on the last attempt
                logger.error(f"Database permission test error: {e}")
            elif verbose:
                logger.info(f"Couldn't connect to {host} for permission tests, trying next host...")
    
    return False

def run_tests(verbose=False):
    """Run all post-deployment database tests"""
    tests = [
        test_database_connection,
        test_database_tables,
        test_database_permissions
    ]
    
    all_tests_passed = True
    
    for test_func in tests:
        try:
            if not test_func(verbose):
                all_tests_passed = False
        except Exception as e:
            logger.error(f"Error in {test_func.__name__}: {e}")
            all_tests_passed = False
    
    return all_tests_passed

if __name__ == "__main__":
    # Set up logging when run directly
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Run all tests with verbose output
    success = run_tests(verbose=True)
    
    if success:
        logger.info("All post-deployment database tests passed!")
        sys.exit(0)
    else:
        logger.error("Some post-deployment database tests failed!")
        sys.exit(1)
