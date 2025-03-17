import docker
import time
import threading
from config import port_in_container, PORT_RANGE
from database import execute_query, remove_container_from_db

client = docker.from_env()
used_ports = set()

# Проверка, свободен ли порт
def is_port_free(port):
    for container in client.containers.list():
        container_ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
        for port_binding in container_ports.get(f"{port_in_container}/tcp", []):
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
            expiration_time = execute_query(
                "SELECT expiration_time FROM containers WHERE id = ?", (container_id,), fetchone=True
            )
            if not expiration_time:
                print(f"[ERROR] Container {container_id} not found in database.")
                return
            
            current_time = int(time.time())
            time_to_wait = expiration_time[0] - current_time

            if time_to_wait <= 0:
                break

            time.sleep(min(time_to_wait, 30))

        print(f"[INFO] Removing container {container_id}.")
        try:
            container = client.containers.get(container_id)
            container.remove(force=True)
        except docker.errors.NotFound:
            print(f"[WARNING] Container {container_id} not found.")

        used_ports.discard(port)
        remove_container_from_db(container_id)

    except Exception as e:
        print(f"[ERROR] Unexpected error in auto_remove_container: {e}")
