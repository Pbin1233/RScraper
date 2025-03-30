import sqlite3
import requests
import json
import time
from datetime import datetime, timezone

# API Endpoints
RESTRAINTS_LIST_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/testate/get"
RESTRAINTS_PREV_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/testate/prev"
RESTRAINTS_DETAILS_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/eventi/contenzioni/get"

def get_timestamp():
    return str(int(time.time() * 1000))

def get_current_time():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

def save_contenzioni_data(patient_id, patient_name, testate_data, details_data):
    """Saves contenzioni data into the SQLite database dynamically."""
    conn = sqlite3.connect("borromea.db")
    cursor = conn.cursor()

    for cont in testate_data:
        cont_id = cont["id"]
        cont_date = cont["data"]
        details = details_data.get(cont_id, {})

        # Ensure we save all relevant fields
        cont_data_dict = {
            "contenzione_id": cont_id,
            "patient_id": patient_id,
            "data": cont_date,
            "dataInizio": details.get("dataInizio"),
            "dataFine": details.get("dataFine"),
            "dataRevisioneFormatted": details.get("dataRevisioneFormatted"),
            "motivazione": details.get("motivazione"),
            "mezziContenzione": details.get("mezzoContenzione"),
            "mezziContenzioneDecodificati": details.get("mezziContenzioneDecodificati"),
            "monitoraggio": details.get("monitoraggio"),
            "alternative": details.get("alternative"),
            "ospiteAffettoDa": details.get("ospiteAffettoDa"),
            "famigliaInformata": details.get("familiareInformato"),
            "compilatore": details.get("compilatore"),
            "compilatoreNominativo": details.get("compilatoreNominativo"),
            "compilatoreFigProf": details.get("compilatoreFigProf"),
            "tipoBlocco": json.dumps(details.get("tipoBlocco", [])),  # Store as JSON
            "contenzioneQuando": details.get("contenzioneQuando"),
            "note": json.dumps(details.get("note", [])),  # Store as JSON
            "scadenza": details.get("scadenza"),
            "agendaFunzione": details.get("agendaFunzione"),
            "fineMese": details.get("fineMese"),
            "permanente": details.get("permanente"),
        }

        # Dynamically build SQL query
        columns = ", ".join(cont_data_dict.keys())
        placeholders = ", ".join(["?" for _ in cont_data_dict.keys()])
        values = tuple(cont_data_dict.values())

        cursor.execute(f"""
            INSERT OR REPLACE INTO contenzioni ({columns})
            VALUES ({placeholders});
        """, values)

    conn.commit()
    conn.close()
    print("✅ All contenzioni saved successfully!")

def fetch_contenzione_details(cont_id, jwt_token):
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    params = {
        "_dc": get_timestamp(),
        "id": cont_id,
        "page": 1,
        "start": 0,
        "limit": 25
    }

    response = requests.get(RESTRAINTS_DETAILS_URL, headers=headers, params=params, verify=False)

    if response.status_code == 401:
        from helpers.auth import refresh_jwt_token
        jwt_token = refresh_jwt_token()
        headers["CBA-JWT"] = f"Bearer {jwt_token}"
        response = requests.get(RESTRAINTS_DETAILS_URL, headers=headers, params=params, verify=False)

    try:
        return response.json()
    except Exception as e:
        print(f"⚠️ Error parsing contenzione details {cont_id}: {e}")
        return None

def fetch_contenzioni(patient_id, patient_name, jwt_token):
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    all_contenzioni = []
    known_ids = set()
    details_data = {}

    params_list = {
        "_dc": get_timestamp(),
        "tipoTestata": "Contenzione",
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

    response = requests.get(RESTRAINTS_LIST_URL, headers=headers, params=params_list, verify=False)

    if response.status_code == 200:
        data = response.json()
        for cont in data.get("data", []):
            cont_id = cont["id"]
            if cont_id not in known_ids:
                all_contenzioni.append(cont)
                known_ids.add(cont_id)
    else:
        print(f"⚠️ Error fetching contenzioni list! Status: {response.status_code}")
        return []

    if not all_contenzioni:
        print("⚠️ No contenzioni found.")
        return []

    # 🔄 Keep fetching previous records until `first == "T"`
    while True:
        last = all_contenzioni[-1]
        last_id = last["id"]
        last_date = last["data"].replace(" ", "T")

        params_prev = {
            "_dc": get_timestamp(),
            "id": last_id,
            "data": last_date,
            "tipoTestata": "Contenzione",
            "idRicovero": patient_id,
            "idProfilo": 3,
            "compilatore": 27
        }

        response = requests.get(RESTRAINTS_PREV_URL, headers=headers, params=params_prev, verify=False)

        if response.status_code != 200:
            print(f"⚠️ Error fetching previous contenzioni! Status: {response.status_code}")
            break

        prev_data = response.json()
        if not prev_data.get("data"):
            print("❌ No more previous contenzioni found. Stopping.")
            break

        new_entry = prev_data["data"][0]
        print(f"🔍 Found previous contenzione: ID {new_entry['id']} - Date {new_entry['data']}")

        if new_entry["id"] in known_ids:
            print("⛔ Already known ID. Stopping.")
            break

        all_contenzioni.append(new_entry)
        known_ids.add(new_entry["id"])

        if new_entry.get("first") == "T":
            print("🔚 Reached the first recorded contenzione. Stopping.")
            break

    print(f"✅ Total contenzioni fetched: {len(all_contenzioni)}")

    # Fetch details for each contenzione
    for cont in all_contenzioni:
        cont_id = cont["id"]
        details = fetch_contenzione_details(cont_id, jwt_token)
        if details and "data" in details:
            details_data[cont_id] = details["data"]

    # 🔄 Save everything into the database
    save_contenzioni_data(patient_id, patient_name, all_contenzioni, details_data)

    return all_contenzioni
