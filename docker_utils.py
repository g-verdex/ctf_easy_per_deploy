import time
import docker
import sqlite3
from config import config

client = docker.from_env()

def auto_remove_container(container_id, port):
    try:
        while True:
            with sqlite3.connect(config.DB_PATH) as conn:
                c = conn.cursor()
                c.execute("SELECT expiration_time FROM containers WHERE id = ?", (container_id,))
                container_data = c.fetchone()
                if not container_data:
                    print(f"[ERROR] Container {container_id} not found in database. Stopping thread.")
                    return  # Выходим из потока

                expiration_time = container_data[0]

            current_time = int(time.time())
            time_to_wait = expiration_time - current_time

            if time_to_wait <= 0:
                break  # Время истекло — удаляем контейнер

            print(f"[INFO] Container {container_id} will be checked again in 30 sec. Time left: {time_to_wait}s")
            time.sleep(min(time_to_wait, 30))  # Проверяем каждые 30 сек

        print(f"[INFO] Removing container {container_id} due to expiration.")

        try:
            container = client.containers.get(container_id)
            container.remove(force=True)
            print(f"[SUCCESS] Container {container_id} removed.")
        except docker.errors.NotFound:
            print(f"[WARNING] Container {container_id} not found in Docker, but still in database.")

        config.USED_PORTS.discard(port)

        with sqlite3.connect(config.DB_PATH) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM containers WHERE id = ?", (container_id,))
            conn.commit()
            print(f"[SUCCESS] Container {container_id} removed from database.")
    except Exception as e:
        print(f"[ERROR] Unexpected error in auto_remove_container: {e}")
