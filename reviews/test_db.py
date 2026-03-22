from db import init_db, get_connection

init_db()

with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT NOW() AS now_time")
        row = cur.fetchone()
        print("DB OK:", row)