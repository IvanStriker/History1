import csv
import psycopg2


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


if __name__ == "__main__":
    seed()