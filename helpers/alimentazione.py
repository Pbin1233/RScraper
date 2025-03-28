import sqlite3
import requests
import json
import time
from datetime import datetime, timezone, timedelta

ALIM_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/parametri/alimentazione/list"
DB_PATH = "borromea.db"

def get_timestamp():
    return str(int(time.time() * 1000))

def get_current_time():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

def get_monday(date):
    return date - timedelta(days=date.weekday())

def parse_date(entry):
    return datetime.strptime(entry["data"], "%Y-%m-%d %H:%M:%S")

def get_db_boundaries(id_ricovero):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT MIN(data), MAX(data) FROM intake WHERE idRicovero = ?", (id_ricovero,))
    row = cursor.fetchone()
    conn.close()

    if row and row[0] and row[1]:
        return datetime.fromisoformat(row[0]), datetime.fromisoformat(row[1])
    return None, None

def save_to_db(id_ricovero, records):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for entry in records:
        cursor.execute("""
            INSERT OR IGNORE INTO intake (
                id, idRicovero, data, tipo, tipoRecord, quantita,
                compilatore, nominativo, compilatoreNominativo,
                compilatoreFigProf, giornoDellaSettimana, note,
                convalidato, nomeIcona, oraConvalida
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.get("id"),
            id_ricovero,
            entry.get("data"),
            entry.get("tipo"),
            entry.get("tipoRecord"),
            entry.get("quantita"),
            entry.get("compilatore"),
            entry.get("nominativo"),
            entry.get("compilatoreNominativo"),
            entry.get("compilatoreFigProf"),
            entry.get("giornoDellaSettimana"),
            entry.get("note"),
            entry.get("convalidato"),
            entry.get("nomeIcona"),
            entry.get("oraConvalida")
        ))
    conn.commit()
    conn.close()
def fetch_alimentazione(id_ricovero, jwt_token, start_date=None, infinite=True):
    now = datetime.now()
    min_saved_date, max_saved_date = get_db_boundaries(id_ricovero)

    if start_date:
        ref_date = datetime.fromisoformat(start_date)
        print(f"📅 Resuming from provided start: {ref_date}")
    else:
        ref_date = min_saved_date if min_saved_date else now
        print(f"📂 Resuming from oldest saved date: {ref_date}")

    total_saved = 0
    while True:
        week_monday = get_monday(ref_date)
        print(f"📆 Downloading week starting {week_monday.date()}:")

        headers = {
            "CBA-JWT": f"Bearer {jwt_token}",
            "Accept": "*/*",
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest"
        }

        params = {
            "_dc": str(int(datetime.utcnow().timestamp() * 1000)),
            "idRicovero": id_ricovero,
            "data": ref_date.isoformat(),
            "page": 1,
            "start": 0,
            "limit": 200,
            "group": '{"property": "giornoDellaSettimana", "direction": "ASC"}'
        }

        print(f"📡 API Call: {BASE_URL} → {params['data']}")
        response = requests.get(BASE_URL, headers=headers, params=params, verify=False)
        response.raise_for_status()
        json_data = response.json()
        entries = json_data.get("data", [])

        if not entries:
            print("🛑 No data returned for this week.")
            break

        # Stop condition: all ids < 0
        all_negative_ids = all(entry.get("id", 1) < 0 for entry in entries)
        if all_negative_ids:
            print("🛑 Week is invalid (all IDs < 0). Stopping.")
            break

        # Filter: discard any entries from the future
        valid_entries = []
        for entry in entries:
            entry_date = parse_date(entry)
            if entry_date > now:
                print(f"⚠️ Skipping future record: {entry_date}")
                continue
            valid_entries.append(entry)

        save_to_db(id_ricovero, valid_entries)
        print(f"✅ {len(valid_entries)} entries saved.")
        total_saved += len(valid_entries)

        if not infinite:
            print("☑️ One-week scrape done (non-infinite mode).")
            break

        # Advance to previous week
        ref_date -= timedelta(days=7)

    return total_saved

def get_default_start_date(patient_code, ricovero_id, jwt_token):
    url = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/ricoveri/search"
    params = {
        "_dc": int(datetime.now().timestamp() * 1000),
        "codospite": patient_code,
        "soloTipologieAbilitate": "true",
        "tutteOrg": "T",
        "page": 1,
        "start": 0,
        "limit": 25
    }

    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers, params=params, verify=False)
    ricoveri = response.json().get("data", [])

    for ricovero in ricoveri:
        if ricovero["id"] == ricovero_id:
            if ricovero["al"]:  # already discharged
                print(f"📅 Using discharge date as reference: {ricovero['al']}")
                return datetime.fromisoformat(ricovero["al"])
            else:
                print("📅 Active ricovero. Using current time as reference.")
                return datetime.now()

    print("⚠️ Ricovero not found. Defaulting to now.")
    return datetime.now()


def save_intake_data(patient_id, records):
    conn = sqlite3.connect("borromea.db")
    cursor = conn.cursor()

    for rec in records:
        tipoBlocco = json.dumps(rec.get("tipoBlocco", [])) if rec.get("tipoBlocco") else None
        permessiAnnulla = json.dumps(rec.get("permessiAnnulla", [])) if rec.get("permessiAnnulla") else None

        data_dict = {
            "id": rec["id"],
            "patient_id": patient_id,
            "idRicovero": rec["idRicovero"],
            "data": rec["data"],
            "tipo": rec["tipo"],
            "quantita": rec["quantita"],
            "tipoRecord": rec["tipoRecord"],
            "compilatore": rec["compilatore"],
            "compilatoreNominativo": rec["compilatoreNominativo"],
            "compilatoreFigProf": rec["compilatoreFigProf"],
            "giornoDellaSettimana": rec["giornoDellaSettimana"],
            "nomeIcona": rec["nomeIcona"],
            "oraConvalida": rec["oraConvalida"],
            "convalidato": rec["convalidato"],
            "note": rec["note"],
            "bozza": rec["bozza"],
            "regAnnullate": rec["regAnnullate"],
            "tipoBlocco": tipoBlocco,
            "permessiAnnulla": permessiAnnulla,
            "codEnte": rec["codEnte"],
            "hashAnnulla": rec["hashAnnulla"],
            "deletedData": rec["deletedData"],
            "nominativo": rec["nominativo"]
        }

        columns = ", ".join(data_dict.keys())
        placeholders = ", ".join(["?" for _ in data_dict])
        values = tuple(data_dict.values())

        cursor.execute(f"""
            INSERT OR REPLACE INTO intake ({columns})
            VALUES ({placeholders});
        """, values)

    conn.commit()
    conn.close()
    print(f"✅ {len(records)} alimentazione/idratazione entries saved.")
