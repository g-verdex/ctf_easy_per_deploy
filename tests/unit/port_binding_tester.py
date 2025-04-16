#!/usr/bin/env python3
"""
Port Binding Tester for CTF Deployer

This script tests whether the CTF Deployer's port reservation system is working correctly
by attempting to bind to each port in the configured range. It reports which ports
are properly reserved (binding fails) and which are vulnerable (binding succeeds).
"""

import socket
import argparse
import sys
import os
from dotenv import load_dotenv

def test_port_binding(port, interface='127.0.0.1'):
    """
    Test if we can bind to a specific port on the given interface.
    
    Returns:
        (bool, str): (binding_succeeded, error_message)
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((interface, port))
        sock.listen(1)
        # Successfully bound - this means the port is NOT properly reserved
        return True, None
    except socket.error as e:
        # Failed to bind - this is good! It means the port is properly reserved
        return False, str(e)
    finally:
        sock.close()

def main():
    parser = argparse.ArgumentParser(description='Test CTF Deployer port reservation')
    parser.add_argument('--env', default='.env', help='Path to .env file')
    parser.add_argument('--interfaces', default='127.0.0.1,0.0.0.0', help='Comma-separated list of interfaces to test')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output for each port')
    args = parser.parse_args()
    
    # Load environment variables
    if not os.path.exists(args.env):
        print(f"Error: Environment file {args.env} not found")
        sys.exit(1)
    
    load_dotenv(args.env)
    
    # Get port range from environment
    try:
        start_range = int(os.getenv('START_RANGE'))
        stop_range = int(os.getenv('STOP_RANGE'))
    except (ValueError, TypeError):
        print("Error: Could not parse START_RANGE and STOP_RANGE from environment")
        sys.exit(1)
    
    print(f"Testing port binding for range {start_range}-{stop_range}")
    
    interfaces = args.interfaces.split(',')
    vulnerable_ports = {}
    
    # Test each interface
    for interface in interfaces:
        print(f"\nTesting interface: {interface}")
        vulnerable = []
        
        # Test each port
        for port in range(start_range, stop_range):
            can_bind, error = test_port_binding(port, interface)
            
            if args.verbose:
                status = "VULNERABLE" if can_bind else "Secured"
                print(f"Port {port}: {status}{' - ' + error if error else ''}")
            
            if can_bind:
                vulnerable.append(port)
        
        # Save vulnerable ports for this interface
        vulnerable_ports[interface] = vulnerable
        
        # Show summary for this interface
        secured_count = stop_range - start_range - len(vulnerable)
        print(f"Interface {interface}: {secured_count} secured ports, {len(vulnerable)} vulnerable ports")
        
        if vulnerable:
            print(f"  Vulnerable ports on {interface}: {vulnerable[:10]}{' and more...' if len(vulnerable) > 10 else ''}")
    
    # Overall summary
    all_vulnerable = set()
    for ports in vulnerable_ports.values():
        all_vulnerable.update(ports)
    
    print("\nOVERALL SUMMARY:")
    if not all_vulnerable:
        print("✅ SUCCESS: All ports are properly secured across all tested interfaces!")
    else:
        print(f"❌ WARNING: {len(all_vulnerable)} ports are vulnerable on at least one interface!")
        print(f"Vulnerable ports: {sorted(list(all_vulnerable))[:10]}{' and more...' if len(all_vulnerable) > 10 else ''}")
        sys.exit(1)

if __name__ == "__main__":
    main()
