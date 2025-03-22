import os

LEAVE_TIME = int(os.getenv('LEAVE_TIME', 240))
ADD_TIME = int(os.getenv('ADD_TIME', 120))
IMAGES_NAME = os.getenv('IMAGES_NAME', "d1temnd/task_images_ozo:1.0.1")
FLAG = os.getenv('FLAG', 'test_flag{}')
PORT_IN_CONTAINER = int(os.getenv('PORT_IN_CONTAINER', '80'))
PORT_RANGE = range(int(os.getenv('START_RANGE', 9000)), int(os.getenv('STOP_RANGE', 10001)))
DB_PATH = './containers.db'

# leave_time = 240  # Время жизни контейнера (сек)
# add_time = 120  # Время продления контейнера (сек)
# images_name = "d1temnd/task_images_ozo:1.0.1"
# port_in_container = "80"
# PORT_RANGE = range(9000, 10001)
