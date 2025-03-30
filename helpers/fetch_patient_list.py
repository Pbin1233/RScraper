import sqlite3
import requests
import time
from dotenv import load_dotenv
from helpers.auth import get_jwt_token_selenium  # Import authentication

# Load environment variables
load_dotenv()

# API Endpoint
PATIENT_LIST_URL = "https://pvc03.cbacloud.it:4445/cba/css/cs/ws/anagrafica/list"
DB_NAME = "borromea.db"

def get_timestamp():
    return str(int(time.time() * 1000))

def get_current_time():
    return time.strftime("%Y-%m-%dT%H:%M:%S")

def fetch_patient_list(jwt_token):
    """Fetches all patient data from API and stores necessary fields."""
    
    headers = {
        "Accept": "*/*",
        "CBA-JWT": f"Bearer {jwt_token}",
        "User-Agent": "Mozilla/5.0",
        "Referer": PATIENT_LIST_URL,
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "X-Requested-With": "XMLHttpRequest"
    }

    patients = []
    first_result = 0
    max_results = 80

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    while True:
        params = {
            '_dc': get_timestamp(),
            'idProfilo': '3',
#            'dal': get_current_time(),
#            'al': get_current_time(),
            'contiene': 'F',
            'maxResults': str(max_results),
            'filtroSettori': 'F',
            'ancheNonAttivi': 'T',
            'filtroMedico': 'F',
            'firstResult': str(first_result),
        }

        print(f"🔗 Fetching patients {first_result} to {first_result + max_results}...")

        response = requests.get(PATIENT_LIST_URL, params=params, headers=headers, verify=False)

        if response.status_code != 200:
            print(f"❌ Failed to retrieve patient data! Status Code: {response.status_code}")
            return None

        result = response.json()

        if not result.get("success"):
            print(f"API response indicated failure: {result.get('message')}")
            return None

        batch = result.get("data", [])
        if not batch:
            print("✅ All patients retrieved!")
            break  # No more patients to fetch, exit loop

        patients.extend(batch)

        # ✅ Store patient data into the database
        for patient in batch:
            cursor.execute("""
                INSERT OR REPLACE INTO patients (
                    codOspite, idRicovero, nome, cognome, sesso, dataNascita, 
                    codiceFiscale, idProfilo, descrProfilo, idSede, idReparto, dal, al, attivo
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                patient.get("codOspite"),
                patient.get("idRicovero"),
                patient.get("nome"),
                patient.get("cognome"),
                patient.get("sesso"),
                patient.get("dataNascita"),
                patient.get("codFisc"),
                patient.get("idProfilo"),
                patient.get("descrProfilo"),
                patient.get("idSede"),
                patient.get("idReparto"),
                patient.get("dal"),
                patient.get("al"),
                patient.get("attivo")
            ))

        first_result += max_results  # Move to next batch

    conn.commit()
    conn.close()

    print(f"📋 Total Patients Retrieved: {len(patients)}")
    return patients

if __name__ == "__main__":
    jwt_token = get_jwt_token_selenium()
    if jwt_token:
        fetch_patient_list(jwt_token)
