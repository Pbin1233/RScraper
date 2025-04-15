import sqlite3
import requests
import time
from datetime import datetime, timezone

def get_timestamp():
    return str(int(time.time() * 1000))

def get_current_time():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

def fetch_gbs_details(test_id, jwt_token):
    url = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/skval/gbs/get"
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
    print(f"📡 Fetching GBS ID {test_id}")
    if response.status_code == 200:
        return response.json().get("data", {})
    elif response.status_code == 401:
        raise requests.exceptions.HTTPError(response=response)
    else:
        print(f"⚠️ Failed to fetch GBS ID {test_id}: {response.status_code}")
        return None

def save_gbs_data(patient_id, patient_name, testate_data, details_map):
    conn = sqlite3.connect("borromea.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gbs (
            id INTEGER PRIMARY KEY,
            patient_id INTEGER,
            data TEXT,
            compilatore INTEGER,
            compilatoreNominativo TEXT,
            compilatoreFigProf TEXT,
            note TEXT,
            scadenza INTEGER,
            convertito TEXT,
            nonsomministrabile TEXT,
            sdconfusione INTEGER,
            sdirritabilita INTEGER,
            sdansia INTEGER,
            sdangoscia INTEGER,
            sddepressione INTEGER,
            sdirrequietezza INTEGER,
            agendaFunzione TEXT,
            FOREIGN KEY (patient_id) REFERENCES hospitalizations_history(idRicoveroCU)
        )
    """)

    for t in testate_data:
        test_id = t["id"]
        d = details_map.get(test_id, {})

        cursor.execute("""
            INSERT OR REPLACE INTO gbs (
                id, patient_id, data, compilatore, compilatoreNominativo,
                compilatoreFigProf, note, scadenza, convertito,
                nonsomministrabile, sdconfusione, sdirritabilita, sdansia,
                sdangoscia, sddepressione, sdirrequietezza, agendaFunzione
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            d.get("nonsomministrabile"),
            d.get("sdconfusione"),
            d.get("sdirritabilita"),
            d.get("sdansia"),
            d.get("sdangoscia"),
            d.get("sddepressione"),
            d.get("sdirrequietezza"),
            d.get("agendaFunzione")
        ))

    conn.commit()
    conn.close()
    print("✅ All GBS entries saved.")

def fetch_gbs(patient_id, patient_name, jwt_token):
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
        "tipoTestata": "Gbs",
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
        print("⚠️ No GBS entries found.")
        return []

    while True and all_testate:
        last = all_testate[-1]
        params_prev = {
            "_dc": get_timestamp(),
            "id": last["id"],
            "data": last["data"].replace(" ", "T"),
            "tipoTestata": "Gbs",
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
        d = fetch_gbs_details(t["id"], jwt_token)
        if d:
            details_map[t["id"]] = d

    save_gbs_data(patient_id, patient_name, all_testate, details_map)
    return all_testate
