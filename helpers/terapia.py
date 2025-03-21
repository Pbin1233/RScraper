import requests
import json
import sqlite3
import time

# API Endpoint
MEDICATIONS_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/terapie/presc/src"

def get_timestamp():
    return str(int(time.time() * 1000))

def fetch_medications(patient_id, jwt_token):
    """Fetches both active and historical medications for a given patient and saves them in the database."""
    
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    # Fetch active medications
    print("💊 Fetching active medications...")
    fetch_medications_by_type(patient_id, jwt_token, headers, storico=False)

    # Fetch historical medications
    print("📜 Fetching historical medications...")
    fetch_medications_by_type(patient_id, jwt_token, headers, storico=True)

def fetch_medications_by_type(patient_id, jwt_token, headers, storico):
    """Fetches medications based on type (active or historical)."""
    
    params = {
        "_dc": get_timestamp(),
        "idRicovero": patient_id,
        "ordineCondSomm": "T",
        "storico": "true" if storico else "false",
        "versione": 1,
        "me": "",
        "page": 1,
        "start": 0,
        "limit": 25
    }

    response = requests.get(MEDICATIONS_URL, headers=headers, params=params, verify=False)

    if response.status_code == 401:
        print("🔄 Token expired during medication fetch. Refreshing...")
        from helpers.auth import refresh_jwt_token
        jwt_token = refresh_jwt_token()
        headers["CBA-JWT"] = f"Bearer {jwt_token}"
        response = requests.get(MEDICATIONS_URL, headers=headers, params=params, verify=False)
    
    if response.status_code == 200:
        data = response.json()
        if "data" in data and data["data"]:
            save_medications(patient_id, data["data"], storico)
        else:
            print(f"🚨 No {'historical' if storico else 'active'} medications found for patient {patient_id}")
    else:
        print(f"⚠️ Error fetching {'historical' if storico else 'active'} medications! Status Code: {response.status_code}")

def save_medications(patient_id, medications, storico):
    """Saves medication data into the SQLite database dynamically."""
    conn = sqlite3.connect("borromea.db")
    cursor = conn.cursor()

    for med in medications:
        medication_data = {
            "med_id": med["id"],
            "patient_id": patient_id,
            "idRicovero": med["idRicovero"],
            "codArticolo": med["codArticolo"],
            "aic": med["aic"],
            "dataInizio": med["dataInizio"],
            "dataFine": med.get("dataFine"),
            "qtaStandard": med["qtaStandard"],
            "tipoTerapia": med["tipoTerapia"],
            "desFarmaco": med["desFarmaco"],
            "desViaDiSomm": med["desViaDiSomm"],
            "desUniMis": med["desUniMis"],
            "principioAttivo": med["principioAttivo"],
            "orari": ", ".join(med["orari"]) if med.get("orari") else None,
            "dosi": ", ".join(med["dosi"]) if med.get("dosi") else None,
            "storico": 1 if storico else 0,  # Mark as history or active
            "isChiusa": 1 if med.get("isChiusa") else 0
        }

        columns = ", ".join(medication_data.keys())
        placeholders = ", ".join(["?" for _ in medication_data.keys()])
        values = tuple(medication_data.values())

        cursor.execute(f"""
            INSERT OR REPLACE INTO medications ({columns})
            VALUES ({placeholders});
        """, values)

    conn.commit()
    conn.close()
    print(f"✅ {'Historical' if storico else 'Active'} medications for patient {patient_id} saved successfully!")
