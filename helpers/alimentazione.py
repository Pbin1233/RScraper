import requests
import sqlite3
import time
from datetime import datetime, timedelta
import json

# API Endpoints
INTAKE_SUMMARY_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/testate/temporali/get"
INTAKE_DETAILS_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/parametri/alimentazione/list"

def get_timestamp():
    return str(int(time.time() * 1000))

def fetch_intake(patient_id, jwt_token):
    """Fetches both summary and detailed intake data for a patient."""
    
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    # Step 1: Fetch Weekly Summary
    print("📊 Fetching intake summary data...")
    fetch_intake_summary(patient_id, jwt_token, headers)

    # Step 2: Fetch Detailed Data
    print("📖 Fetching detailed intake data...")
    fetch_intake_details(patient_id, jwt_token, headers)

def fetch_intake_summary(patient_id, jwt_token, headers):
    """Fetches the intake summary (food & water) for the past few weeks."""
    
    params = {
        "_dc": get_timestamp(),
        "tipoTestata": "",
        "idRicovero": patient_id,
        "data": "2025-03-15T18:32:54",  # Use current timestamp in real-time
        "gap": 3,
        "page": 1,
        "start": 0,
        "limit": 25
    }

    response = requests.get(INTAKE_SUMMARY_URL, headers=headers, params=params, verify=False)

    if response.status_code == 401:
        print("🔄 Token expired during intake summary fetch. Refreshing...")
        from helpers.auth import refresh_jwt_token
        jwt_token = refresh_jwt_token()
        headers["CBA-JWT"] = f"Bearer {jwt_token}"
        response = requests.get(INTAKE_SUMMARY_URL, headers=headers, params=params, verify=False)
    
    if response.status_code == 200:
        data = response.json()
        if "data" in data and data["data"]:
            save_intake(patient_id, data["data"])
        else:
            print(f"🚨 No intake summary found for patient {patient_id}")
    else:
        print(f"⚠️ Error fetching intake summary! Status Code: {response.status_code}")


def fetch_intake_details(patient_id, jwt_token, headers):
    from datetime import datetime, timedelta
    import json

    current_date = datetime.now()

    while True:
        iso_date = current_date.isoformat(timespec='seconds') + "+01:00"

        params = {
            "_dc": get_timestamp(),
            "idRicovero": patient_id,
            "data": iso_date,
            "page": 1,
            "start": 0,
            "limit": 25,
            "group": '{"property":"giornoDellaSettimana","direction":"ASC"}'
        }

        print(f"\n📅 Fetching data for week starting {current_date.date()}...")

        response = requests.get(INTAKE_DETAILS_URL, headers=headers, params=params, verify=False)

        if response.status_code == 401:
            print("🔄 Token expired during intake detail fetch. Refreshing...")
            from helpers.auth import refresh_jwt_token
            jwt_token = refresh_jwt_token()
            headers["CBA-JWT"] = f"Bearer {jwt_token}"
            continue

        print(f"📦 Raw response ({response.status_code}):")
        try:
            data = response.json()
            print(json.dumps(data, indent=2)[:1000])
        except Exception as e:
            print("❌ Failed to parse JSON:", e)
            break

        if response.status_code == 200:
            entries = data.get("data", [])

            # ⛔ Stop if all entries are placeholders
            all_placeholders = all(
                e.get("id", 0) == -10000 or e.get("nominativo") is None
                for e in entries
            )

            if not entries or all_placeholders:
                print(f"📭 No real data found for {current_date.date()}. Stopping fetch.")
                break

            save_intake(patient_id, entries)
            current_date -= timedelta(days=7)
        else:
            print(f"⚠️ Error fetching data: {response.status_code}")
            break

def save_intake(patient_id, intake_data):
    """Saves food and water intake data into the SQLite database with more detail."""

    conn = sqlite3.connect("borromea.db")
    cursor = conn.cursor()

    for entry in intake_data:
        # 🚫 Skip placeholder data
        entry_id = entry.get("id")
        if entry_id is None or entry_id < 1000:
            continue

        intake_entry = {
                "patient_id": patient_id,
                "idRicovero": entry.get("idRicovero"),
                "data": entry.get("data"),
                "tipo": entry.get("tipo", "UNKNOWN"),
                "quantita": entry.get("quantita", 0),
                "tipoRecord": entry.get("tipoRecord", ""),
                "compilatore": entry.get("compilatore"),
                "compilatoreNominativo": entry.get("compilatoreNominativo", ""),
                "compilatoreFigProf": entry.get("compilatoreFigProf", ""),
                "giornoDellaSettimana": entry.get("giornoDellaSettimana", -1),
                "nomeIcona": entry.get("nomeIcona", ""),
                "oraConvalida": entry.get("oraConvalida", ""),
                "convalidato": 1 if entry.get("convalidato") else 0,
                "note": entry.get("note"),
                "bozza": 1 if entry.get("bozza") else 0,
                "regAnnullate": 1 if entry.get("regAnnullate") else 0,
                "tipoBlocco": json.dumps(entry.get("tipoBlocco", [])),
                "permessiAnnulla": json.dumps(entry.get("permessiAnnulla", [])),
                "codEnte": entry.get("codEnte"),
                "hashAnnulla": entry.get("hashAnnulla"),
                "deletedData": entry.get("deletedData"),
                "id": entry.get("id"),  # the unique record id
                "nominativo": entry.get("nominativo"),
            }

        columns = ", ".join(intake_entry.keys())
        placeholders = ", ".join(["?" for _ in intake_entry])
        values = tuple(intake_entry.values())

        cursor.execute(f"""
            INSERT OR REPLACE INTO intake ({columns})
            VALUES ({placeholders});
        """, values)

    conn.commit()
    conn.close()
    print(f"✅ Intake data for patient {patient_id} saved successfully!")

