import os

# db_path = os.getenv('DB_PATH')
leave_time = int(os.getenv('LEAVE_TIME'))
add_time = int(os.getenv('ADD_TIME'))
images_name = os.getenv('IMAGES_NAME')
port_in_container = int(os.getenv('PORT_IN_CONTAINER'))
PORT_RANGE = range(int(os.getenv('START_RANGE')), int(os.getenv('STOP_RANGE')))


db_path = './containers.db'

# leave_time = 240  # Время жизни контейнера (сек)
# add_time = 120  # Время продления контейнера (сек)
# images_name = "d1temnd/task_images_ozo:1.0.1"
# port_in_container = "80"
# PORT_RANGE = range(9000, 10001)
