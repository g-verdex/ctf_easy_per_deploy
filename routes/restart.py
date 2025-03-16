from flask import jsonify, request
import docker
from docker_utils import client
from db import get_container_by_user_uuid
from config import config
from . import main_routes

@main_routes.route("/restart", methods=["POST"])
def restart_container():
    user_uuid = request.cookies.get('user_uuid')

    container_data = get_container_by_user_uuid(user_uuid)
    if not container_data:
        return jsonify({"error": "No active container"}), 400

    container_id = container_data[0]

    try:
        container = client.containers.get(container_id)
        container.restart()
    except docker.errors.NotFound:
        return jsonify({"error": "Container not found"}), 404

    return jsonify({"message": "Container restarted"})
