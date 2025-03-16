from flask import Blueprint

main_routes = Blueprint('main_routes', __name__)

from .deploy import *