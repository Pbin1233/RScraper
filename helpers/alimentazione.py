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
    min_date = datetime.fromisoformat(row[0]) if row[0] else None
    max_date = datetime.fromisoformat(row[1]) if row[1] else None
    return min_date, max_date

def save_to_db(id_ricovero, entries):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for entry in entries:
        cursor.execute("""
            INSERT OR REPLACE INTO intake (
                id, idRicovero, data, tipo, quantita, tipoRecord, compilatore,
                note, nominativo, compilatoreNominativo,
                compilatoreFigProf, giornoDellaSettimana, convalidato,
                nomeIcona, oraConvalida
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry["id"],
            entry["idRicovero"],
            entry["data"],
            entry["tipo"],
            entry["quantita"],
            entry["tipoRecord"],
            entry["compilatore"],
            entry["note"],
            entry["nominativo"],
            entry["compilatoreNominativo"],
            entry["compilatoreFigProf"],
            entry["giornoDellaSettimana"],
            entry["convalidato"],
            entry["nomeIcona"],
            entry["oraConvalida"]
        ))
    conn.commit()
    conn.close()

def fetch_alimentazione(id_ricovero, jwt_token, start_date=None, infinite=True, skip_partial_check=False):
    now = datetime.now()
    min_saved_date, max_saved_date = get_db_boundaries(id_ricovero)

    min_saved_date, max_saved_date = get_db_boundaries(id_ricovero)

    if start_date:
        ref_date = start_date if isinstance(start_date, datetime) else datetime.fromisoformat(start_date)
        print(f"📅 Resuming from provided start: {ref_date}")
    else:
        if min_saved_date is None:
            print("⚠️ No existing records found for this ricovero. Skipping.")
            return 0
        ref_date = min_saved_date
        print(f"📂 Resuming from oldest saved date: {ref_date}")

    total_saved = 0

    extra_update_done = False

    while True:
        week_start = get_monday(ref_date)
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        print(f"📆 Downloading week starting {week_start.date()}:")

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

        print(f"📡 API Call: {ALIM_URL} → {params['data']}")
        response = requests.get(ALIM_URL, headers=headers, params=params, verify=False)
        response.raise_for_status()
        json_data = response.json()
        entries = json_data.get("data", [])

        if not entries:
            print("🛑 No data returned for this week.")
            break

        # Filter out placeholder entries and future-dated entries
        valid_entries = [
            entry for entry in entries
            if parse_date(entry) <= now and entry.get("id", 0) > 0
        ]

        all_negative_ids = all(entry.get("id", 1) < 0 for entry in entries)
        if all_negative_ids:
            print("🛑 Week is invalid (all IDs < 0). Stopping.")
            break

        # Check if this week is already fully saved in original DB state
        if not infinite:
            # Single week scrape mode, exit after one
            print("☑️ One-week scrape done (non-infinite mode).")
            break

        if not valid_entries:
            print("🛑 Week is empty. Stopping.")
            break

        save_to_db(id_ricovero, valid_entries)
        print(f"✅ {len(valid_entries)} entries saved.")
        total_saved += len(valid_entries)

        # Exit condition for non-infinite mode
        if not infinite:
            print("☑️ One-week scrape done (non-infinite mode).")
            break

        if not skip_partial_check and min_saved_date and week_start <= max_saved_date and week_end >= min_saved_date and not extra_update_done:
            print("⚠️ Week already partially saved (based on original DB scan). Will update this and go one more week.")
            extra_update_done = True
            ref_date -= timedelta(days=7)
            continue

        if not skip_partial_check and extra_update_done:
            print("🛑 One extra update done after partial week. Stopping.")
            break

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
