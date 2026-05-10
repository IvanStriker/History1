import csv
import psycopg2
from werkzeug.security import generate_password_hash


CSV_FILE = "db.csv"

DB_CONFIG = {
    "host": "db",
    "port": 5432,
    "dbname": "appdb",
    "user": "user",
    "password": "pass",
}


def seed():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM cards")
    if cur.fetchone()[0] > 0:
        print("Already seeded, skipping")
        cur.close()
        conn.close()
        return

    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        rows = []

        for row in reader:
            rows.append((
                row["category"],
                row.get("front_type", "text"),
                row["front_content"],
                row.get("back_type", "text"),
                row["back_content"],
                row["answer_text"],
            ))

    query = """
        INSERT INTO cards (
            category,
            front_type,
            front_content,
            back_type,
            back_content,
            answer_text
        )
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    cur.executemany(query, rows)

    conn.commit()
    cur.close()
    conn.close()

    print(f"Inserted {len(rows)} rows")


def seed_admin():
    """Create an admin user (Admin / 11111111) if none exists."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users WHERE is_admin = true")
    if cur.fetchone()[0] > 0:
        print("Admin already exists, skipping")
        cur.close()
        conn.close()
        return

    hashed = generate_password_hash("11111111")
    cur.execute(
        "INSERT INTO users (first_name, last_name, username, email, password, bio, is_admin) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        ("Admin", "1", "Admin", "admin@example.com", hashed, "Администратор", True),
    )
    conn.commit()
    cur.close()
    conn.close()
    print("Admin user created.")


if __name__ == "__main__":
    seed()
    seed_admin()