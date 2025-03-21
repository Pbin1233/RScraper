import requests
import sqlite3
import time
from datetime import datetime

# API Endpoints
TESTATE_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/testate/get"
VITALS_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/parametri/visite/get"
VITALS_HISTORY_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/testate/prev"

def get_timestamp():
    return str(int(time.time() * 1000))

def fetch_vitals(patient_id, jwt_token):
    """Fetches vitals dynamically and retries if token expires."""
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    try:
        vitals_records = fetch_testate_vitals(patient_id, jwt_token, headers)

        if not vitals_records:
            print(f"🚨 No vitals records found for patient {patient_id}")
            return

        for vitals in vitals_records:
            print(f"🩺 Fetching detailed vitals for ID: {vitals['id']}")
            fetch_vitals_details(patient_id, vitals['id'], jwt_token, headers)

        print("📜 Fetching historical vitals records...")
        fetch_previous_vitals(patient_id, vitals_records[-1], jwt_token, headers)

    except requests.exceptions.RequestException as e:
        if "401" in str(e):  # Detect Unauthorized error
            jwt_token = refresh_jwt_token()  # Refresh token
            fetch_vitals(patient_id, jwt_token)  # Retry with new token
        else:
            print(f"⚠️ Unexpected error: {e}")

def fetch_testate_vitals(patient_id, jwt_token, headers):
    """Fetches testate data for vitals and retries if token expires."""
    params = {
        "_dc": get_timestamp(),
        "al": datetime.utcnow().isoformat(),
        "tipoTestata": "Visite",
        "idRicovero": patient_id,
        "idProfilo": 3,
        "compilatore": 27,
        "soloUnaTestata": "F",
        "extraParams": "",
        "page": 1,
        "start": 0,
        "limit": 25
    }

    response = requests.get(TESTATE_URL, headers=headers, params=params, verify=False)
    
    if response.status_code == 401:
        jwt_token = refresh_jwt_token()
        return fetch_testate_vitals(patient_id, jwt_token, headers)  # Retry
    
    if response.status_code == 200:
        data = response.json()
        return data.get("data", [])
    
    print(f"⚠️ Error fetching testate data! Status Code: {response.status_code}")
    return []


def fetch_vitals_details(patient_id, vitals_id, jwt_token, headers):
    """Fetches detailed vitals data for a specific ID."""
    
    params = {
        "_dc": get_timestamp(),
        "id": vitals_id,
        "idProfiloPwdDeCss": 20,
        "page": 1,
        "start": 0,
        "limit": 25
    }

    response = requests.get(VITALS_URL, headers=headers, params=params, verify=False)
    
    if response.status_code == 200:
        data = response.json()
        
        if "data" in data and data["data"]:
            save_vitals(patient_id, data["data"])
        else:
            print(f"🚨 No detailed vitals found for ID {vitals_id}")
    else:
        print(f"⚠️ Error fetching vitals details! Status Code: {response.status_code}")

def fetch_previous_vitals(patient_id, last_vitals, jwt_token, headers):
    """Fetches previous vitals records dynamically using pagination."""
    
    known_vitals_ids = set()
    all_vitals = []
    
    last_id = last_vitals["id"]
    last_date = last_vitals["data"]

    while True:
        params = {
            "_dc": get_timestamp(),
            "id": last_id,
            "data": last_date.replace(" ", "T"),
            "tipoTestata": "Visite",
            "idRicovero": patient_id,
            "idProfilo": 3,
            "compilatore": 27
        }

        response = requests.get(VITALS_HISTORY_URL, headers=headers, params=params, verify=False)

        if response.status_code == 200:
            data = response.json()
            if "data" in data and data["data"]:
                new_vitals = data["data"][0]
                vitals_id = new_vitals["id"]

                if vitals_id in known_vitals_ids:
                    break  # Stop if duplicate ID is found

                all_vitals.append(new_vitals)
                known_vitals_ids.add(vitals_id)

                print(f"✅ Retrieved past vitals data (ID: {vitals_id})")
                fetch_vitals_details(patient_id, vitals_id, jwt_token, headers)  # Fetch details

                last_id = vitals_id  # Move to next past record
                last_date = new_vitals["data"]

            else:
                break  # No more past vitals available
        else:
            print(f"⚠️ Error fetching past vitals! Status Code: {response.status_code}")
            break

