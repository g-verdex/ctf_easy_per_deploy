from flask import jsonify, request
import threading
import time
import uuid
from docker_utils import get_free_port, run_container
from db import insert_container
from config import config
from . import main_routes

@main_routes.route("/deploy", methods=["POST"])
def deploy_container():
    user_uuid = request.cookies.get('user_uuid')

    existing_container = get_container_by_user_uuid(user_uuid)
    if existing_container:
        return jsonify({"error": "You already have a running container"}), 400

    port = get_free_port(config.USED_PORTS)
    if not port:
        return jsonify({"error": "No available ports"}), 400

    expiration_time = int(time.time()) + config.LEAVE_TIME
    container = run_container(config.IMAGE_NAME, port)

    insert_container(container.id, port, int(time.time()), expiration_time, user_uuid)

    threading.Thread(target=auto_remove_container, args=(container.id, port)).start()

    return jsonify({"message": "Container started", "port": port, "id": container.id, "expiration_time": expiration_time})
