import sqlite3
import requests
import json
import time
from datetime import datetime, timezone
import re
from html import unescape

# Endpoints
PI_LIST_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/testate/get"
PI_PREV_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/testate/prev"
PI_DETAILS_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/pi/pi/get"
PAI_LIST_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/testate/get"
PAI_PREV_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/testate/prev"
PAI_DETAILS_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/pai/pai/piano/get"

PAI_COD_AREE = [3244, 3245, 3246, 3247]  # Aree fisse da interrogare

def get_timestamp():
    return str(int(time.time() * 1000))

def get_current_time():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

def clean_html(text):
    if not text:
        return ""
    text = unescape(text)  # converte &nbsp; ecc.
    text = re.sub(r"<[^>]+>", "", text)  # rimuove tag HTML
    return text.strip()

def fetch_pai_details(idTe, jwt_token):
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    all_data = []
    for codArea in PAI_COD_AREE:
        params = {
            "_dc": get_timestamp(),
            "idTe": idTe,
            "codArea": codArea,
            "page": 1,
            "start": 0,
            "limit": 25
        }

        response = requests.get(PAI_DETAILS_URL, headers=headers, params=params, verify=False)
        print(f"📡 Fetching PAI area {codArea} for IDTe {idTe}: {response.url}")

        if response.status_code == 200:
            try:
                data = response.json().get("data", [])
                for d in data:
                    d["problemi"] = clean_html(d.get("problemi"))
                    d["obiettivi"] = clean_html(d.get("obiettivi"))
                    d["strategie"] = clean_html(d.get("strategie"))
                    d["note"] = clean_html(d.get("note"))
                all_data.extend(data)
            except Exception as e:
                print(f"⚠️ Error parsing area {codArea}: {e}")
        else:
            print(f"⚠️ Error fetching area {codArea} for IDTe {idTe}: {response.status_code}")

    return all_data

def fetch_pi_details(pi_id, jwt_token):
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    params = {
        "_dc": get_timestamp(),
        "id": pi_id,
        "page": 1,
        "start": 0,
        "limit": 25
    }

    response = requests.get(PI_DETAILS_URL, headers=headers, params=params, verify=False)
    print(f"📡 Fetching PI details for ID {pi_id}: {response.url}")

    if response.status_code == 200:
        try:
            return response.json()
        except Exception as e:
            print(f"⚠️ Error parsing details for PI ID {pi_id}: {e}")
    else:
        print(f"⚠️ Error fetching PI ID {pi_id}: Status {response.status_code}")

    return None

