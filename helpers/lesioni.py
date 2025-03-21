import sqlite3
import requests
import json
import time
from datetime import datetime, timezone

# API Endpoints
LESIONI_LIST_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/testate/get"
LESIONI_PREV_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/testate/prev"
LESIONI_DETAILS_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/eventi/lesioni/get"
LESIONI_DETTAGLIO_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/eventi/lesioni/dettaglio/get"
LESIONI_MEDICAZIONI_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/medicazioni/get"


def get_timestamp():
    return str(int(time.time() * 1000))

def get_current_time():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

def save_lesioni_data(patient_id, patient_name, testate_data, details_data):
    """Saves lesion data into the SQLite database, including details & medications."""
    conn = sqlite3.connect("borromea.db")
    cursor = conn.cursor()

    for les in testate_data:
        les_id = les["id"]
        les_date = les["data"]
        details = details_data.get(les_id, {}).get("lesione", {})
        dettaglio = details_data.get(les_id, {}).get("dettaglio", {})
        medicazione = details_data.get(les_id, {}).get("medicazione", {})

        # 🔹 Save to lesioni table (main lesion details)
        les_data_dict = {
            "lesione_id": les_id,
            "patient_id": patient_id,
            "data": les_date,
            "dataFine": details.get("dataFine"),
            "sedeLesione": details.get("sedeLesione"),
            "sedeLesioneDecod": details.get("sedeLesioneDecod"),
            "compilatore": details.get("compilatore"),
            "compilatoreNominativo": details.get("compilatoreNominativo"),
            "compilatoreFigProf": details.get("compilatoreFigProf"),
            "dataRecenteDett": details.get("dataRecenteDett"),
            "dataFineFormatted": details.get("dataFineFormatted"),
            "dataFormatted": details.get("dataFormatted"),
            "idUltimoDett": details.get("idUltimoDett"),
            "idUltimaMedicazioneV1": details.get("idUltimaMedicazioneV1")
        }

        cursor.execute(f"""
            INSERT OR REPLACE INTO lesioni ({", ".join(les_data_dict.keys())})
            VALUES ({", ".join(["?" for _ in les_data_dict.keys()])});
        """, tuple(les_data_dict.values()))

        # 🔹 Save to lesioni_dettagli table (detailed lesion measurements)
        if dettaglio:
            dettaglio_data_dict = {
                "dettaglio_id": dettaglio.get("id"),
                "lesione_id": les_id,
                "data": dettaglio.get("data"),
                "lunghezza": dettaglio.get("lunghezza"),
                "larghezza": dettaglio.get("larghezza"),
                "profondita": dettaglio.get("profondita"),
                "superficie": dettaglio.get("superficie"),
                "stadio": dettaglio.get("stadio"),
                "tipoTessuto": dettaglio.get("tipoTessuto"),
                "essudato": dettaglio.get("essudato"),
                "compilatore": dettaglio.get("compilatore"),
                "compilatoreNominativo": dettaglio.get("compilatoreNominativo"),
                "compilatoreFigProf": dettaglio.get("compilatoreFigProf"),
                "lunghezza_s2": dettaglio.get("lunghezza_s2"),
                "larghezza_s2": dettaglio.get("larghezza_s2"),
                "profondita_s2": dettaglio.get("profondita_s2"),
                "stadioFormatted": dettaglio.get("stadioFormatted"),
                "numeroLesioni": dettaglio.get("numeroLesioni"),
            }

            cursor.execute(f"""
                INSERT OR REPLACE INTO lesioni_dettagli ({", ".join(dettaglio_data_dict.keys())})
                VALUES ({", ".join(["?" for _ in dettaglio_data_dict.keys()])});
            """, tuple(dettaglio_data_dict.values()))

        # 🔹 Save to lesioni_medicazioni table (lesion treatments)
        if medicazione:
            # 🔹 Save nested `lesioneMedDett` entries
            med_dett_list = medicazione.get("lesioneMedDett", [])
            for dett in med_dett_list:
                med_dett_dict = {
                    "id": dett.get("id"),
                    "idLesione": dett.get("idLesione"),
                    "idMedTe": dett.get("idMedTe"),
                    "idCassetto": dett.get("idCassetto"),
                    "codArticolo": dett.get("codArticolo"),
                    "aic": dett.get("aic"),
                    "ordine": dett.get("ordine"),
                    "descrCassetto": dett.get("descrCassetto"),
                    "descrFarmacoFormatted": dett.get("descrFarmacoFormatted"),
                    "data": dett.get("data"),
                    "compilatore": dett.get("compilatore"),
                    "idRicovero": dett.get("idRicovero"),
                }

                cursor.execute(f"""
                    INSERT OR REPLACE INTO lesione_med_dettagli ({", ".join(med_dett_dict.keys())})
                    VALUES ({", ".join(["?" for _ in med_dett_dict])});
                """, tuple(med_dett_dict.values()))

    conn.commit()
    conn.close()
    print("✅ All lesioni, dettagli, and medicazioni saved successfully!")

