from flask import jsonify, request
from docker_utils import client
from db import get_container_by_user_uuid, delete_container
from config import config
from . import main_routes
import docker

@main_routes.route("/stop", methods=["POST"])
def stop_container():
    user_uuid = request.cookies.get('user_uuid')

    container_data = get_container_by_user_uuid(user_uuid)
    if not container_data:
        return jsonify({"error": "No active container"}), 400

    container_id, port = container_data

    try:
        container = client.containers.get(container_id)
        container.stop()
        container.remove()
        config.USED_PORTS.discard(port)
    except docker.errors.NotFound:
        pass

    delete_container(container_id)

    return jsonify({"message": "Container stopped"})
