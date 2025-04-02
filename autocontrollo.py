import sqlite3
from datetime import datetime, timedelta

# Connect to the database
conn = sqlite3.connect("borromea.db")
cursor = conn.cursor()

# Configuration
MAX_DIFF_DAYS = 30.5*6+14  # ~6 months
DO_CHECK_generale_1 = True    # Interval between PAI/PI
DO_CHECK_generale_2_1 = True    # First PAI/PI within 30 days of DAL

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

    any_issues = False  # track if we show any failures

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

    # === CHECK generale_1 ===
    if DO_CHECK_generale_1:
        for i in range(1, len(pai_dates)):
            delta = (pai_dates[i] - pai_dates[i - 1]).days
            if delta > MAX_DIFF_DAYS:
                print(f"❌ [Check Generale 1] PAI interval too long: {pai_dates[i-1].date()} → {pai_dates[i].date()} = {delta} days")
                any_issues = True

        for i in range(1, len(pi_dates)):
            delta = (pi_dates[i] - pi_dates[i - 1]).days
            if delta > MAX_DIFF_DAYS:
                print(f"❌ [Check Generale 1] PI interval too long: {pi_dates[i-1].date()} → {pi_dates[i].date()} = {delta} days")
                any_issues = True

    # === CHECK generale_2.1 ===
    if DO_CHECK_generale_2_1:
        if data_dal < datetime(2022, 2, 1):
            print(f"⚠️  [Check Generale 2.1] Hospitalization started before PI/PAI system (DAL = {data_dal.date()}) — skipping Check 2.1")
        else:
            if pai_dates:
                delta = (pai_dates[0] - data_dal).days
                if delta > 30:
                    print(f"❌ [Check Generale 2.1] First PAI too late: {pai_dates[0].date()} ({delta} days after DAL)")
                    any_issues = True
            if pi_dates:
                delta = (pi_dates[0] - data_dal).days
                if delta > 30:
                    print(f"❌ [Check Generale 2.1] First PI too late: {pi_dates[0].date()} ({delta} days after DAL)")
                    any_issues = True

    # === CHECK Cadute 1.1 ===
    if pai_dates:
        for pai_date in pai_dates:
            start_window = pai_date - timedelta(days=20)
            end_window = pai_date + timedelta(days=2)

            # Check Tinetti
            cursor.execute("""
                SELECT COUNT(*) FROM tinetti
                WHERE patient_id = ? AND data BETWEEN ? AND ?
            """, (patient_id, start_window.strftime("%Y-%m-%d %H:%M:%S"), end_window.strftime("%Y-%m-%d %H:%M:%S")))
            tinetti_count = cursor.fetchone()[0]

            # Check Conley
            cursor.execute("""
                SELECT COUNT(*) FROM conley
                WHERE patient_id = ? AND data BETWEEN ? AND ?
            """, (patient_id, start_window.strftime("%Y-%m-%d %H:%M:%S"), end_window.strftime("%Y-%m-%d %H:%M:%S")))
            conley_count = cursor.fetchone()[0]

            if tinetti_count == 0 and conley_count == 0:
                print(f"❌ [Check Cadute 1.1] No Tinetti or Conley for the PAI on {pai_date.date()}")
                any_issues = True

    # === CHECK Dolore 3.1 ===
    if pai_dates:
        for pai_date in pai_dates:
            start_window = pai_date - timedelta(days=20)
            end_window = pai_date + timedelta(days=2)

            # Check NRS
            cursor.execute("""
                SELECT COUNT(*) FROM nrs
                WHERE patient_id = ? AND data BETWEEN ? AND ?
            """, (patient_id, start_window.strftime("%Y-%m-%d %H:%M:%S"), end_window.strftime("%Y-%m-%d %H:%M:%S")))
            nrs_count = cursor.fetchone()[0]

            # Check PAINAD
            cursor.execute("""
                SELECT COUNT(*) FROM painad
                WHERE patient_id = ? AND data BETWEEN ? AND ?
            """, (patient_id, start_window.strftime("%Y-%m-%d %H:%M:%S"), end_window.strftime("%Y-%m-%d %H:%M:%S")))
            painad_count = cursor.fetchone()[0]

            if nrs_count == 0 and painad_count == 0:
                print(f"❌ [Check Dolore 3.1] No NRS or PAINAD for the PAI on {pai_date.date()}")
                any_issues = True

    # Optional: clean output if all is good
    if not any_issues:
        print("✅ All checks passed.")
    
conn.close()
