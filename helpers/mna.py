import sqlite3
import requests
import time
from datetime import datetime, timezone

def get_timestamp():
    return str(int(time.time() * 1000))

def get_current_time():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

def fetch_mna_details(test_id, jwt_token):
    url = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/skval/mna/get"
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
    print(f"📡 Fetching MNA ID {test_id}")
    if response.status_code == 200:
        return response.json().get("data", {})
    else:
        print(f"⚠️ Failed to fetch MNA ID {test_id}: {response.status_code}")
        return None

def save_mna_data(patient_id, testate_data, details_map):
    conn = sqlite3.connect("borromea.db")
    cursor = conn.cursor()

    for t in testate_data:
        d = details_map.get(t["id"], {})
        cursor.execute("""
            INSERT OR REPLACE INTO mna (
                id, patient_id, data, compilatore, compilatoreNominativo, compilatoreFigProf,
                scadenza, convertito, bmi, mac, cc, perditaPeso, viveIndipendentemente, piuDi3Farmaci,
                stressPsicologici, mobilita, problemiNeuro, piagheDecubito, pastiCompleti, consuma,
                consumaFruttaVerdura, riduzioneAppetito, liquidiAssunti, comeMangia, ritieneDiAvereProb,
                statoSalute, consuma1, consuma2, consuma3, peso, altezza, bmiCalcolata, dataBmi, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            d.get("id"),
            patient_id,
            d.get("data"),
            d.get("compilatore"),
            d.get("compilatoreNominativo"),
            d.get("compilatoreFigProf"),
            d.get("scadenza"),
            d.get("convertito"),
            d.get("bmi"),
            d.get("mac"),
            d.get("cc"),
            d.get("perditaPeso"),
            d.get("viveIndipendentemente"),
            d.get("piuDi3Farmaci"),
            d.get("stressPsicologici"),
            d.get("mobilita"),
            d.get("problemiNeuro"),
            d.get("piagheDecubito"),
            d.get("pastiCompleti"),
            d.get("consuma"),
            d.get("consumaFruttaVerdura"),
            d.get("riduzioneAppetito"),
            d.get("liquidiAssunti"),
            d.get("comeMangia"),
            d.get("ritieneDiAvereProb"),
            d.get("statoSalute"),
            d.get("consuma1"),
            d.get("consuma2"),
            d.get("consuma3"),
            d.get("peso"),
            d.get("altezza"),
            d.get("bmiCalcolata"),
            d.get("dataBmi"),
            d.get("note")
        ))

    conn.commit()
    conn.close()
    print("✅ All MNA entries saved.")

def fetch_mna(patient_id, patient_name, jwt_token):
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
        "tipoTestata": "MNA",
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
        print("⚠️ No MNA entries found.")
        return []

    # Try to get older entries using /prev
    while True and all_testate:
        last = all_testate[-1]
        params_prev = {
            "_dc": get_timestamp(),
            "id": last["id"],
            "data": last["data"].replace(" ", "T"),
            "tipoTestata": "MNA",
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
        d = fetch_mna_details(t["id"], jwt_token)
        if d:
            details_map[t["id"]] = d

    if not details_map:
        print("⚠️ No MNA details successfully downloaded.")
        return None

    save_mna_data(patient_id, all_testate, details_map)
    return all_testate

