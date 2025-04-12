from flask import Flask, jsonify, render_template, request, make_response
import threading
import time
import uuid
import docker
import logging
import os
from datetime import datetime
from database import execute_query, record_ip_request, check_ip_rate_limit, get_container_by_uuid
from docker_utils import (
    # Explicitly import PORT_RANGE
    PORT_RANGE,
    get_free_port, 
    client, 
    auto_remove_container, 
    remove_container, 
    get_container_status, 
    get_container_security_options, 
    get_container_capabilities, 
    get_container_tmpfs
)
from config import (IMAGES_NAME, LEAVE_TIME, ADD_TIME, FLAG, PORT_IN_CONTAINER, 
                   CHALLENGE_TITLE, CHALLENGE_DESCRIPTION, CONTAINER_MEMORY_LIMIT,
                   CONTAINER_SWAP_LIMIT, CONTAINER_CPU_LIMIT, CONTAINER_PIDS_LIMIT,
                   ENABLE_READ_ONLY, MAX_CONTAINERS_PER_HOUR, RATE_LIMIT_WINDOW,
                   NETWORK_NAME)  # Added NETWORK_NAME import
from captcha import create_captcha, validate_captcha

app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ctf-deployer')

# Define cookie name
COOKIE_NAME = 'user_uuid'

@app.template_filter('to_datetime')
def to_datetime_filter(timestamp):
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

