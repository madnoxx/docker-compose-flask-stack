from flask import Flask
import redis
import psycopg2
import os
import time
import sys

app = Flask(__name__)

# Настройки Redis
redis_host = "redis"
redis_port = int(os.getenv("REDIS_PORT", 6379))

# Настройки Postgres
db_host = "db"
db_user = os.getenv("POSTGRES_USER")
db_pass = os.getenv("POSTGRES_PASSWORD")
db_name = os.getenv("POSTGRES_DB")

# Проверка Postgres с таймаутом
timeout = 60  # секунд
start_time = time.time()
conn = None

while True:
    try:
        conn = psycopg2.connect(
            host=db_host,
            user=db_user,
            password=db_pass,
            dbname=db_name
        )
        print("Postgres готов, продолжаем!")
        break
    except psycopg2.OperationalError as e:
        elapsed = int(time.time() - start_time)
        if elapsed > timeout:
            print("Не удалось подключиться к Postgres за", timeout, "секунд.")
            print("Ошибка:", e)
            sys.exit(1)
        print(f"Postgres не готов ({elapsed}s), ждём 2 секунды...")
        time.sleep(2)

# Проверка Redis
r = None
try:
    r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
    r.ping()
    print("Redis готов!")
except redis.exceptions.ConnectionError as e:
    print("Ошибка подключения к Redis:", e)
    # можно решать: либо sys.exit(1), либо продолжить без кэша

@app.route("/")
def index():
    hits = 0
    visits_count = 0

    # Redis
    if r:
        try:
            r.incr("hits")
            hits = r.get("hits")
        except Exception as e:
            print("Ошибка работы с Redis:", e)

    # Postgres
    try:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS visits (count INT);")
        cur.execute("INSERT INTO visits (count) VALUES (%s);", (int(hits),))
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM visits;")
        visits_count = cur.fetchone()[0]
    except Exception as e:
        print("Ошибка работы с Postgres:", e)

    return f"Hits: {hits}, Total visits records in Postgres: {visits_count}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
