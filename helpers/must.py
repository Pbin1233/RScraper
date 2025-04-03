import sqlite3
import requests
import time
from datetime import datetime, timezone

def get_timestamp():
    return str(int(time.time() * 1000))

def fetch_must_details(id_ricovero, jwt_token):
    url = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/skval/must/list"
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    params = {
        "_dc": get_timestamp(),
        "idRicovero": id_ricovero,
        "page": 1,
        "start": 0,
        "limit": 25
    }

    response = requests.get(url, headers=headers, params=params, verify=False)
    if response.status_code == 200:
        return response.json().get("data", [])
    else:
        print(f"⚠️ Failed to fetch MUST data: {response.status_code}")
        return []

def save_must_data(patient_id, entries):
    conn = sqlite3.connect("borromea.db")
    cursor = conn.cursor()

    for d in entries:
        m = d.get("modelPunteggio", {})
        cursor.execute("""
            INSERT OR REPLACE INTO must (
                id, patient_id, data, compilatore, compilatoreNominativo,
                compilatoreFigProf, step1, step2, step3, punteggio
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            d["id"],
            patient_id,
            d["data"],
            d["compilatore"],
            d["compilatoreNominativo"],
            d["compilatoreFigProf"],
            d.get("step1"),
            d.get("step2"),
            d.get("step3"),
            m.get("punteggio")
        ))

    conn.commit()
    conn.close()
    print("✅ MUST data saved.")

def fetch_must(id_ricovero, patient_name, jwt_token):
    entries = fetch_must_details(id_ricovero, jwt_token)
    if entries:
        save_must_data(id_ricovero, entries)
    return entries
