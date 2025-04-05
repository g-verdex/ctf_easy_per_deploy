import os
from dotenv import load_dotenv

# Try to load from .env file (root level)
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

# Container settings
LEAVE_TIME = int(os.getenv('LEAVE_TIME', 240))
ADD_TIME = int(os.getenv('ADD_TIME', 120))
IMAGES_NAME = os.getenv('IMAGES_NAME', "localhost/snake_game:latest")
FLAG = os.getenv('FLAG', 'test_flag{}')
PORT_IN_CONTAINER = int(os.getenv('PORT_IN_CONTAINER', '80'))
PORT_RANGE = range(int(os.getenv('START_RANGE', 9000)), int(os.getenv('STOP_RANGE', 10001)))
DB_PATH = os.getenv('DB_PATH', '/app/data/containers.db')

# Rate limiting
MAX_CONTAINERS_PER_HOUR = int(os.getenv('MAX_CONTAINERS_PER_HOUR', 5))
RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', 3600))  # 1 hour in seconds

# hCaptcha settings - read from environment or hcaptcha_key file
HCAPTCHA_SITE_KEY = os.getenv('HCAPTCHA_SITE_KEY')
HCAPTCHA_SECRET_KEY = os.getenv('HCAPTCHA_SECRET_KEY')
HCAPTCHA_VERIFY_URL = "https://hcaptcha.com/siteverify"

# If keys not in environment, try reading from hcaptcha_key file
if not HCAPTCHA_SITE_KEY or not HCAPTCHA_SECRET_KEY:
    key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hcaptcha_key')
    if os.path.exists(key_file):
        try:
            with open(key_file, 'r') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        if key == 'SITE_KEY' and not HCAPTCHA_SITE_KEY:
                            HCAPTCHA_SITE_KEY = value
                        elif key == 'SECRET_KEY' and not HCAPTCHA_SECRET_KEY:
                            HCAPTCHA_SECRET_KEY = value
        except Exception as e:
            print(f"Error loading hCaptcha keys from file: {e}")

# Set default test keys if still not found
if not HCAPTCHA_SITE_KEY:
    HCAPTCHA_SITE_KEY = '10000000-ffff-ffff-ffff-000000000001'
if not HCAPTCHA_SECRET_KEY:
    HCAPTCHA_SECRET_KEY = '0x0000000000000000000000000000000000000000'