def save_vitals(patient_id, vitals_data):
    """Saves vitals data into the SQLite database."""
    conn = sqlite3.connect("borromea.db")
    cursor = conn.cursor()

    for vitals in (vitals_data if isinstance(vitals_data, list) else [vitals_data]):
        vitals_entry = {
            "patient_id": patient_id,
            "idRicovero": vitals.get("idRicovero"),
            "data": vitals.get("data"),
            "compilatore": vitals.get("compilatore"),
            "compilatoreNominativo": vitals.get("compilatoreNominativo", ""),
            "compilatoreFigProf": vitals.get("compilatoreFigProf", ""),
            "pressioneMaxOrto": vitals.get("pressioneMaxOrto"),
            "pressioneMinOrto": vitals.get("pressioneMinOrto"),
            "pressioneMaxClino": vitals.get("pressioneMaxClino"),
            "pressioneMinClino": vitals.get("pressioneMinClino"),
            "pressioneMaxNoSpec": vitals.get("pressioneMaxNoSpec"),
            "pressioneMinNoSpec": vitals.get("pressioneMinNoSpec"),
            "frequenza": vitals.get("frequenza"),
            "temperatura": vitals.get("temperatura"),
            "curvaGli": vitals.get("curvaGli"),
            "peso": vitals.get("peso"),
            "alvo": vitals.get("alvo"),
            "diuresi": vitals.get("diuresi"),
            "ossigeno": vitals.get("ossigeno"),
            "spo2": vitals.get("spo2"),
            "spo2NoSpec": vitals.get("spo2NoSpec"),
            "tipoRespirazione": vitals.get("tipoRespirazioneFormatted", ""),
            "tipoFreqCardiaca": vitals.get("tipoFreqCardiacaFormatted", ""),
            "note": vitals.get("note", ""),
            "sonno": vitals.get("sonnoFormatted", ""),
            "alimentazione": vitals.get("alimentazione"),
            "mobilita": vitals.get("mobilitaFormatted", ""),
            "dolore": vitals.get("dolore"),
            "freqRespiratoria": vitals.get("freqRespiratoria"),
            "spo2ot": vitals.get("spo2ot"),
            "oSpo2ot": vitals.get("oSpo2ot"),
            "comportamento": vitals.get("comportamentoFormatted", ""),
            "comportamentoAttivita": vitals.get("comportamentoAttivita"),
            "avpu": vitals.get("avpu"),
            "altezza": vitals.get("altezza"),
            "malattiaAcuta": vitals.get("malattiaAcuta"),
            "notePeso": vitals.get("notePeso"),
            "testDroghe": vitals.get("testDroghe"),
            "testDrogheDescr": vitals.get("testDrogheDescr"),
            "testAlcool": vitals.get("testAlcool"),
            "testGravidanza": vitals.get("testGravidanza"),
            "bmi": vitals.get("bmi"),
            "inr": vitals.get("inr"),
            "ciclo": vitals.get("ciclo"),
            "tipoFlusso": vitals.get("tipoFlussoFormatted", ""),
            "ulterioriParametri": vitals.get("ulterioriParametri"),
            "punteggioMMSE": vitals.get("punteggioMMSE"),
            "punteggioCDR": vitals.get("punteggioCDR"),
            "vas": vitals.get("vas"),
            "vrs": vitals.get("vrs"),
            "nrs": vitals.get("nrs"),
            "noppain": vitals.get("noppain"),
            "noppain55": vitals.get("noppain55"),
            "painad": vitals.get("painad"),
            "visualSkvalMust": vitals.get("visualSkvalMust"),
            "mews": vitals.get("mews"),
            "punteggioMews": vitals.get("punteggioMews"),
            "news": vitals.get("news"),
            "punteggioNews": vitals.get("punteggioNews"),
            "parametroATre": vitals.get("parametroATre"),
            "listaWarning": vitals.get("listaWarning")
        }

        columns = ", ".join(vitals_entry.keys())
        placeholders = ", ".join(["?" for _ in vitals_entry.keys()])
        values = tuple(vitals_entry.values())

        cursor.execute(f"""
            INSERT OR REPLACE INTO vitals ({columns})
            VALUES ({placeholders});
        """, values)

    conn.commit()
    conn.close()
    print(f"✅ Vitals data for patient {patient_id} saved successfully!")
