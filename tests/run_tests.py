#!/usr/bin/env python3
"""
Test runner for CTF Deployer validation tests

This script runs pre-deployment validation tests to ensure the environment
is properly configured before deploying the application, or post-deployment
tests to verify the deployed application.

Usage:
  python run_tests.py [options]

Options:
  --verbose, -v     Enable verbose output
  --post-deploy, -p Run post-deployment tests (requires running services)
  --unit-tests, -u  Run unit tests
  --help, -h        Show this help message
"""

import argparse
import sys
import importlib
import os
import logging
import traceback
from dotenv import load_dotenv
import time
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test-runner')

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()

def discover_test_modules(test_dir="environment"):
    """Discover all test modules in the specified directory"""
    modules = []
    base_path = os.path.join(os.path.dirname(__file__), test_dir)
    
    # Skip if directory doesn't exist
    if not os.path.exists(base_path):
        logger.warning(f"Test directory {base_path} does not exist")
        return modules
    
    for filename in sorted(os.listdir(base_path)):
        if filename.startswith("test_") and filename.endswith(".py"):
            module_name = filename[:-3]  # Remove .py extension
            module_path = f"tests.{test_dir}.{module_name}"
            try:
                modules.append(importlib.import_module(module_path))
                logger.debug(f"Loaded test module: {module_path}")
            except ImportError as e:
                logger.error(f"Failed to import {module_path}: {e}")
                logger.error(traceback.format_exc())
    
    return modules

def run_pre_deploy_tests(verbose=False):
    """Run all environment validation tests (pre-deployment)"""
    test_modules = discover_test_modules("environment")
    
    if not test_modules:
        logger.error("No pre-deployment test modules found!")
        return False
    
    success = True
    
    logger.info(f"Running {len(test_modules)} pre-deployment validation test modules")
    
    for module in test_modules:
        module_name = module.__name__.split('.')[-1]
        logger.info(f"Running {module_name} tests...")
        
        # Each test module has a run_tests function that returns a boolean
        if hasattr(module, 'run_tests'):
            try:
                if not module.run_tests(verbose):
                    logger.error(f"{module_name} tests failed")
                    success = False
                else:
                    logger.info(f"{module_name} tests passed")
            except Exception as e:
                logger.error(f"Error running {module_name} tests: {e}")
                logger.error(traceback.format_exc())
                success = False
        else:
            logger.warning(f"{module_name} has no run_tests function")
            logger.warning(f"Module contents: {dir(module)}")
    
    return success

def run_post_deploy_tests(verbose=False):
    """Run all post-deployment tests"""
    # First check if the post_deploy directory exists
    post_deploy_dir = os.path.join(os.path.dirname(__file__), "post_deploy")
    if not os.path.exists(post_deploy_dir):
        os.makedirs(post_deploy_dir, exist_ok=True)
        logger.info(f"Created post_deploy directory: {post_deploy_dir}")
    
    # Discover and run post-deployment test modules
    test_modules = discover_test_modules("post_deploy")
    
    # Run API tests if the script exists
    api_test_success = True
    api_test_path = os.path.join(os.path.dirname(__file__), "api", "api_test.sh")
    if os.path.exists(api_test_path):
        logger.info("Running API tests...")
        try:
            # Make sure the script is executable
            os.chmod(api_test_path, 0o755)
            
            # Run the API tests
            result = subprocess.run(
                [api_test_path], 
                check=False,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"API tests failed with code {result.returncode}")
                logger.error(f"Output: {result.stdout}")
                logger.error(f"Errors: {result.stderr}")
                api_test_success = False
            else:
                logger.info("API tests passed")
                if verbose:
                    print(result.stdout)
        except Exception as e:
            logger.error(f"Error running API tests: {e}")
            logger.error(traceback.format_exc())
            api_test_success = False
    
    # Run post-deployment test modules
    module_success = True
    if test_modules:
        logger.info(f"Running {len(test_modules)} post-deployment test modules")
        
        for module in test_modules:
            module_name = module.__name__.split('.')[-1]
            logger.info(f"Running {module_name} post-deployment tests...")
            
            if hasattr(module, 'run_tests'):
                try:
                    if not module.run_tests(verbose):
                        logger.error(f"{module_name} post-deployment tests failed")
                        module_success = False
                    else:
                        logger.info(f"{module_name} post-deployment tests passed")
                except Exception as e:
                    logger.error(f"Error running {module_name} post-deployment tests: {e}")
                    logger.error(traceback.format_exc())
                    module_success = False
            else:
                logger.warning(f"{module_name} has no run_tests function")
    else:
        logger.warning("No post-deployment test modules found")
    
    return api_test_success and module_success

def run_unit_tests(verbose=False):
    """Run unit tests using pytest"""
    logger.info("Running unit tests...")
    
    try:
        # Build the pytest command
        pytest_cmd = ["python", "-m", "pytest"]
        
        # Add the specific test module paths
        test_modules = []
        unit_tests_dir = os.path.join(os.path.dirname(__file__), "unit")
        
        if os.path.exists(unit_tests_dir):
            for filename in os.listdir(unit_tests_dir):
                if filename.startswith("test_") and filename.endswith(".py"):
                    module_path = os.path.join("tests", "unit", filename)
                    test_modules.append(module_path)
        
        if not test_modules:
            logger.warning("No unit test modules found!")
            # Look for test_database_minimal.py in the current directory as fallback
            if os.path.exists(os.path.join(os.path.dirname(__file__), "test_database_minimal.py")):
                test_modules.append(os.path.join("tests", "test_database_minimal.py"))
        
        pytest_cmd.extend(test_modules)
        
        if verbose:
            pytest_cmd.append("-v")
        
        logger.info(f"Running pytest with command: {' '.join(pytest_cmd)}")
        
        # Run pytest
        result = subprocess.run(
            pytest_cmd,
            check=False,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Unit tests failed with code {result.returncode}")
            print(result.stdout)
            print(result.stderr)
            return False
        else:
            logger.info("Unit tests passed")
            if verbose:
                print(result.stdout)
            return True
    except Exception as e:
        logger.error(f"Error running unit tests: {e}")
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run environment validation tests")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("-p", "--post-deploy", action="store_true", help="Run post-deployment tests")
    parser.add_argument("-u", "--unit-tests", action="store_true", help="Run unit tests")
    args = parser.parse_args()
    
    # Configure logging level based on verbosity
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    all_success = True
    
    if args.post_deploy:
        # Only run post-deployment tests
        logger.info("Running post-deployment tests...")
        post_deploy_success = run_post_deploy_tests(args.verbose)
        if post_deploy_success:
            logger.info("All post-deployment tests passed!")
        else:
            logger.error("Some post-deployment tests failed!")
            all_success = False
    elif args.unit_tests:
        # Run unit tests
        logger.info("Running unit tests...")
        unit_tests_success = run_unit_tests(args.verbose)
        if unit_tests_success:
            logger.info("All unit tests passed!")
        else:
            logger.error("Some unit tests failed!")
            all_success = False
    else:
        # Run pre-deployment tests by default
        logger.info("Running pre-deployment validation tests...")
        pre_deploy_success = run_pre_deploy_tests(args.verbose)
        if pre_deploy_success:
            logger.info("All pre-deployment tests passed!")
        else:
            logger.error("Some pre-deployment tests failed!")
            all_success = False
    
    if all_success:
        logger.info("✅ All requested tests passed!")
        sys.exit(0)
    else:
        logger.error("❌ Some tests failed!")
        sys.exit(1)