def save_pai_data(patient_id, patient_name, testate_data, details_map):
    conn = sqlite3.connect("borromea.db")
    cursor = conn.cursor()

    for testata in testate_data:
        idTe = testata["id"]
        data = testata["data"]
        pai_entries = details_map.get(idTe, [])

        for entry in pai_entries:
            indicatori = ", ".join([
                i.get("descrizione") or i.get("descrizioneFormatted") or "(senza descrizione)"
                for i in entry.get("indicatori", [])
            ])
            compilatori = ", ".join([c["compilatoreNominativo"] for c in entry.get("listaCompilatori", [])])

            cursor.execute("""
                INSERT OR REPLACE INTO pai (
                    pai_id, patient_id, idTe, data,
                    codArea, nomeArea, patologia, descrizionePatologia,
                    problemi, obiettivi, strategie, rispObiettiviDesc,
                    indicatori, note, compilatoreNominativo,
                    compilatoreFigProf, listaCompilatori
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry["id"], patient_id, idTe, data,
                entry.get("codArea"),
                entry.get("nomeArea"),
                entry.get("patologia"),
                entry.get("descrizionePatologia"),
                entry.get("problemi"),
                entry.get("obiettivi"),
                entry.get("strategie"),
                entry.get("rispObiettiviDesc"),
                indicatori,
                entry.get("note"),
                entry.get("compilatoreNominativo"),
                entry.get("compilatoreFigProf"),
                compilatori
            ))

    conn.commit()
    conn.close()
    print("✅ All PAI entries saved.")

def fetch_pai(patient_id, patient_name, jwt_token):
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    all_testate = []
    known_ids = set()
    details_map = {}

    params = {
        "_dc": get_timestamp(),
        "tipoTestata": "Pai",
        "idRicovero": patient_id,
        "idProfilo": 3,
        "compilatore": 27,
        "soloUnaTestata": "F",
        "extraParams": "",
        "sottoTipoTestata": 0,
        "page": 1,
        "start": 0,
        "limit": 25,
        "al": get_current_time()
    }

    response = requests.get(PAI_LIST_URL, headers=headers, params=params, verify=False)
    print(f"📡 Fetching PAI testate: {response.url}")

    if response.status_code == 200:
        data = response.json().get("data", [])
        for d in data:
            if d["id"] not in known_ids:
                all_testate.append(d)
                known_ids.add(d["id"])
    else:
        print(f"⚠️ Failed to fetch PAI testate: {response.status_code}")
        return []

    # Try previous ones (optional logic)
    while len(all_testate) < 6:
        last = all_testate[-1]
        params_prev = {
            "_dc": get_timestamp(),
            "id": last["id"],
            "data": last["data"].replace(" ", "T"),
            "tipoTestata": "Pai",
            "idRicovero": patient_id,
            "idProfilo": 3,
            "compilatore": 27,
            "sottoTipoTestata": 0
        }

        response = requests.get(PAI_PREV_URL, headers=headers, params=params_prev, verify=False)
        if response.status_code == 200:
            prev = response.json().get("data", [])
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

    # Get details for each testata
    for t in all_testate:
        idTe = t["id"]
        details = fetch_pai_details(idTe, jwt_token)
        details_map[idTe] = details

    save_pai_data(patient_id, patient_name, all_testate, details_map)
    return all_testate

def save_pi_data(patient_id, patient_name, testate_data, details_data):
    conn = sqlite3.connect("borromea.db")
    cursor = conn.cursor()

    for pi in testate_data:
        pi_id = pi["id"]
        pi_date = pi["data"]
        details = details_data.get(pi_id, {}).get("data", {})

        tipoBlocco = ", ".join([f"{t['codice']}:{t['valore']} ({t['extra']})" for t in details.get("tipoBlocco", [])]) if details.get("tipoBlocco") else None
        permessiAnnulla = ", ".join(map(str, details.get("permessiAnnulla", []))) if details.get("permessiAnnulla") else None
        team = ", ".join([f"{m['descrFiguraProf']} - {m['nominativo']}" for m in details.get("team", [])]) if details.get("team") else None
        listaCompilatori = ", ".join([c["compilatoreNominativo"] for c in details.get("listaCompilatori", [])]) if details.get("listaCompilatori") else None
        listaAree = ", ".join([str(a["area"]) for a in details.get("listaAree", [])]) if details.get("listaAree") else None

        areaNotes = details.get("areaNotes", [])
        areaDescriptions = "; ".join([
            f"{a.get('nomeArea')}: {clean_html(a.get('note', ''))}"
            for a in areaNotes
        ]) if areaNotes else None

        pi_dict = {
            "pi_id": pi_id,
            "patient_id": patient_id,
            "data": pi_date,
            "deletedData": details.get("deletedData"),
            "tipoBlocco": tipoBlocco,
            "bozza": details.get("bozza"),
            "permessiAnnulla": permessiAnnulla,
            "codEnte": details.get("codEnte"),
            "idRicovero": details.get("idRicovero"),
            "compilatore": details.get("compilatore"),
            "compilatoreNominativo": details.get("compilatoreNominativo"),
            "compilatoreFigProf": details.get("compilatoreFigProf"),
            "schedavalida": details.get("schedavalida"),
            "nominativo": details.get("nominativo"),
            "isCopia": details.get("isCopia"),
            "listaCompilatori": listaCompilatori,
            "team": team,
            "listaAree": listaAree,
            "areaDescriptions": areaDescriptions,
        }

        columns = ", ".join(pi_dict.keys())
        placeholders = ", ".join(["?" for _ in pi_dict])
        values = tuple(pi_dict.values())

        cursor.execute(f"""
            INSERT OR REPLACE INTO pi ({columns})
            VALUES ({placeholders});
        """, values)

    conn.commit()
    conn.close()
    print("✅ All PI entries saved successfully!")

def fetch_area_notes(idTe, jwt_token):
    url = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/pi/pi/aree/listbyidte"
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    params = {
        "_dc": get_timestamp(),
        "idTe": idTe,
        "page": 1,
        "start": 0,
        "limit": 25
    }

    response = requests.get(url, headers=headers, params=params, verify=False)
    print(f"📡 Fetching area notes for PI ID {idTe}: {response.url}")

    if response.status_code == 200:
        try:
            return response.json().get("data", [])
        except Exception as e:
            print(f"⚠️ Error parsing area notes for PI ID {idTe}: {e}")
    else:
        print(f"⚠️ Error fetching area notes: Status {response.status_code}")

    return []


def fetch_pi(patient_id, patient_name, jwt_token):
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    all_pi = []
    known_ids = set()
    details_data = {}

    params = {
        "_dc": get_timestamp(),
        "tipoTestata": "PrgInd",
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

    response = requests.get(PI_LIST_URL, headers=headers, params=params, verify=False)
    print(f"📡 Initial PI list: {response.url}")

    if response.status_code == 200:
        data = response.json()
        for entry in data.get("data", []):
            if entry["id"] not in known_ids:
                all_pi.append(entry)
                known_ids.add(entry["id"])
    else:
        print(f"⚠️ Error fetching PI list: {response.status_code}")
        return []

    # Fetch previous entries
    while len(all_pi) < 6:
        last = all_pi[-1]
        last_id = last["id"]
        last_date = last["data"].replace(" ", "T")

        params_prev = {
            "_dc": get_timestamp(),
            "id": last_id,
            "data": last_date,
            "tipoTestata": "PrgInd",
            "idRicovero": patient_id,
            "idProfilo": 3,
            "compilatore": 27,
            "al": get_current_time()
        }

        response = requests.get(PI_PREV_URL, headers=headers, params=params_prev, verify=False)

        if response.status_code == 200:
            data = response.json()
            if "data" in data and data["data"]:
                new_entry = data["data"][0]
                if new_entry["id"] not in known_ids:
                    all_pi.append(new_entry)
                    known_ids.add(new_entry["id"])
                else:
                    break
            else:
                break
        else:
            print(f"⚠️ Error fetching previous PI entries: {response.status_code}")
            break

    print("🔍 Fetching PI details...")
    for pi in all_pi:
        pi_id = pi["id"]
        details = fetch_pi_details(pi_id, jwt_token)
        area_notes = fetch_area_notes(pi_id, jwt_token)

        if details:
            details["data"]["areaNotes"] = area_notes
            details_data[pi_id] = details

    save_pi_data(patient_id, patient_name, all_pi, details_data)
    
    return all_pi
