import os

# db_path = os.getenv('DB_PATH')
leave_time = int(os.getenv('LEAVE_TIME', 240))
add_time = int(os.getenv('ADD_TIME', 120))
images_name = os.getenv('IMAGES_NAME', "d1temnd/task_images_ozo:1.0.1")
port_in_container = int(os.getenv('PORT_IN_CONTAINER', '80'))
PORT_RANGE = range(int(os.getenv('START_RANGE', 9000)), int(os.getenv('STOP_RANGE', 10001)))


db_path = './containers.db'

# leave_time = 240  # Время жизни контейнера (сек)
# add_time = 120  # Время продления контейнера (сек)
# images_name = "d1temnd/task_images_ozo:1.0.1"
# port_in_container = "80"
# PORT_RANGE = range(9000, 10001)
