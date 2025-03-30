import sqlite3
import requests
import time
from datetime import datetime, timezone

def get_timestamp():
    return str(int(time.time() * 1000))

def get_current_time():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

def fetch_tinetti_details(test_id, jwt_token):
    url = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/skval/tinetti/get"
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
    print(f"📡 Fetching Tinetti ID {test_id}")
    if response.status_code == 200:
        return response.json().get("data", {})
    elif response.status_code == 401:
        raise requests.exceptions.HTTPError(response=response)
    else:
        print(f"⚠️ Failed to fetch Tinetti ID {test_id}: {response.status_code}")
        return None


def save_tinetti_data(patient_id, patient_name, testate_data, details_map):
    conn = sqlite3.connect("borromea.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tinetti (
            id INTEGER PRIMARY KEY,
            patient_id INTEGER,
            data TEXT,
            compilatore INTEGER,
            compilatoreNominativo TEXT,
            compilatoreFigProf TEXT,
            note TEXT,
            scadenza INTEGER,
            punteggio INTEGER,
            punteggio_andatura INTEGER,
            punteggio_equilibrio INTEGER,
            andInizioDeamb INTEGER,
            andLunghPassoDx INTEGER,
            andAltezzaPassoDx INTEGER,
            andLunghPassoSx INTEGER,
            andAltezzaPassoSx INTEGER,
            andSimmetria INTEGER,
            andContinuitaPasso INTEGER,
            andTraiettoria INTEGER,
            andTronco INTEGER,
            andCammino INTEGER,
            eqDaSeduto INTEGER,
            eqAlzarsiSedia INTEGER,
            eqTentativo INTEGER,
            eqStazEretta5Sec INTEGER,
            eqStazErettaProl INTEGER,
            eqRomberg INTEGER,
            eqRombergSens INTEGER,
            eqGirarsi INTEGER,
            eqGirarsiStab INTEGER,
            eqSedersi INTEGER
        )
    """)

    for t in testate_data:
        test_id = t["id"]
        d = details_map.get(test_id, {})
        m = d.get("modelPunteggio", {})

        cursor.execute("""
            INSERT OR REPLACE INTO tinetti (
                id, patient_id, data, compilatore, compilatoreNominativo,
                compilatoreFigProf, note, scadenza, punteggio,
                punteggio_andatura, punteggio_equilibrio,
                andInizioDeamb, andLunghPassoDx, andAltezzaPassoDx,
                andLunghPassoSx, andAltezzaPassoSx, andSimmetria,
                andContinuitaPasso, andTraiettoria, andTronco, andCammino,
                eqDaSeduto, eqAlzarsiSedia, eqTentativo, eqStazEretta5Sec,
                eqStazErettaProl, eqRomberg, eqRombergSens,
                eqGirarsi, eqGirarsiStab, eqSedersi
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            test_id,
            patient_id,
            d.get("data"),
            d.get("compilatore"),
            d.get("compilatoreNominativo"),
            d.get("compilatoreFigProf"),
            d.get("note"),
            d.get("scadenza"),
            m.get("punteggio"),
            m.get("punteggioAndatura"),
            m.get("punteggioEquilibrio"),
            d.get("andInizioDeamb"),
            d.get("andLunghPassoDx"),
            d.get("andAltezzaPassoDx"),
            d.get("andLunghPassoSx"),
            d.get("andAltezzaPassoSx"),
            d.get("andSimmetria"),
            d.get("andContinuitaPasso"),
            d.get("andTraiettoria"),
            d.get("andTronco"),
            d.get("andCammino"),
            d.get("eqDaSeduto"),
            d.get("eqAlzarsiSedia"),
            d.get("eqTentativo"),
            d.get("eqStazEretta5Sec"),
            d.get("eqStazErettaProl"),
            d.get("eqRomberg"),
            d.get("eqRombergSens"),
            d.get("eqGirarsi"),
            d.get("eqGirarsiStab"),
            d.get("eqSedersi")
        ))

    conn.commit()
    conn.close()
    print("✅ All Tinetti entries saved.")

def fetch_tinetti(patient_id, patient_name, jwt_token):
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
        "tipoTestata": "Tinetti",
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
        print("⚠️ No Tinetti entries found.")
        return []

    while True and all_testate:
        last = all_testate[-1]
        params_prev = {
            "_dc": get_timestamp(),
            "id": last["id"],
            "data": last["data"].replace(" ", "T"),
            "tipoTestata": "Tinetti",
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
        d = fetch_tinetti_details(t["id"], jwt_token)
        if d:
            details_map[t["id"]] = d

    save_tinetti_data(patient_id, patient_name, all_testate, details_map)
    return all_testate
