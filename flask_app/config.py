import os
from dotenv import load_dotenv

# Try to load from .env file (root level)
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

# Container settings
LEAVE_TIME = int(os.getenv('LEAVE_TIME', 1800))  # Default: 30 minutes
ADD_TIME = int(os.getenv('ADD_TIME', 600))      # Default: 10 minutes
IMAGES_NAME = os.getenv('IMAGES_NAME', "localhost/generic_ctf_task:latest")
FLAG = os.getenv('FLAG', 'CTF{generic_flag_for_testing}')
PORT_IN_CONTAINER = int(os.getenv('PORT_IN_CONTAINER', '80'))
PORT_RANGE = range(int(os.getenv('START_RANGE', 9000)), int(os.getenv('STOP_RANGE', 10001)))
DB_PATH = os.getenv('DB_PATH', './data/containers.db')

# Rate limiting
MAX_CONTAINERS_PER_HOUR = int(os.getenv('MAX_CONTAINERS_PER_HOUR', 5))
RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', 3600))  # 1 hour in seconds

# CTF Challenge title and description
CHALLENGE_TITLE = os.getenv('CHALLENGE_TITLE', 'Generic CTF Challenge')
CHALLENGE_DESCRIPTION = os.getenv('CHALLENGE_DESCRIPTION', 
                                'Solve the challenge to find the hidden flag!')
