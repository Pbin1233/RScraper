import sqlite3
import requests
import json
import time

# API Endpoints
DIARIO_LIST_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/testate/get"
DIARIO_DETAILS_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/diari/get"

# Function to generate a timestamp
def get_timestamp():
    return str(int(time.time() * 1000))

def fetch_diario_entries(patient_id, jwt_token, diary_type=13):
    """
    Fetch all diary entries for a patient, stopping when an entry contains "last": "T".
    Also prints the full JSON response for debugging.
    """
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    all_diarios = []
    known_diario_ids = set()
    start_index = 1  # Start at 0 and increment by 4 each time

    while True:
        params_list = {
            "_dc": get_timestamp(),
            "tipoTestata": "Diari",
            "idRicovero": patient_id,
            "idProfilo": 3,
            "compilatore": 27,
            "soloUnaTestata": "F",
            "extraParams": "",
            "sottoTipoTestata": diary_type,
            "page": start_index,
            "start": 0,
            "limit": 25
        }

        response = requests.get(DIARIO_LIST_URL, headers=headers, params=params_list, verify=False)

        print(f"\n📡 Request Params (start={start_index}): {json.dumps(params_list, indent=2)}")

        if response.status_code == 200:
            data = response.json()

            # Print the full response for debugging
            print(f"📥 API Response (start={start_index}):\n{json.dumps(data, indent=2)}")

            if "data" in data and data["data"]:
                for diario in data["data"]:
                    diario_id = diario["id"]
                    if diario_id not in known_diario_ids:
                        all_diarios.append(diario)
                        known_diario_ids.add(diario_id)

                    # Stop if this is the last available entry
                    if diario.get("last") == "T":
                        print(f"🛑 Stopping fetch at Diario ID {diario_id} (last='T').")
                        return all_diarios

                print(f"✅ Retrieved {len(data['data'])} diary entries (Start: {start_index})")
            else:
                print("🚨 No more diary entries found!")
                break  # Stop fetching if no more data
        else:
            print(f"❌ Error fetching diaries! Status Code: {response.status_code}, Response: {response.text}")
            break

        start_index += 1  # Increase start index by 4 each time

    return all_diarios


def fetch_diario_details(diario_id, jwt_token):
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    
    params = {
        "_dc": get_timestamp(),
        "id": diario_id,
        "page": 1,
        "start": 0,
        "limit": 25
    }
    
    response = requests.get(DIARIO_DETAILS_URL, headers=headers, params=params, verify=False)
    
    if response.status_code == 200:
        data = response.json()
        return data.get("data", {})
    else:
        print(f"Error fetching diario details for ID {diario_id}: {response.status_code}")
        return {}

def save_diario_entries(patient_id, diary_entries, jwt_token, diary_type=13):
    """
    Save all fetched diary entries into the appropriate table based on diary type.
    """
    if not diary_entries:
        print(f"🚨 No diary entries found for type {diary_type}. Nothing to save.")
        return

    conn = sqlite3.connect("borromea.db")
    cursor = conn.cursor()

    # Map diary_type to table name
    table_map = {
        13: "diario_medico",
        14: "diario_infermieristico",
        15: "diario_sociale",
        16: "diario_assistenziale",
        17: "diario_riabilitativo"
    }
    
    table_name = table_map.get(diary_type, "diario_medico")  # Default to medico if unknown

    print(f"💾 Saving {len(diary_entries)} diary entries into {table_name}...")

    for entry in diary_entries:
        diario_id = entry["id"]
        details = fetch_diario_details(diario_id, jwt_token)

        print(f"🔍 Inserting Diario ID: {diario_id} into {table_name}")

        query = f"""
        INSERT OR REPLACE INTO {table_name} (
            diario_id, patient_id, data, compilatore, compilatoreNominativo, 
            compilatoreFigProf, note, eventoAcuto, eventoEvidenzia, riservato,
            indicazioniAss, codPatologia, alimentaPrePai, alimentaPrePti, alimentaPrePri,
            tipoBlocco, permessiAnnulla
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        values = (
            diario_id, patient_id, entry["data"], entry["compilatore"],
            details.get("compilatoreNominativo"), details.get("compilatoreFigProf"),
            details.get("note"), details.get("eventoAcuto"),
            details.get("eventoEvidenzia"), details.get("riservato"),
            details.get("indicazioniAss"), details.get("codPatologia"),
            details.get("alimentaPrePai"), details.get("alimentaPrePti"),
            details.get("alimentaPrePri"),
            json.dumps(entry.get("tipoBlocco", [])),  
            json.dumps(entry.get("permessiAnnulla", []))
        )

        try:
            cursor.execute(query, values)
        except sqlite3.Error as e:
            print(f"❌ SQLite Error: {e}")

    conn.commit()
    conn.close()
    print(f"✅ {len(diary_entries)} entries saved in {table_name}.")
