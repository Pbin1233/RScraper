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

def fetch_nrs_details(test_id, jwt_token):
    url = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/skval/dolore/get"
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
    print(f"📡 Fetching NRS test ID {test_id}")

    if response.status_code == 200:
        return response.json().get("data", {})
    elif response.status_code == 401:
        raise requests.exceptions.HTTPError(response=response)
    else:
        print(f"⚠️ Failed to fetch NRS ID {test_id}: {response.status_code}")
        return None

def save_nrs_data(patient_id, patient_name, testate_data, details_map):
    conn = sqlite3.connect("borromea.db")
    cursor = conn.cursor()

    for t in testate_data:
        test_id = t["id"]
        detail = details_map.get(test_id, {})

        cursor.execute("""
            INSERT OR REPLACE INTO nrs (
                id, patient_id, data, valore, note, scadenza,
                tipo, compilatore, compilatoreNominativo, compilatoreFigProf
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            test_id,
            patient_id,
            detail.get("data"),
            detail.get("valore"),
            detail.get("note"),
            detail.get("scadenza"),
            detail.get("tipo"),
            detail.get("compilatore"),
            detail.get("compilatoreNominativo"),
            detail.get("compilatoreFigProf")
        ))

    conn.commit()
    conn.close()
    print("✅ All NRS entries saved.")


def fetch_nrs(patient_id, patient_name, jwt_token):
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
        "tipoTestata": "SkValDolore",
        "sottoTipoTestata": 37,
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
    print(f"📡 Fetching NRS headers for patient {patient_name}: {response.url}")
    if response.status_code == 200:
        for d in response.json().get("data", []):
            if d["id"] not in known_ids:
                all_testate.append(d)
                known_ids.add(d["id"])

    if not all_testate:
        print("⚠️ No NRS entries found.")
        return []

    while True:
        last = all_testate[-1]
        params_prev = {
            "_dc": get_timestamp(),
            "id": last["id"],
            "data": last["data"].replace(" ", "T"),
            "tipoTestata": "SkValDolore",
            "sottoTipoTestata": 37,
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
        d = fetch_nrs_details(t["id"], jwt_token)
        if d:
            details_map[t["id"]] = d

    if not details_map:
        print("⚠️ No NRS details successfully downloaded.")
        return None

    save_nrs_data(patient_id, patient_name, all_testate, details_map)
    return all_testate

