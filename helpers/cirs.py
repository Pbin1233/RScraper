import sqlite3
import requests
import json
import time
import sys
from datetime import datetime, timezone

# Function to generate a timestamp
def get_timestamp():
    return str(int(time.time() * 1000))

def get_current_time():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

def fetch_cirs_details(test_id, jwt_token):
    url = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/skval/cirs/get"
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    params = {
        "_dc": get_timestamp(),
        "id": test_id,
        "page": 1,
        "start": 0,
        "limit": 25
    }

    response = requests.get(url, headers=headers, params=params, verify=False)
    print(f"📡 Fetching CIRS ID {test_id}")
    if response.status_code == 200:
        return response.json().get("data", {})
    elif response.status_code == 401:
        raise requests.exceptions.HTTPError(response=response)
    else:
        print(f"⚠️ Failed to fetch CIRS ID {test_id}: {response.status_code}")
        return None

def save_cirs_data(patient_id, patient_name, testate_data, details_map):
    conn = sqlite3.connect("borromea.db")
    cursor = conn.cursor()

    for t in testate_data:
        test_id = t["id"]
        d = details_map.get(test_id, {})

        # Lista ordinata delle 14 aree CIRS (incluso psichiatrico)
        categories = [
            "cardiaca", "ipertensione", "vascolari", "respiratorie",
            "oongl", "appGiSup", "appGiInf", "epatiche",
            "renali", "patGenUri", "sisMusSche", "sisNervoso",
            "endoMeta", "psichiatrico"
        ]

        values = [d.get(k) for k in categories]

        # Comorbidity Index: solo le prime 13 aree, con punteggio >= 3
        comorbidity_index = sum(
            1 for k in categories[:-1]  # exclude 'psichiatrico'
            if isinstance(d.get(k), int) and d[k] >= 3
        )

        # Severity Index: media di tutti i valori numerici (escluso psichiatrico)
        valid_scores = [d.get(k) for k in categories[:-1] if isinstance(d.get(k), int)]
        severity_index = round(sum(valid_scores) / len(valid_scores), 1) if valid_scores else 0

        cursor.execute("""
            INSERT OR REPLACE INTO cirs (
                id, patient_id, data, compilatore, compilatoreNominativo,
                compilatoreFigProf, note, scadenza, convertito, punteggio,
                cardiaca, ipertensione, vascolari, respiratorie, oongl,
                appGiSup, appGiInf, epatiche, renali, patGenUri,
                sisMusSche, sisNervoso, endoMeta, psichiatrico,
                indiceComorbilita, indiceSeverita
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            test_id,
            patient_id,
            d.get("data"),
            d.get("compilatore"),
            d.get("compilatoreNominativo"),
            d.get("compilatoreFigProf"),
            d.get("note"),
            d.get("scadenza"),
            d.get("convertito"),
            d.get("punteggio"),
            *values,
            comorbidity_index,
            severity_index
        ))

    conn.commit()
    conn.close()
    print("✅ All CIRS entries saved.")

def fetch_cirs(patient_id, patient_name, jwt_token):
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    testate_url = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/testate/get"
    prev_url = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/testate/prev"
    all_testate = []
    known_ids = set()
    details_map = {}

    params = {
        "_dc": get_timestamp(),
        "tipoTestata": "Cirs",
        "idRicovero": patient_id,
        "idProfilo": 3,
        "compilatore": 27,
        "soloUnaTestata": "F",
        "extraParams": "",
        "page": 1,
        "start": 0,
        "limit": 25,
        "al": get_current_time()
    }

    r = requests.get(testate_url, headers=headers, params=params, verify=False)
    if r.status_code == 200:
        for d in r.json().get("data", []):
            if d["id"] not in known_ids:
                all_testate.append(d)
                known_ids.add(d["id"])

    if not all_testate:
        print("⚠️ No CIRS entries found.")
        return []

    while True:
        last = all_testate[-1]
        params_prev = {
            "_dc": get_timestamp(),
            "id": last["id"],
            "data": last["data"].replace(" ", "T"),
            "tipoTestata": "Cirs",
            "idRicovero": patient_id,
            "idProfilo": 3,
            "compilatore": 27
        }
        r = requests.get(prev_url, headers=headers, params=params_prev, verify=False)
        if r.status_code == 200:
            prev = r.json().get("data", [])
            if not prev:
                break
            new = prev[0]
            if new["id"] not in known_ids:
                all_testate.append(new)
                known_ids.add(new["id"])
            else:
                break
        else:
            break

    for t in all_testate:
        d = fetch_cirs_details(t["id"], jwt_token)
        if d:
            details_map[t["id"]] = d

    save_cirs_data(patient_id, patient_name, all_testate, details_map)
    return all_testate