@app.route("/")
def index():
    user_uuid = request.cookies.get(COOKIE_NAME)
    
    # Get server hostname for the template
    hostname = request.host.split(':')[0] if ':' in request.host else request.host
    is_localhost = hostname == '127.0.0.1' or hostname == 'localhost'

    # Determine protocol (http by default)
    protocol = "http"
    
    logger.info(f"Index accessed by {request.remote_addr} - Using protocol: {protocol} for hostname: {hostname}")

    if not user_uuid:
        user_uuid = str(uuid.uuid4())
        logger.info(f"Creating new user UUID: {user_uuid}")
        response = make_response(render_template("index.html", 
                                               user_container=None, 
                                               add_minutes=(ADD_TIME // 60),
                                               hostname=hostname,
                                               protocol=protocol,
                                               challenge_title=CHALLENGE_TITLE,
                                               challenge_description=CHALLENGE_DESCRIPTION))
        
        # For localhost development, we need less strict cookie settings
        if is_localhost:
            # Development environment - more permissive cookies
            response.set_cookie(COOKIE_NAME, user_uuid, httponly=True, samesite='Lax')
        else:
            # Production environment - less strict cookies for better compatibility
            response.set_cookie(COOKIE_NAME, user_uuid, httponly=True, secure=False, samesite='Lax')
        return response

    logger.info(f"Existing user UUID: {user_uuid}")
    user_container = get_container_by_uuid(user_uuid)
    
    # If container exists, check its actual status
    container_status = None
    if user_container:
        container_status = get_container_status(user_container[0])
    
    response = make_response(render_template("index.html", 
                                           user_container=user_container, 
                                           container_status=container_status,
                                           add_minutes=(ADD_TIME // 60),
                                           hostname=hostname,
                                           protocol=protocol,
                                           challenge_title=CHALLENGE_TITLE,
                                           challenge_description=CHALLENGE_DESCRIPTION))
    return response

@app.route("/get_captcha", methods=["GET"])
def get_captcha():
    """Generate a new CAPTCHA challenge"""
    captcha_id, captcha_image = create_captcha()
    return jsonify({
        "captcha_id": captcha_id,
        "captcha_image": captcha_image
    })


@app.route("/deploy", methods=["POST"])
def deploy_container():
    try:
        user_uuid = request.cookies.get(COOKIE_NAME)
        
        if not user_uuid:
            logger.error(f"Session error: No {COOKIE_NAME} cookie found")
            return jsonify({"error": "Session error. Please refresh the page."}), 400
        
        remote_ip = request.remote_addr
        logger.info(f"Deploy request from IP: {remote_ip}, UUID: {user_uuid}")
        
        # Check if IP has hit rate limits - USE CONFIG VALUES INSTEAD OF HARDCODED
        try:
            # Use the values from config instead of hardcoded values
            if check_ip_rate_limit(remote_ip, time_window=RATE_LIMIT_WINDOW, max_requests=MAX_CONTAINERS_PER_HOUR):
                logger.warning(f"Rate limit exceeded for IP: {remote_ip}")
                return jsonify({"error": f"You have reached the maximum number of deployments allowed per hour (limit: {MAX_CONTAINERS_PER_HOUR})."}), 429
        except Exception as e:
            logger.error(f"Error during rate limit check: {str(e)}")
            return jsonify({"error": "Internal server error during rate limit check."}), 500

        # Log request data for debugging
        try:
            data = request.get_json()
            logger.info(f"Request data: {data}")
            
            if not data:
                logger.error("No JSON data in request")
                return jsonify({"error": "Invalid request format. Please refresh and try again."}), 400
                
            captcha_id = data.get('captcha_id')
            captcha_answer = data.get('captcha_answer')
            
            if not captcha_id or not captcha_answer:
                logger.error(f"Missing captcha data: id={captcha_id}, answer={captcha_answer}")
                return jsonify({"error": "CAPTCHA verification required"}), 400
            
            logger.info(f"Validating captcha: id={captcha_id}, answer={captcha_answer}")
            if not validate_captcha(captcha_id, captcha_answer):
                logger.error(f"Incorrect captcha answer: {captcha_answer}")
                return jsonify({"error": "Incorrect CAPTCHA answer. Please try again."}), 400
                
        except Exception as e:
            logger.error(f"Error parsing request data: {str(e)}")
            return jsonify({"error": "Invalid request format. Please refresh and try again."}), 400

        try:
            existing_container = get_container_by_uuid(user_uuid)
            if existing_container:
                logger.warning(f"User {user_uuid} already has container: {existing_container[0]}")
                return jsonify({"error": "You already have a running container"}), 400
        except Exception as e:
            logger.error(f"Error checking existing container: {str(e)}")
            return jsonify({"error": "Error checking for existing containers."}), 500
        
        # CRITICAL FIX: Check if PORT_RANGE is properly initialized
        try:
            # Ensure PORT_RANGE is properly initialized and contains values
            if not hasattr(PORT_RANGE, '__iter__') or len(list(PORT_RANGE)) == 0:
                logger.error(f"PORT_RANGE is invalid: {PORT_RANGE}")
                return jsonify({"error": "Invalid port range configuration."}), 500
                
            port = get_free_port()
            if not port:
                logger.error("No available ports")
                return jsonify({"error": "No available ports. Please try again later."}), 400
            logger.info(f"Assigned port: {port}")
        except Exception as e:
            logger.error(f"Error getting free port: {str(e)}")
            return jsonify({"error": "Error allocating port for container."}), 500

        expiration_time = int(time.time()) + LEAVE_TIME
        
        # Create a shortened UUID for container naming
        short_uuid = user_uuid.split('-')[0] if '-' in user_uuid else user_uuid[:8]
        
        try:
            # Get security options
            security_options = get_container_security_options()
            logger.info(f"Security options: {security_options}")
            
            # Get capability options
            capabilities = get_container_capabilities()
            logger.info(f"Capabilities: {capabilities}")
            
            # Get tmpfs configuration
            tmpfs = get_container_tmpfs()
            logger.info(f"Tmpfs config: {tmpfs}")
        except Exception as e:
            logger.error(f"Error configuring container options: {str(e)}")
            return jsonify({"error": "Error configuring container security options."}), 500
        
        # Prepare container configuration
        try:
            container_config = {
                'image': IMAGES_NAME,
                'detach': True,
                'ports': {f"{PORT_IN_CONTAINER}/tcp": port},
                'environment': {'FLAG': FLAG},
                'hostname': f"ctf-challenge-{short_uuid}",
                'security_opt': security_options,
                'mem_limit': CONTAINER_MEMORY_LIMIT,
                'memswap_limit': CONTAINER_SWAP_LIMIT,
                'cpu_period': 100000,  # Default period (100ms)
                'cpu_quota': int(100000 * CONTAINER_CPU_LIMIT),  # Adjust quota based on CPU limit
                'pids_limit': CONTAINER_PIDS_LIMIT,
                'read_only': ENABLE_READ_ONLY,
                # FIX: Specify the network for proper isolation
                'network': NETWORK_NAME
            }
            
            # Add capabilities if needed
            if capabilities['drop_all']:
                container_config['cap_drop'] = ['ALL']
                container_config['cap_add'] = capabilities['add']
            
            # Add tmpfs if configured
            if tmpfs:
                container_config['tmpfs'] = tmpfs
            
            # Log the container configuration for debugging
            logger.info(f"Container configuration: {container_config}")
        except Exception as e:
            logger.error(f"Error preparing container configuration: {str(e)}")
            return jsonify({"error": "Error preparing container configuration."}), 500
        
        # Create container with configured settings
        try:
            # CRITICAL FIX: Verify Docker client is properly initialized
            if client is None:
                logger.error("Docker client is not initialized")
                return jsonify({"error": "Docker client initialization error."}), 500
                
            # Check Docker connectivity before attempting to create container
            try:
                docker_info = client.info()
                logger.info(f"Connected to Docker daemon: {docker_info.get('Name')}")
            except Exception as docker_error:
                logger.error(f"Failed to connect to Docker daemon: {str(docker_error)}")
                return jsonify({"error": "Cannot connect to Docker daemon."}), 500
                
            container = client.containers.run(**container_config)
            logger.info(f"Created container: {container.id}")
        except Exception as e:
            logger.error(f"Error creating container: {str(e)}")
            return jsonify({"error": f"Failed to create container: {str(e)}"}), 500

        try:
            # Record this IP request
            record_ip_request(remote_ip)
            
            execute_query(
                "INSERT INTO containers (id, port, start_time, expiration_time, user_uuid, ip_address) VALUES (?, ?, ?, ?, ?, ?)",
                (container.id, port, int(time.time()), expiration_time, user_uuid, remote_ip)
            )

            threading.Thread(target=auto_remove_container, args=(container.id, port)).start()
        except Exception as e:
            logger.error(f"Error recording container in database: {str(e)}")
            # Try to clean up container if database insert fails
            try:
                container.remove(force=True)
                logger.info(f"Removed container {container.id} due to database error")
            except:
                logger.error(f"Failed to remove container {container.id} after database error")
            return jsonify({"error": "Error recording container information."}), 500
        
        return jsonify({
            "message": "Your CTF challenge is ready! Redirecting to your instance...",
            "port": port, 
            "id": container.id, 
            "expiration_time": expiration_time
        })
    except Exception as e:
        logger.error(f"Unhandled error in deploy_container: {str(e)}")
        return jsonify({"error": f"Failed to start container: {str(e)}"}), 500

@app.route("/stop", methods=["POST"])
def stop_container():
    user_uuid = request.cookies.get(COOKIE_NAME)
    
    if not user_uuid:
        return jsonify({"error": "Session error. Please refresh the page."}), 400

    try:
        container_data = execute_query("SELECT id, port FROM containers WHERE user_uuid = ?", (user_uuid,), fetchone=True)
        if not container_data:
            return jsonify({"error": "No active container"}), 400

        container_id, port = container_data

        remove_container(container_id, port)
        return jsonify({"message": "Challenge instance stopped successfully"})
    except Exception as e:
        logger.error(f"Error in stop_container: {str(e)}")
        return jsonify({"error": f"Failed to stop container: {str(e)}"}), 500

@app.route("/restart", methods=["POST"])
def restart_container():
    user_uuid = request.cookies.get(COOKIE_NAME)
    
    if not user_uuid:
        return jsonify({"error": "Session error. Please refresh the page."}), 400

    try:
        container_data = execute_query("SELECT id FROM containers WHERE user_uuid = ?", (user_uuid,), fetchone=True)
        if not container_data:
            return jsonify({"error": "No active container"}), 400
        
        container_id = container_data[0]
        
        container = client.containers.get(container_id)
        container.restart()
        return jsonify({"message": "Challenge instance restarted successfully"})
    except docker.errors.NotFound:
        return jsonify({"error": "Container not found"}), 404
    except Exception as e:
        logger.error(f"Error in restart_container: {str(e)}")
        return jsonify({"error": f"Failed to restart container: {str(e)}"}), 500

@app.route("/extend", methods=["POST"])
def extend_container_lifetime():
    user_uuid = request.cookies.get(COOKIE_NAME)
    
    if not user_uuid:
        return jsonify({"error": "Session error. Please refresh the page."}), 400

    try:
        container_data = execute_query("SELECT id, expiration_time FROM containers WHERE user_uuid = ?", (user_uuid,), fetchone=True)
        if not container_data:
            return jsonify({"error": "No active container"}), 400
            
        container_id, expiration_time = container_data
        
        # Increase container lifetime by ADD_TIME
        new_expiration_time = expiration_time + ADD_TIME
        
        # Update lifetime in database
        execute_query(
            "UPDATE containers SET expiration_time = ? WHERE id = ?", 
            (new_expiration_time, container_id)
        )
        
        return jsonify({
            "message": f"Challenge lifetime extended by {ADD_TIME // 60} minutes!", 
            "new_expiration_time": new_expiration_time
        })
    except Exception as e:
        logger.error(f"Error in extend_container_lifetime: {str(e)}")
        return jsonify({"error": f"Failed to extend container lifetime: {str(e)}"}), 500

@app.route("/status")
def status():
    """Endpoint to check the status of the deployer service"""
    try:
        # Make sure we have access to PORT_RANGE from docker_utils
        active_containers = execute_query("SELECT COUNT(*) FROM containers", fetchone=True)[0]
        return jsonify({
            "status": "online",
            "active_containers": active_containers,
            "max_containers": len(list(PORT_RANGE)),
            "service": "Generic CTF Challenge Deployer"
        })
    except Exception as e:
        logger.error(f"Error in status endpoint: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
