from flask import Flask, jsonify, render_template, request, make_response
import threading
import time
import uuid
import docker
import requests
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from database import execute_query, remove_container_from_db, record_ip_request, check_ip_rate_limit
from docker_utils import get_free_port, client, auto_remove_container, remove_container
from config import IMAGES_NAME, LEAVE_TIME, ADD_TIME, FLAG, PORT_IN_CONTAINER
from config import HCAPTCHA_SITE_KEY, HCAPTCHA_SECRET_KEY, HCAPTCHA_VERIFY_URL

app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('snake-challenge')

@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    # Content Security Policy to help prevent XSS - allowing hCaptcha domains
    # Make sure to include 'self' in connect-src to allow form submission
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' https://js.hcaptcha.com https://hcaptcha.com https://*.hcaptcha.com https://cdn.jsdelivr.net 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://hcaptcha.com https://*.hcaptcha.com; "
        "frame-src https://*.hcaptcha.com https://hcaptcha.com; "
        "img-src 'self' data: https://cdn.jsdelivr.net https://hcaptcha.com https://*.hcaptcha.com; "
        "connect-src 'self' https://*.hcaptcha.com https://hcaptcha.com;"
    )
    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    # XSS Protection as a secondary defense
    response.headers['X-XSS-Protection'] = '1; mode=block'
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    return response

@app.template_filter('to_datetime')
def to_datetime_filter(timestamp):
    from datetime import datetime
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def verify_hcaptcha(captcha_response, remote_ip):
    """Verify hCaptcha response token with hCaptcha API"""
    try:
        if not HCAPTCHA_SECRET_KEY or not captcha_response:
            logger.warning("hCaptcha verification failed: Missing keys or response")
            return False
        
        logger.info(f"Verifying hCaptcha response, token length: {len(captcha_response)}")
        
        data = {
            'secret': HCAPTCHA_SECRET_KEY,
            'response': captcha_response,
            'remoteip': remote_ip
        }
        
        logger.info(f"Sending verification request to hCaptcha")
        response = requests.post(HCAPTCHA_VERIFY_URL, data=data, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"hCaptcha API returned status code {response.status_code}")
            return False
            
        result = response.json()
        logger.info(f"hCaptcha verification result: {result}")
        
        if not result.get('success', False):
            error_codes = result.get('error-codes', [])
            logger.warning(f"hCaptcha verification failed: {error_codes}")
            
        return result.get('success', False)
    except Exception as e:
        logger.error(f"hCaptcha verification error: {str(e)}")
        return False

