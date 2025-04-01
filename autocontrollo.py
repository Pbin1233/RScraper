import sqlite3
from datetime import datetime

# Connect to the database
conn = sqlite3.connect("borromea.db")
cursor = conn.cursor()

# Configuration
MAX_DIFF_DAYS = 30.5*6+14  # ~6 months
DO_CHECK_1 = True    # Interval between PAI/PI
DO_CHECK_2 = True    # First PAI/PI within 30 days of DAL

# Get all patient IDs that have both PAI and PI
cursor.execute("""
    SELECT DISTINCT pai.patient_id
    FROM pai
    INNER JOIN pi ON pai.patient_id = pi.patient_id
""")
patient_ids = [row[0] for row in cursor.fetchall()]

for patient_id in patient_ids:
    # Get hospitalization start (dal) and codOspite
    cursor.execute("""
        SELECT h.dal, h.codOspite
        FROM hospitalizations_history h
        WHERE h.id = ?
        LIMIT 1
    """, (patient_id,))
    row = cursor.fetchone()

    if not row:
        print(f"\n📌 Checking patient_id: {patient_id} (not found in hospitalizations_history)")
        continue

    dal_str, cod_ospite = row

    try:
        data_dal = datetime.strptime(dal_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        data_dal = datetime.strptime(dal_str, "%Y-%m-%d")

    # Try to get name
    if cod_ospite:
        cursor.execute("SELECT nome, cognome FROM patients WHERE codOspite = ?", (cod_ospite,))
        name_row = cursor.fetchone()
    else:
        name_row = None

    if name_row and all(name_row):
        nome, cognome = name_row
        print(f"\n📌 Checking: {cognome.upper()} {nome.upper()} (idRicoveroCU: {patient_id})")
    else:
        print(f"\n📌 Checking patient_id: {patient_id} (name not found)")

    # Load PAI and PI dates
    cursor.execute("SELECT DISTINCT data FROM pai WHERE patient_id = ?", (patient_id,))
    pai_dates = sorted([
        datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        for row in cursor.fetchall() if row[0]
    ])

    cursor.execute("SELECT DISTINCT data FROM pi WHERE patient_id = ?", (patient_id,))
    pi_dates = sorted([
        datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        for row in cursor.fetchall() if row[0]
    ])

    # CHECK 1: Interval between each successive PAI and PI
    if DO_CHECK_1:
        for i in range(1, len(pai_dates)):
            delta = (pai_dates[i] - pai_dates[i - 1]).days
            if delta > MAX_DIFF_DAYS:
                print(f"[PAI] Interval too long: {pai_dates[i-1].date()} → {pai_dates[i].date()} = {delta} days")

        for i in range(1, len(pi_dates)):
            delta = (pi_dates[i] - pi_dates[i - 1]).days
            if delta > MAX_DIFF_DAYS:
                print(f"[PI ] Interval too long: {pi_dates[i-1].date()} → {pi_dates[i].date()} = {delta} days")

    # CHECK 2: First PAI and PI must be within 30 days of hospitalization start
    if DO_CHECK_2:
        if pai_dates:
            delta = (pai_dates[0] - data_dal).days
            if delta > 30:
                print(f"[PAI] First PAI too late: {pai_dates[0].date()} ({delta} days after DAL)")
        if pi_dates:
            delta = (pi_dates[0] - data_dal).days
            if delta > 30:
                print(f"[PI ] First PI too late: {pi_dates[0].date()} ({delta} days after DAL)")

conn.close()
