import sqlite3
from config import config

def get_container_by_user_uuid(user_uuid):
    with sqlite3.connect(config.DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id, port, expiration_time FROM containers WHERE user_uuid = ?", (user_uuid,))
        return c.fetchone()
        
def insert_container(container_id, port, start_time, expiration_time, user_uuid):
    with sqlite3.connect(config.DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO containers (id, port, start_time, expiration_time, user_uuid)
            VALUES (?, ?, ?, ?, ?)
        """, (container_id, port, start_time, expiration_time, user_uuid))
        conn.commit()

def delete_container(container_id):
    with sqlite3.connect(config.DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM containers WHERE id = ?", (container_id,))
        conn.commit()

def update_container_expiration_time(container_id, new_expiration_time):
    with sqlite3.connect(config.DB_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE containers SET expiration_time = ? WHERE id = ?", (new_expiration_time, container_id))
        conn.commit()
