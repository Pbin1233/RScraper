import requests
import sqlite3
import time
from datetime import datetime
import json

# API Endpoints
WEEK_LIST_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/testate/temporali/get"
INTAKE_DETAILS_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/parametri/alimentazione/list"

def get_timestamp():
    return str(int(time.time() * 1000))

def fetch_all_intake_weeks(patient_id, jwt_token):
    print(f"\n🚀 Fetching all alimentation weeks for patient {patient_id}")
    weeks = fetch_week_list(patient_id, jwt_token)

    if not weeks:
        print("❌ No week data available.")
        return

    for week in weeks:
        inizio_range = week.get("inizioRange")
        fine_range = week.get("fineRange")
        print(f"➡️ Found week: {inizio_range} → {fine_range}")
        ...


def fetch_week_list(patient_id, jwt_token):
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    params = {
        "_dc": get_timestamp(),
        "tipoTestata": "AlimentazioneIdratazione",
        "idRicovero": patient_id,
        "gap": 3,
        "page": 1,
        "start": 0,
        "limit": 100
    }

    print(f"\n🔍 Requesting week list for idRicovero {patient_id}")
    print("🔗 URL:", WEEK_LIST_URL)
    print("📦 Params:", json.dumps(params, indent=2))

    response = requests.get(WEEK_LIST_URL, headers=headers, params=params, verify=False)

    print(f"📥 Response status: {response.status_code}")

    if response.status_code == 401:
        raise requests.exceptions.HTTPError("Token expired", response=response)

    if response.status_code != 200:
        print(f"⚠️ Error fetching week list: {response.status_code}")
        return []

    try:
        data = response.json().get("data", [])
        print(f"📊 Week entries received: {len(data)}")
        if data:
            print("📅 Example week:", json.dumps(data[0], indent=2))
        return data
    except Exception as e:
        print(f"❌ Failed to parse week list JSON: {e}")
        return []

def fetch_week_data(patient_id, inizio_range, jwt_token):
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    date_with_offset = inizio_range + "+01:00"
    params = {
        "_dc": get_timestamp(),
        "idRicovero": patient_id,
        "data": date_with_offset,
        "page": 1,
        "start": 0,
        "limit": 25,
        "group": '{"property":"giornoDellaSettimana","direction":"ASC"}'
    }

    response = requests.get(INTAKE_DETAILS_URL, headers=headers, params=params, verify=False)

    if response.status_code == 401:
        raise requests.exceptions.HTTPError("Token expired", response=response)
    if response.status_code != 200:
        print(f"⚠️ Error fetching data for {inizio_range[:10]}: {response.status_code}")
        return []

    try:
        return response.json().get("data", [])
    except Exception as e:
        print(f"❌ Failed to parse intake JSON: {e}")
        return []

def save_intake(patient_id, intake_data):
    conn = sqlite3.connect("borromea.db")
    cursor = conn.cursor()

    for entry in intake_data:
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
            "id": entry.get("id"),
            "nominativo": entry.get("nominativo")
        }

        columns = ", ".join(intake_entry.keys())
        placeholders = ", ".join(["?"] * len(intake_entry))
        values = tuple(intake_entry.values())

        cursor.execute(f"""
            INSERT OR REPLACE INTO intake ({columns})
            VALUES ({placeholders})
        """, values)

    conn.commit()
    conn.close()
    print(f"✅ Intake data for patient {patient_id} saved successfully!")
