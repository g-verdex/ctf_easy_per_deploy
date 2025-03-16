from flask import Blueprint

main_routes = Blueprint('main_routes', __name__)

from .deploy import *
from .stop import *
from .restart import *
from .extend import *
from .main import index
