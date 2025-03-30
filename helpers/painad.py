import sqlite3
import requests
import json
import time
import sys
from datetime import datetime, timezone

# API Endpoints
FALLS_LIST_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/testate/get"
FALLS_PREV_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/testate/prev"
FALLS_DETAILS_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/eventi/cadute/get"

# Function to generate a timestamp
def get_timestamp():
    return str(int(time.time() * 1000))

def get_current_time():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

def fetch_painad_details(test_id, jwt_token):
    url = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/skval/test/getTest"
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    params = {
        "_dc": get_timestamp(),
        "id": test_id,
        "idProfilo": 3,
        "page": 1,
        "start": 0,
        "limit": 25
    }

    response = requests.get(url, headers=headers, params=params, verify=False)
    print(f"📡 Fetching PAINAD test ID {test_id}")

    if response.status_code == 200:
        try:
            return response.json().get("data", {})
        except Exception as e:
            print(f"⚠️ Error parsing PAINAD ID {test_id}: {e}")
    elif response.status_code == 401:
        raise requests.exceptions.HTTPError(response=response)
    else:
        print(f"⚠️ Error fetching PAINAD details for ID {test_id}: Status {response.status_code}")
    return None

def fetch_painad(patient_id, patient_name, jwt_token):
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
        "tipoTestata": "Test",
        "sottoTipoTestata": 35,
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

    response = requests.get(testate_url, headers=headers, params=params, verify=False)
    print(f"📡 Fetching PAINAD headers for patient {patient_name}: {response.url}")
    if response.status_code == 200:
        data = response.json().get("data", [])
        for d in data:
            if d["id"] not in known_ids:
                all_testate.append(d)
                known_ids.add(d["id"])

    if not all_testate:
        print("⚠️ No PAINAD entries found.")
        return []

    while True:
        last = all_testate[-1]
        params_prev = {
            "_dc": get_timestamp(),
            "id": last["id"],
            "data": last["data"].replace(" ", "T"),
            "tipoTestata": "Test",
            "sottoTipoTestata": 35,
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

    # Recupero dettagli
    for t in all_testate:
        d = fetch_painad_details(t["id"], jwt_token)
        if d:
            details_map[t["id"]] = d

    save_painad_data(patient_id, patient_name, all_testate, details_map)
    return all_testate


def save_painad_data(patient_id, patient_name, testate_data, details_map):
    conn = sqlite3.connect("borromea.db")
    cursor = conn.cursor()

    for testata in testate_data:
        id_test = testata["id"]
        detail = details_map.get(id_test, {})

        domande = detail.get("domande", [])
        domande_str = "; ".join([
            f"{d['descrizione']}: {d.get('risposte', [{}])[0].get('descrizione', '')} (score: {d.get('punteggioRisposta')})"
            for d in domande
        ])

        cursor.execute("""
            INSERT OR REPLACE INTO painad (
                id, patient_id, data, compilatore, compilatoreNominativo,
                compilatoreFigProf, punteggio, punteggioMassimo, domande
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            id_test,
            patient_id,
            detail.get("data"),
            detail.get("compilatore"),
            detail.get("compilatoreNominativo"),
            detail.get("compilatoreFigProf"),
            detail.get("punteggio"),
            detail.get("punteggioMassimo"),
            domande_str
        ))

    conn.commit()
    conn.close()
    print("✅ All PAINAD entries saved.")
