import sqlite3
from datetime import datetime

# Connect to the database
conn = sqlite3.connect("borromea.db")
cursor = conn.cursor()

MAX_DIFF_DAYS = 30.5*6+14  # ~6 months

# Get all patient IDs that have at least one PAI and one PI
cursor.execute("""
    SELECT DISTINCT pai.patient_id
    FROM pai
    INNER JOIN pi ON pai.patient_id = pi.patient_id
""")
patient_ids = [row[0] for row in cursor.fetchall()]

for patient_id in patient_ids:
    print(f"\n📌 Checking patient_id: {patient_id}")

    # --- PAI ---
    cursor.execute("SELECT DISTINCT data FROM pai WHERE patient_id = ?", (patient_id,))
    pai_dates = sorted([
        datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        for row in cursor.fetchall() if row[0]
    ])

    for i in range(1, len(pai_dates)):
        diff = (pai_dates[i] - pai_dates[i - 1]).days
        if diff > MAX_DIFF_DAYS:
            print(f"[PAI] Interval too long: {pai_dates[i-1].date()} → {pai_dates[i].date()} = {diff} days")

    # --- PI ---
    cursor.execute("SELECT DISTINCT data FROM pi WHERE patient_id = ?", (patient_id,))
    pi_dates = sorted([
        datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        for row in cursor.fetchall() if row[0]
    ])

    for i in range(1, len(pi_dates)):
        diff = (pi_dates[i] - pi_dates[i - 1]).days
        if diff > MAX_DIFF_DAYS:
            print(f"[PI ] Interval too long: {pi_dates[i-1].date()} → {pi_dates[i].date()} = {diff} days")

conn.close()