@app.route("/")
def index():
    user_uuid = request.cookies.get('user_uuid')
    
    # Get server hostname for the template
    hostname = request.host.split(':')[0] if ':' in request.host else request.host
    is_localhost = hostname == '127.0.0.1' or hostname == 'localhost'

    if not user_uuid:
        user_uuid = str(uuid.uuid4())
        response = make_response(render_template("index.html", 
                                               user_container=None, 
                                               add_minutes=(ADD_TIME // 60),
                                               hostname=hostname,
                                               hcaptcha_site_key=HCAPTCHA_SITE_KEY))
        
        # For localhost development, we need less strict cookie settings
        if is_localhost:
            # Development environment - more permissive cookies
            response.set_cookie('user_uuid', user_uuid, httponly=True, samesite='Lax')
        else:
            # Production environment - secure cookies
            response.set_cookie('user_uuid', user_uuid, httponly=True, secure=True, samesite='Strict')
        return response

    user_container = execute_query("SELECT * FROM containers WHERE user_uuid = ?", (user_uuid,), fetchone=True)
    response = make_response(render_template("index.html", 
                                           user_container=user_container, 
                                           add_minutes=(ADD_TIME // 60),
                                           hostname=hostname,
                                           hcaptcha_site_key=HCAPTCHA_SITE_KEY))
    return response

@app.route("/deploy", methods=["POST"])
def deploy_container():
    user_uuid = request.cookies.get('user_uuid')
    
    if not user_uuid:
        return jsonify({"error": "Session error. Please refresh the page."}), 400
    
    # Extract and verify hCaptcha response
    data = request.get_json()
    
    # Check all possible parameter names for the captcha response
    captcha_response = (
        data.get('captcha-response') or 
        data.get('h-captcha-response') or 
        data.get('g-recaptcha-response')
    )
    
    logger.info(f"Received captcha data: {data}")
    
    if not captcha_response:
        return jsonify({"error": "Please complete the captcha challenge."}), 400
    
    remote_ip = request.remote_addr
    
    # Skip verification if secret key is not set (development mode)
    if not HCAPTCHA_SECRET_KEY:
        logger.warning("hCaptcha secret key not set - VERIFICATION SKIPPED (development mode)")
    elif not verify_hcaptcha(captcha_response, remote_ip):
        logger.warning(f"Failed hCaptcha verification from {remote_ip}")
        return jsonify({"error": "Captcha verification failed. Please try again."}), 400
        
    # Check if IP has hit rate limits (5 containers per hour)
    if check_ip_rate_limit(remote_ip, time_window=3600, max_requests=5):
        logger.warning(f"Rate limit exceeded for IP: {remote_ip}")
        return jsonify({"error": "You have reached the maximum number of deployments allowed per hour."}), 429

    try:
        existing_container = execute_query("SELECT * FROM containers WHERE user_uuid = ?", (user_uuid,), fetchone=True)
        if existing_container:
            return jsonify({"error": "You already have a running container"}), 400
        
        port = get_free_port()
        if not port:
            return jsonify({"error": "No available ports. Please try again later."}), 400

        expiration_time = int(time.time()) + LEAVE_TIME
        
        # Create a shortened UUID for container naming
        short_uuid = user_uuid.split('-')[0] if '-' in user_uuid else user_uuid[:8]
        
        container = client.containers.run(
            IMAGES_NAME, 
            detach=True, 
            ports={f"{PORT_IN_CONTAINER}/tcp": port}, 
            environment={'FLAG': FLAG},
            hostname=f"snake-challenge-{short_uuid}"
        )

        # Record this IP request
        record_ip_request(remote_ip)
        
        try:
            # Try to insert with IP field
            execute_query(
                "INSERT INTO containers (id, port, start_time, expiration_time, user_uuid, ip_address) VALUES (?, ?, ?, ?, ?, ?)",
                (container.id, port, int(time.time()), expiration_time, user_uuid, remote_ip)
            )
        except sqlite3.OperationalError:
            # Fall back to insert without IP if column doesn't exist
            execute_query(
                "INSERT INTO containers (id, port, start_time, expiration_time, user_uuid) VALUES (?, ?, ?, ?, ?)",
                (container.id, port, int(time.time()), expiration_time, user_uuid)
            )

        threading.Thread(target=auto_remove_container, args=(container.id, port)).start()
        
        return jsonify({
            "message": "Your Snake challenge is ready! Redirecting to your instance...",
            "port": port, 
            "id": container.id, 
            "expiration_time": expiration_time
        })
    except Exception as e:
        logger.error(f"Error in deploy_container: {str(e)}")
        return jsonify({"error": f"Failed to start container: {str(e)}"}), 500

@app.route("/stop", methods=["POST"])
def stop_container():
    user_uuid = request.cookies.get('user_uuid')
    
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
    user_uuid = request.cookies.get('user_uuid')
    
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
    user_uuid = request.cookies.get('user_uuid')
    
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
        active_containers = len(execute_query("SELECT id FROM containers"))
        return jsonify({
            "status": "online",
            "active_containers": active_containers,
            "max_containers": len(list(range(int(9000), int(10000)))),
            "service": "Serpent's Hidden Path CTF Challenge Deployer"
        })
    except Exception as e:
        logger.error(f"Error in status endpoint: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
