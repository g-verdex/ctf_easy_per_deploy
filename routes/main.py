from flask import render_template, request, make_response
import uuid
from db import get_container_by_user_uuid
from config import config
from . import main_routes

@main_routes.route("/")
def index():
    user_uuid = request.cookies.get('user_uuid')

    if not user_uuid:
        user_uuid = str(uuid.uuid4())
        response = make_response(render_template("index.html", user_container=None, add_minutes=(config.ADD_TIME // 60)))
        response.set_cookie('user_uuid', user_uuid)
        return response

    user_container = get_container_by_user_uuid(user_uuid)
    response = make_response(render_template("index.html", user_container=user_container, add_minutes=(config.ADD_TIME // 60)))
    return response
