"""
Database validation tests for CTF Deployer

This module validates that the database connection settings are correct and 
that the database server is accessible.
"""
import os
import sys
import logging
import psycopg2
import time
from dotenv import load_dotenv

# Setup logging
logger = logging.getLogger('test-database')

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
    
    try:
        # Try to connect to the database
        conn = psycopg2.connect(
            host=db_host,
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
                    logger.info("Database connection successful")
            else:
                logger.error("Database connection test failed")
                return False
        
        conn.close()
        return True
    except psycopg2.OperationalError as e:
        logger.error(f"Database connection error: {e}")
        
        # Provide more helpful information based on the error
        error_str = str(e).lower()
        if "could not connect to server" in error_str:
            logger.error(f"Could not connect to PostgreSQL server at {db_host}:{db_port}")
            logger.error("Make sure the PostgreSQL server is running and accessible")
        elif "password authentication failed" in error_str:
            logger.error(f"Authentication failed for user '{db_user}'")
            logger.error("Check that the DB_USER and DB_PASSWORD are correct")
        elif "database" in error_str and "does not exist" in error_str:
            logger.error(f"Database '{db_name}' does not exist")
            logger.error("You need to create the database before starting the deployer")
        
        return False
    except Exception as e:
        logger.error(f"Unexpected database error: {e}")
        return False

def test_connection_params_consistency(verbose=False):
    """Test that database connection parameters are consistent with docker-compose.yml"""
    db_host = os.getenv("DB_HOST")
    
    # When running with docker-compose, the DB_HOST should typically be 'postgres'
    # unless an external database is being used
    expected_docker_db_host = "postgres"
    
    if db_host != expected_docker_db_host:
        # This is not a failure, just a warning
        logger.warning(f"DB_HOST is set to '{db_host}', but the docker-compose configuration typically uses '{expected_docker_db_host}'")
        logger.warning("This is only an issue if you're using the built-in PostgreSQL container from docker-compose.yml")
        logger.warning("If you're using an external database, this warning can be ignored")
    elif verbose:
        logger.info(f"DB_HOST is set to '{db_host}', which is consistent with docker-compose.yml")
    
    # Always return True since this is just a warning
    return True

def test_database_pool_settings(verbose=False):
    """Test that database pool settings are valid"""
    db_pool_min = os.getenv("DB_POOL_MIN")
    db_pool_max = os.getenv("DB_POOL_MAX")
    
    if not db_pool_min or not db_pool_max:
        logger.error("DB_POOL_MIN or DB_POOL_MAX is not set")
        return False
    
    try:
        db_pool_min = int(db_pool_min)
        db_pool_max = int(db_pool_max)
        
        if db_pool_min <= 0:
            logger.error(f"DB_POOL_MIN must be positive, got {db_pool_min}")
            return False
        
        if db_pool_max <= 0:
            logger.error(f"DB_POOL_MAX must be positive, got {db_pool_max}")
            return False
        
        if db_pool_min > db_pool_max:
            logger.error(f"DB_POOL_MIN ({db_pool_min}) must be less than or equal to DB_POOL_MAX ({db_pool_max})")
            return False
        
        if db_pool_max > 100:
            # This is not a failure, just a warning
            logger.warning(f"DB_POOL_MAX is set to {db_pool_max}, which is quite high")
            logger.warning("Consider reducing it to avoid overloading the database server")
        
        if verbose:
            logger.info(f"Database pool settings are valid: MIN={db_pool_min}, MAX={db_pool_max}")
        
        return True
    except ValueError:
        logger.error(f"DB_POOL_MIN ({db_pool_min}) and DB_POOL_MAX ({db_pool_max}) must be integers")
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
    
    try:
        # Connect to the database
        conn = psycopg2.connect(
            host=db_host,
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
                    return False
                
                if verbose:
                    logger.info("Database user has CREATE TABLE, INSERT, and SELECT permissions")
            except psycopg2.Error as e:
                logger.error(f"Permission test failed: {e}")
                return False
            finally:
                conn.rollback()  # Clean up the transaction
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Database permission test error: {e}")
        return False

def run_tests(verbose=False):
    """Run all database validation tests"""
    tests = [
        test_database_connection,
        test_connection_params_consistency,
        test_database_pool_settings,
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
        logger.info("All database tests passed!")
        sys.exit(0)
    else:
        logger.error("Some database tests failed!")
        sys.exit(1)
