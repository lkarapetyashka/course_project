from app.database import get_connection
from config import SCHEMA_PATH, SEED_PATH


def init_db():
    connection = get_connection()
    cursor = connection.cursor()

    with open(SCHEMA_PATH, "r", encoding="utf-8") as file:
        cursor.executescript(file.read())

    connection.commit()
    connection.close()

def seed_db():
    connection = get_connection()
    cursor = connection.cursor()

    with open(SEED_PATH, "r", encoding="utf-8") as file:
        cursor.executescript(file.read())


    connection.commit()
    connection.close()

if __name__ == "__main__":
    init_db()
    seed_db()