import socket
import threading
import logging
import time
from config import START_RANGE, STOP_RANGE, SOCKET_BIND_TIMEOUT

# Setup logging
logger = logging.getLogger('ctf-deployer')

# Global dictionary to hold socket objects for each port
# We'll store multiple socket objects per port (one for each interface)
reserved_sockets = {}
socket_lock = threading.RLock()

# Interfaces to bind to for complete port reservation
INTERFACES = ['0.0.0.0', '127.0.0.1']

def reserve_all_ports():
    """
    Reserve all ports in the configured range by opening sockets on them.
    This prevents other processes from binding to these ports.
    
    Returns:
        (int, int): Tuple of (available_ports_count, unavailable_ports_count)
    """
    available_ports = []
    unavailable_ports = []
    
    logger.info(f"Reserving all ports in range {START_RANGE}-{STOP_RANGE}...")
    
    # First, close any existing sockets
    close_all_sockets()
    
    # Try to bind to each port
    with socket_lock:
        for port in range(START_RANGE, STOP_RANGE):
            port_sockets = []
            port_reserved = True
            
            # Bind to each interface
            for interface in INTERFACES:
                try:
                    # Create a socket WITHOUT setting SO_REUSEADDR
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(SOCKET_BIND_TIMEOUT)
                    sock.bind((interface, port))
                    sock.listen(1)  # Start listening to keep the socket active
                    port_sockets.append(sock)
                    
                except (socket.error, OSError) as e:
                    # Port is already in use on this interface
                    logger.warning(f"Port {port} could not be reserved on {interface}: {str(e)}")
                    port_reserved = False
                    # Close any sockets we managed to create for this port
                    for s in port_sockets:
                        try:
                            s.close()
                        except:
                            pass
                    break
            
            # If we successfully reserved the port on all interfaces
            if port_reserved and port_sockets:
                reserved_sockets[port] = port_sockets
                available_ports.append(port)
                
                # Log progress periodically
                if len(available_ports) % 10 == 0:  # Log every 10 ports
                    logger.debug(f"Reserved {len(available_ports)} ports so far...")
            else:
                unavailable_ports.append(port)
    
    logger.info(f"Successfully reserved {len(available_ports)} ports. {len(unavailable_ports)} ports were unavailable.")
    if unavailable_ports:
        logger.warning(f"Unavailable ports: {unavailable_ports[:10]}{'...' if len(unavailable_ports) > 10 else ''}")
    
    return len(available_ports), len(unavailable_ports)

def is_port_reserved(port):
    """
    Check if a port is currently reserved by us.
    
    Args:
        port: Port number to check
        
    Returns:
        Boolean indicating if we have sockets bound to this port
    """
    with socket_lock:
        return port in reserved_sockets and reserved_sockets[port] 

def release_port_reservation(port):
    """
    Release a port reservation by closing its sockets.
    This allows Docker to bind to this port.
    
    Args:
        port: Port number to release
        
    Returns:
        Boolean indicating success
    """
    with socket_lock:
        if port not in reserved_sockets or not reserved_sockets[port]:
            logger.warning(f"Port {port} is not currently reserved")
            return False
        
        try:
            # Close all sockets for this port
            for sock in reserved_sockets[port]:
                try:
                    sock.close()
                except Exception as e:
                    logger.error(f"Error closing socket for port {port}: {str(e)}")
            
            # Mark as released but keep the entry so we know it was once reserved
            reserved_sockets[port] = None
            logger.info(f"Released port reservation for port {port}")
            return True
        except Exception as e:
            logger.error(f"Error releasing port {port} reservation: {str(e)}")
            return False

def re_reserve_port(port):
    """
    Attempt to re-reserve a port that was previously released.
    
    Args:
        port: Port number to re-reserve
        
    Returns:
        Boolean indicating success
    """
    with socket_lock:
        # Check if the port is already reserved
        if is_port_reserved(port) and reserved_sockets[port] is not None:
            logger.warning(f"Port {port} is already reserved")
            return True
        
        port_sockets = []
        port_reserved = True
        
        # Try to bind to each interface
        for interface in INTERFACES:
            try:
                # Create a new socket WITHOUT setting SO_REUSEADDR
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(SOCKET_BIND_TIMEOUT)
                sock.bind((interface, port))
                sock.listen(1)
                port_sockets.append(sock)
                
            except (socket.error, OSError) as e:
                logger.warning(f"Failed to re-reserve port {port} on {interface}: {str(e)}")
                port_reserved = False
                # Close any sockets we managed to create
                for s in port_sockets:
                    try:
                        s.close()
                    except:
                        pass
                break
        
        # If we successfully reserved on all interfaces
        if port_reserved and port_sockets:
            reserved_sockets[port] = port_sockets
            logger.info(f"Successfully re-reserved port {port}")
            return True
        else:
            reserved_sockets[port] = None  # Mark as not reserved
            logger.warning(f"Failed to re-reserve port {port} on all interfaces")
            return False

def close_all_sockets():
    """
    Close all reserved sockets.
    This should be called during shutdown.
    """
    with socket_lock:
        sockets_closed = 0
        for port, sockets_list in list(reserved_sockets.items()):
            if sockets_list:
                for sock in sockets_list:
                    try:
                        sock.close()
                        sockets_closed += 1
                    except Exception as e:
                        logger.error(f"Error closing socket for port {port}: {str(e)}")
                
        reserved_sockets.clear()
        logger.info(f"Closed {sockets_closed} reserved port sockets")

def get_available_ports():
    """
    Get a list of ports that are currently reserved by us.
    
    Returns:
        List of available port numbers
    """
    with socket_lock:
        return [port for port, sockets in reserved_sockets.items() 
                if sockets is not None]

def get_port_status():
    """
    Get status of all ports in our range.
    
    Returns:
        Dictionary with port statistics
    """
    with socket_lock:
        total_ports = STOP_RANGE - START_RANGE
        reserved_count = sum(1 for sockets in reserved_sockets.values() if sockets is not None)
        released_count = sum(1 for sockets in reserved_sockets.values() if sockets is None)
        unavailable_count = total_ports - (reserved_count + released_count)
        
        return {
            "total_ports": total_ports,
            "reserved_ports": reserved_count,
            "released_ports": released_count,
            "unavailable_ports": unavailable_count,
            "reserved_percent": (reserved_count / total_ports) * 100 if total_ports > 0 else 0
        }

# Cleanup function to be registered with atexit
def cleanup():
    """Close all sockets when the application exits."""
    logger.info("Cleaning up port reservations...")
    close_all_sockets()
