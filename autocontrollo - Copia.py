import sqlite3
from datetime import datetime, timedelta

# Connect to the database
conn = sqlite3.connect("borromea.db")
cursor = conn.cursor()

# Configuration
MAX_DIFF_DAYS = 30.5*6+14  # ~6 months
DO_CHECK_generale_1 = True    # Interval between PAI/PI
DO_CHECK_generale_2_1 = True    # First PAI/PI within 30 days of DAL
VERBOSE = True  # Set to True to show successful check results

# === SETUP: Loop through ospiti and ricoveri ===

# Get all unique patients
cursor.execute("SELECT DISTINCT codOspite FROM personal_data")
ospiti = [row[0] for row in cursor.fetchall()]

for cod_ospite in ospiti:
    # For each ospite, get all ricoveri with name and surname
    cursor.execute("""
        SELECT ricovero_id, nome, cognome
        FROM personal_data
        WHERE codOspite = ? AND ricovero_id IS NOT NULL
    """, (cod_ospite,))
    ricoveri = cursor.fetchall()

    for ricovero_id, nome, cognome in ricoveri:
        # Print the analysis header for this specific ricovero
        print(f"\n📌 Checking: {cognome.upper()} {nome} (idRicoveroCU: {ricovero_id})")

        # === All the following checks will use this ricovero_id ===
        # You can now start with CHECK Generale 1 here.

    # === CHECK generale_1 ===

    # Get DAL for this ricovero from hospitalizations_history
    cursor.execute("SELECT dal FROM hospitalizations_history WHERE idRicoveroCU = ?", (ricovero_id,))
    dal_row = cursor.fetchone()
    if not dal_row or not dal_row[0]:
        print(f"⚠️ No DAL found for ricovero_id {ricovero_id}, skipping checks.")
        continue

    dal_str = dal_row[0]
    try:
        data_dal = datetime.strptime(dal_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        data_dal = datetime.strptime(dal_str, "%Y-%m-%d")

    any_issues = False  # Reset issue tracker for this ricovero

    # Load PAI and PI dates for this ricovero
    cursor.execute("SELECT DISTINCT data FROM pai WHERE patient_id = ?", (ricovero_id,))
    pai_dates = sorted([
        datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        for row in cursor.fetchall() if row[0]
    ])

    cursor.execute("SELECT DISTINCT data FROM pi WHERE patient_id = ?", (ricovero_id,))
    pi_dates = sorted([
        datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        for row in cursor.fetchall() if row[0]
    ])

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



    # === CHECK generale_2.1 ===
    if DO_CHECK_generale_2_1:
        if data_dal < datetime(2022, 2, 1):
            print(f"⚠️ [Check Generale 2.1] Hospitalization started before PI/PAI system (DAL = {data_dal.date()}) — skipping Check 2.1")
        else:
            passed_all = True
            if pai_dates:
                delta = (pai_dates[0] - data_dal).days
                if delta > 30:
                    print(f"❌ [Check Generale 2.1] First PAI too late: {pai_dates[0].date()} ({delta} days after DAL)")
                    any_issues = True
                    passed_all = False
            if pi_dates:
                delta = (pi_dates[0] - data_dal).days
                if delta > 30:
                    print(f"❌ [Check Generale 2.1] First PI too late: {pi_dates[0].date()} ({delta} days after DAL)")
                    any_issues = True
                    passed_all = False
            if VERBOSE and passed_all:
                print("✅ [Check Generale 2.1] First PAI and PI within 30 days of DAL")


    # === CHECK Cadute 1.1 ===
    if pai_dates:
        passed_all = True
        for pai_date in pai_dates:
            start_window = pai_date - timedelta(days=10)
            end_window = pai_date

            cursor.execute("""
                SELECT COUNT(*) FROM tinetti
                WHERE patient_id = ? AND data BETWEEN ? AND ?
            """, (patient_id, start_window.strftime("%Y-%m-%d %H:%M:%S"), end_window.strftime("%Y-%m-%d %H:%M:%S")))
            tinetti_count = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(*) FROM conley
                WHERE patient_id = ? AND data BETWEEN ? AND ?
            """, (patient_id, start_window.strftime("%Y-%m-%d %H:%M:%S"), end_window.strftime("%Y-%m-%d %H:%M:%S")))
            conley_count = cursor.fetchone()[0]

            if tinetti_count == 0 and conley_count == 0:
                print(f"❌ [Check Cadute 1.1] No Tinetti or Conley for the PAI on {pai_date.date()}")
                any_issues = True
                passed_all = False
        if VERBOSE and passed_all:
            print("✅ [Check Cadute 1.1] At least one Tinetti or Conley found for all PAI")

    # === CHECK Contenzioni 2.1 ===
    DEBUG = True

    def normalize_code(code):
        return code.replace(";", "").strip()

    # Load mapping of code → description
    cursor.execute("SELECT inputValueInt, descrizione FROM dispositivi_contenzione")
    contenzione_map = {str(row[0]): row[1] for row in cursor.fetchall()}
    if DEBUG:
        print("DEBUG: Mapping of codes to description:", contenzione_map)

    cursor.execute("SELECT DISTINCT patient_id FROM contenzioni")
    patient_ids_contenzioni = [row[0] for row in cursor.fetchall()]
    if DEBUG:
        print("DEBUG: Found patient_ids in contenzioni:", patient_ids_contenzioni)

    for patient_id in patient_ids_contenzioni:
        # Get ricovero_id from personal_data
        cursor.execute("SELECT ricovero_id FROM personal_data WHERE id = ?", (patient_id,))
        pd_row = cursor.fetchone()
        if not pd_row:
            if DEBUG:
                print(f"DEBUG: No ricovero_id found in personal_data for patient {patient_id}")
            continue
        ricovero_id = pd_row[0]
        if DEBUG:
            print(f"DEBUG: Processing patient {patient_id} (ricovero_id = {ricovero_id})")

        # Load contenzioni for this patient
        cursor.execute("""
            SELECT dataInizio, mezziContenzione
            FROM contenzioni
            WHERE patient_id = ?
        """, (patient_id,))
        rows = cursor.fetchall()
        if DEBUG:
            print(f"DEBUG: Found {len(rows)} contenzioni rows for patient {patient_id}")

        first_use_by_type = {}
        for data_inizio, mezzi in rows:
            if not data_inizio or not mezzi:
                continue
            if DEBUG:
                print(f"DEBUG: Processing row: dataInizio = {data_inizio}, mezziContenzione = {mezzi}")
            try:
                dt = datetime.strptime(data_inizio, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                dt = datetime.strptime(data_inizio, "%Y-%m-%d")
            codes = [normalize_code(c) for c in mezzi.split(",") if normalize_code(c)]
            if DEBUG:
                print("DEBUG: Normalized codes from row:", codes)
            for code in codes:
                if code not in first_use_by_type or dt < first_use_by_type[code]:
                    first_use_by_type[code] = dt

        if DEBUG:
            readable_first_use = {k: v.strftime("%Y-%m-%d") for k, v in first_use_by_type.items()}
            print("DEBUG: First use by type for patient", patient_id, ":", readable_first_use)

        for code, dt in sorted(first_use_by_type.items(), key=lambda x: x[1]):
            data_str = dt.strftime("%Y-%m-%d")
            desc = contenzione_map.get(code, f"(Unknown {code})")
            if DEBUG:
                print(f"DEBUG: Checking code {code} ({desc}) with earliest date {data_str}")

            cursor.execute("""
                SELECT testoDiario FROM diario_medico
                WHERE idRicovero = ? AND DATE(dataOra) = ?
            """, (ricovero_id, data_str))
            diario_entries = [r[0] for r in cursor.fetchall()]
            if DEBUG:
                print(f"DEBUG: Diario entries for ricovero {ricovero_id} on {data_str}:", diario_entries)

            if not any("contenzion" in (entry or "").lower() for entry in diario_entries):
                print(f"❌ [Check Contenzioni 2.1] New contenzione: {desc} (code {code}) on {data_str} not justified in diario medico")
            elif VERBOSE:
                print(f"✅ [Check Contenzioni 2.1] New contenzione: {desc} (code {code}) justified on {data_str}")

    # === CHECK Dolore 3.1 ===
    if pai_dates:
        passed_all = True
        for pai_date in pai_dates:
            start_window = pai_date - timedelta(days=10)
            end_window = pai_date

            cursor.execute("""
                SELECT COUNT(*) FROM nrs
                WHERE patient_id = ? AND data BETWEEN ? AND ?
            """, (patient_id, start_window.strftime("%Y-%m-%d %H:%M:%S"), end_window.strftime("%Y-%m-%d %H:%M:%S")))
            nrs_count = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(*) FROM painad
                WHERE patient_id = ? AND data BETWEEN ? AND ?
            """, (patient_id, start_window.strftime("%Y-%m-%d %H:%M:%S"), end_window.strftime("%Y-%m-%d %H:%M:%S")))
            painad_count = cursor.fetchone()[0]

            if nrs_count == 0 and painad_count == 0:
                print(f"❌ [Check Dolore 3.1] No NRS or PAINAD for the PAI on {pai_date.date()}")
                any_issues = True
                passed_all = False
        if VERBOSE and passed_all:
            print("✅ [Check Dolore 3.1] At least one NRS or PAINAD found for all PAI")

    # === CHECK LDP 4.1 ===
    if pai_dates:
        passed_all = True
        for pai_date in pai_dates:
            start_window = pai_date - timedelta(days=10)
            end_window = pai_date

            cursor.execute("""
                SELECT COUNT(*) FROM braden
                WHERE patient_id = ? AND data BETWEEN ? AND ?
            """, (patient_id, start_window.strftime("%Y-%m-%d %H:%M:%S"), end_window.strftime("%Y-%m-%d %H:%M:%S")))
            braden_count = cursor.fetchone()[0]

            if braden_count == 0:
                print(f"❌ [Check LDP 4.1] No Braden scale recorded for the PAI on {pai_date.date()}")
                any_issues = True
                passed_all = False
        if VERBOSE and passed_all:
            print("✅ [Check LDP 4.1] At least one Braden found for all PAI")

    # === CHECK Attività motoria 8 ===
    cursor.execute("""
        SELECT DISTINCT dataOra FROM diario_riabilitativo
        WHERE patient_id = ?
        ORDER BY dataOra ASC
    """, (patient_id,))
    rehab_dates = [
        datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        for row in cursor.fetchall() if row[0]
    ]

    if rehab_dates:
        passed_all = True
        for i in range(1, len(rehab_dates)):
            delta = (rehab_dates[i] - rehab_dates[i - 1]).days
            if delta > 35:
                print(f"❌ [Check Attività Motoria 8] Rehab entries too far apart: {rehab_dates[i-1].date()} → {rehab_dates[i].date()} = {delta} days")
                any_issues = True
                passed_all = False
        if VERBOSE and passed_all:
            print("✅ [Check Attività Motoria 8] All rehab entries ≤ 35 days apart")


    # Optional: clean output if all is good
    if not any_issues:
        print("✅ All checks passed.")
    
conn.close()
