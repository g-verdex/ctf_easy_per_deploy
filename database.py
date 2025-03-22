import sqlite3
from config import DB_PATH

# Инициализация базы данных
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS containers (
                id TEXT PRIMARY KEY,
                port INTEGER,
                start_time INTEGER,
                expiration_time INTEGER,
                user_uuid TEXT
            )
        """)
        conn.commit()

# Функция для выполнения SQL-запросов
def execute_query(query, params=(), fetchone=False):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()
        return c.fetchone() if fetchone else c.fetchall()

# Удаление контейнера из БД
def remove_container_from_db(container_id):
    execute_query("DELETE FROM containers WHERE id = ?", (container_id,))
