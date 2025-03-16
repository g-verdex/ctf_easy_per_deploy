from flask import jsonify, request
import docker
from docker_utils import client
from db import get_container_by_user_uuid, update_container_expiration_time
from config import config
from datetime import datetime
from . import main_routes

@main_routes.route("/extend", methods=["POST"])
def extend_container_lifetime():
    user_uuid = request.cookies.get('user_uuid')

    container_data = get_container_by_user_uuid(user_uuid)
    if not container_data:
        return jsonify({"error": "No active container"}), 400

    container_id, expiration_time = container_data
    new_expiration_time = expiration_time + config.ADD_TIME

    update_container_expiration_time(container_id, new_expiration_time)

    try:
        container = client.containers.get(container_id)
        container.attrs['State']['FinishedAt'] = datetime.fromtimestamp(new_expiration_time).strftime('%Y-%m-%d %H:%M:%S')
    except docker.errors.NotFound:
        return jsonify({"error": "Container not found"}), 404

    return jsonify({"message": "Container lifetime extended", "new_expiration_time": new_expiration_time})
