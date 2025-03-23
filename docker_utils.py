import docker
import time
import threading
from config import PORT_IN_CONTAINER, PORT_RANGE
from database import execute_query, remove_container_from_db

client = docker.from_env()
used_ports = set()

# Проверка, свободен ли порт
def is_port_free(port):
    for container in client.containers.list():
        container_ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
        for port_binding in container_ports.get(f"{PORT_IN_CONTAINER}/tcp", []):
            if port_binding['HostPort'] == str(port):
                return False
    return True

# Получение свободного порта
def get_free_port():
    available_ports = list(set(PORT_RANGE) - used_ports)
    for port in available_ports:
        if is_port_free(port):
            used_ports.add(port)
            return port
    return None

# Автоматическое удаление контейнера после истечения времени жизни
def auto_remove_container(container_id, port):
    try:
        while True:
            # Получаем данные контейнера из базы данных
            container_data = execute_query("SELECT expiration_time FROM containers WHERE id = ?", (container_id,), fetchone=True)
            if not container_data:
                print(f"[ERROR] Container {container_id} not found in database. Stopping thread.")
                return  # Выходим из потока

            expiration_time = container_data[0]

            current_time = int(time.time())
            time_to_wait = expiration_time - current_time

            if time_to_wait <= 0:
                break  # Время истекло — удаляем контейнер

            print(f"[INFO] Container {container_id} will be checked again in 30 sec. Time left: {time_to_wait}s")
            time.sleep(min(time_to_wait, 30))  # Проверяем каждые 30 сек или до истечения времени

        print(f"[INFO] Removing container {container_id} due to expiration.")

        try:
            container = client.containers.get(container_id)
            container.remove(force=True)
            print(f"[SUCCESS] Container {container_id} removed.")
        except docker.errors.NotFound:
            print(f"[WARNING] Container {container_id} not found in Docker, but still in database.")

        used_ports.discard(port)

        execute_query("DELETE FROM containers WHERE id = ?", (container_id,))
        print(f"[SUCCESS] Container {container_id} removed from database.")

    except Exception as e:
        print(f"[ERROR] Unexpected error in auto_remove_container: {e}")