def fetch_lesione_details(les_id, jwt_token):
    """Fetches full lesion details, including dettaglio and medicazione"""
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    # Step 1: Fetch main lesion details
    params = {"_dc": get_timestamp(), "id": les_id, "page": 1, "start": 0, "limit": 25}
    response = requests.get(LESIONI_DETAILS_URL, headers=headers, params=params, verify=False)

    if response.status_code != 200:
        print(f"⚠️ Error fetching lesion details for ID {les_id}. Status: {response.status_code}")
        return None

    lesione_data = response.json().get("data", {})

    # Step 2: Fetch `dettaglio` (detailed lesion metrics)
    dettaglio_data = {}
    dettaglio_id = lesione_data.get("idUltimoDett")
    if dettaglio_id:
        params_dettaglio = {"_dc": get_timestamp(), "id": dettaglio_id, "page": 1, "start": 0, "limit": 25}
        response_dettaglio = requests.get(LESIONI_DETTAGLIO_URL, headers=headers, params=params_dettaglio, verify=False)

        if response_dettaglio.status_code == 200:
            dettaglio_data = response_dettaglio.json().get("data", {})
        else:
            print(f"⚠️ Error fetching dettaglio for lesion {les_id}. Status: {response_dettaglio.status_code}")

    # Step 3: Fetch `medicazioni` (medications/treatment details)
    medicazione_data = {}
    medicazione_id = lesione_data.get("idUltimaMedicazioneV1")
    if medicazione_id:
        params_medicazione = {"_dc": get_timestamp(), "id": medicazione_id, "page": 1, "start": 0, "limit": 25}
        response_medicazione = requests.get(LESIONI_MEDICAZIONI_URL, headers=headers, params=params_medicazione, verify=False)

        if response_medicazione.status_code == 200:
            medicazione_data = response_medicazione.json().get("data", {})
        else:
            print(f"⚠️ Error fetching medicazione for lesion {les_id}. Status: {response_medicazione.status_code}")

    return {
        "lesione": lesione_data,
        "dettaglio": dettaglio_data,
        "medicazione": medicazione_data
    }

def fetch_lesioni(patient_id, patient_name, jwt_token):
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    all_lesioni = []
    known_ids = set()
    details_data = {}

    params_list = {
        "_dc": get_timestamp(),
        "tipoTestata": "Lesione",
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

    response = requests.get(LESIONI_LIST_URL, headers=headers, params=params_list, verify=False)

    if response.status_code == 200:
        data = response.json()
        for les in data.get("data", []):
            les_id = les["id"]
            if les_id not in known_ids:
                all_lesioni.append(les)
                known_ids.add(les_id)
    else:
        print(f"⚠️ Error fetching lesioni list! Status: {response.status_code}")
        return []

    # 🔄 Keep fetching previous records until `first == "T"`
    while True:
        last = all_lesioni[-1]
        last_id = last["id"]
        last_date = last["data"].replace(" ", "T")

        params_prev = {
            "_dc": get_timestamp(),
            "id": last_id,
            "data": last_date,
            "tipoTestata": "Lesione",
            "idRicovero": patient_id,
            "idProfilo": 3,
            "compilatore": 27
        }

        response = requests.get(LESIONI_PREV_URL, headers=headers, params=params_prev, verify=False)

        if response.status_code != 200:
            print(f"⚠️ Error fetching previous lesioni! Status: {response.status_code}")
            break

        prev_data = response.json()
        if not prev_data.get("data"):
            print("❌ No more previous lesioni found. Stopping.")
            break

        new_entry = prev_data["data"][0]
        print(f"🔍 Found previous lesione: ID {new_entry['id']} - Date {new_entry['data']}")

        if new_entry["id"] in known_ids:
            print("⛔ Already known ID. Stopping.")
            break

        all_lesioni.append(new_entry)
        known_ids.add(new_entry["id"])

        if new_entry.get("first") == "T":
            print("🔚 Reached the first recorded lesione. Stopping.")
            break

    print(f"✅ Total lesioni fetched: {len(all_lesioni)}")

    # Fetch details for each lesione
    for les in all_lesioni:
        les_id = les["id"]
        details = fetch_lesione_details(les_id, jwt_token)
        if details:
            details_data[les_id] = details

    save_lesioni_data(patient_id, patient_name, all_lesioni, details_data)
    return all_lesioni
