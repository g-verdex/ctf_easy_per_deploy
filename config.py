import os

class Config:
    DB_PATH = './containers.db'
    LEAVE_TIME = 240  # Время жизни контейнера в секундах
    ADD_TIME = 120  # Время добавления в секундах
    IMAGE_NAME = "docker images"
    PORT_IN_CONTAINER = "80"
    PORT_RANGE = range(9000, 10001)
    USED_PORTS = set()
    PORT_START_SERVIS = 5000

config = Config
