import sqlite3
import requests
import json
import time
import sys
from datetime import datetime, timezone

# API Endpoints
FALLS_LIST_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/testate/get"
FALLS_PREV_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/testate/prev"
FALLS_DETAILS_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/eventi/cadute/get"

# Function to generate a timestamp
def get_timestamp():
    return str(int(time.time() * 1000))

def get_current_time():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

def save_fall_data(patient_id, patient_name, testate_data, details_data):
    """Saves fall data into the SQLite database dynamically."""
    conn = sqlite3.connect("borromea.db")
    cursor = conn.cursor()

    for fall in testate_data:
        fall_id = fall["id"]
        fall_date = fall["data"]
        details = details_data.get(fall_id, {})
        fall_data = details.get("data", {})

        # Convert lists into strings for storage
        tipoBlocco = ", ".join([f"{t['codice']}:{t['valore']} ({t['extra']})" for t in fall_data.get("tipoBlocco", [])]) if fall_data.get("tipoBlocco") else None
        permessiAnnulla = ", ".join(map(str, fall_data.get("permessiAnnulla", []))) if fall_data.get("permessiAnnulla") else None
        testimoni = ", ".join([t["nome"] for t in fall_data.get("testimoni", [])]) if fall_data.get("testimoni") else None
        operatori = ", ".join([o["nome"] for o in fall_data.get("operatori", [])]) if fall_data.get("operatori") else None
        listaCompilatori = ", ".join([c["compilatoreNominativo"] for c in fall_data.get("listaCompilatori", [])]) if fall_data.get("listaCompilatori") else None
        history = ", ".join([json.dumps(item) for item in fall_data.get("history", [])]) if fall_data.get("history") else None

        # Dictionary storing column names and corresponding values
        fall_data_dict = {
            "fall_id": fall_id,
            "patient_id": patient_id,
            "data": fall_date,
            "deletedData": fall_data.get("deletedData"),
            "hashAnnulla": fall_data.get("hashAnnulla"),
            "tipoBlocco": tipoBlocco,
            "bozza": fall_data.get("bozza"),
            "permessiAnnulla": permessiAnnulla,
            "hashConvalidatore": fall_data.get("hashConvalidatore"),
            "codEnte": fall_data.get("codEnte"),
            "tipoScheda": fall_data.get("tipoScheda"),
            "compilatore": fall_data.get("compilatore"),
            "deambulante": fall_data.get("deambulante"),
            "ausili": fall_data.get("ausili"),
            "ausiliAltro": fall_data.get("ausiliAltro"),
            "apparecchioAcustico": fall_data.get("apparecchioAcustico"),
            "occhiali": fall_data.get("occhiali"),
            "altraProtesi": fall_data.get("altraProtesi"),
            "presenzaTestimoni": fall_data.get("presenzaTestimoni"),
            "luogoCaduta": fall_data.get("luogoCaduta"),
            "luogoCadutaAltro": fall_data.get("luogoCadutaAltro"),
            "codSede": fall_data.get("codSede"),
            "codReparto": fall_data.get("codReparto"),
            "illuminazione": fall_data.get("illuminazione"),
            "ostacoli": fall_data.get("ostacoli"),
            "ostacoliTipo": fall_data.get("ostacoliTipo"),
            "tipoPavimento": fall_data.get("tipoPavimento"),
            "fattoreAmbientaleAltro": fall_data.get("fattoreAmbientaleAltro"),
            "fattoreAmbientaleAltroDescr": fall_data.get("fattoreAmbientaleAltroDescr"),
            "attivitaSvolta": fall_data.get("attivitaSvolta"),
            "calzatura": fall_data.get("calzatura"),
            "calzaturaAllacciata": fall_data.get("calzaturaAllacciata"),
            "calzaturaAltro": fall_data.get("calzaturaAltro"),
            "contenzione": fall_data.get("contenzione"),
            "patologiaAcuta": fall_data.get("patologiaAcuta"),
            "demenza": fall_data.get("demenza"),
            "sedazione": fall_data.get("sedazione"),
            "cadutePrecedenti": fall_data.get("cadutePrecedenti"),
            "cadutePrecedentiQuando": fall_data.get("cadutePrecedentiQuando"),
            "descrizioneCaduta": fall_data.get("descrizioneCaduta"),
            "fratture": fall_data.get("fratture"),
            "prontoSoccorso": fall_data.get("prontoSoccorso"),
            "conseguenzeCaduta": fall_data.get("conseguenzeCaduta"),
            "altraProtesiDescr": fall_data.get("altraProtesiDescr"),
            "testimoniOperatori": fall_data.get("testimoniOperatori"),
            "apparecchioAcusticoInUso": fall_data.get("apparecchioAcusticoInUso"),
            "occhialiInUso": fall_data.get("occhialiInUso"),
            "altraProtesiInUso": fall_data.get("altraProtesiInUso"),
            "attivitaSvoltaDescr": fall_data.get("attivitaSvoltaDescr"),
            "codStanza": fall_data.get("codStanza"),
            "contenzioneTipo": fall_data.get("contenzioneTipo"),
            "farmaciAssunti": fall_data.get("farmaciAssunti"),
            "provvedimenti": fall_data.get("provvedimenti"),
            "conseguenze": fall_data.get("conseguenze"),
            "provv": fall_data.get("provv"),
            "progrEpilessia": fall_data.get("progrEpilessia"),
            "tipologiaCaduta": fall_data.get("tipologiaCaduta"),
            "modalitaCaduta": fall_data.get("modalitaCaduta"),
            "autoreSegn": fall_data.get("autoreSegn"),
            "idRicovero": fall_data.get("idRicovero"),
            "descAnte": fall_data.get("descAnte"),
            "tipoCaduta": fall_data.get("tipoCaduta"),
            "evento": fall_data.get("evento"),
            "nominativo": fall_data.get("nominativo"),
            "compilatoreNominativo": fall_data.get("compilatoreNominativo"),
            "compilatoreFigProf": fall_data.get("compilatoreFigProf"),
            "testimoni": testimoni,
            "operatori": operatori,
            "listaCompilatori": listaCompilatori,
            "dataUltimaCaduta": fall_data.get("dataUltimaCaduta"),
            "history": history,
            "operatore": fall_data.get("operatore"),
        }

        # Dynamically build SQL query
        columns = ", ".join(fall_data_dict.keys())
        placeholders = ", ".join(["?" for _ in fall_data_dict.keys()])
        values = tuple(fall_data_dict.values())

        # Execute SQL dynamically
        cursor.execute(f"""
            INSERT OR REPLACE INTO falls ({columns})
            VALUES ({placeholders});
        """, values)

    conn.commit()
    conn.close()
    print("✅ All falls saved successfully!")

def fetch_falls(patient_id, patient_name, jwt_token):
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    all_falls = []
    known_fall_ids = set()
    fall_details = {}  # Store detailed fall data

    params_list = {
        "_dc": get_timestamp(),
        "tipoTestata": "Caduta",
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

    response = requests.get(FALLS_LIST_URL, headers=headers, params=params_list, verify=False)

    if response.status_code == 401:
        print("🔄 Token expired during fall list fetch. Refreshing...")
        from helpers.auth import refresh_jwt_token
        jwt_token = refresh_jwt_token()
        headers["CBA-JWT"] = f"Bearer {jwt_token}"
        response = requests.get(FALLS_LIST_URL, headers=headers, params=params_list, verify=False)

    if response.status_code == 200:
        data = response.json()
        if "data" in data and data["data"]:
            for fall in data["data"]:
                fall_id = fall["id"]
                if fall_id not in known_fall_ids:
                    all_falls.append(fall)
                    known_fall_ids.add(fall_id)
            print(f"✅ Initial Falls Retrieved: {len(data['data'])}")
        else:
            print("🚨 No falls found!")
            return all_falls
    else:
        print(f"⚠️ Error fetching falls! Status Code: {response.status_code}")
        return all_falls

    # Fetch previous falls if needed
    while len(all_falls) < 6:
        last_fall = all_falls[-1]
        last_id = last_fall["id"]
        last_date = last_fall["data"].replace(" ", "T")

        params_prev = {
            "_dc": get_timestamp(),
            "id": last_id,
            "data": last_date,
            "tipoTestata": "Caduta",
            "idRicovero": patient_id,
            "idProfilo": 3,
            "compilatore": 27,
            "al": get_current_time()
        }

        response = requests.get(FALLS_PREV_URL, headers=headers, params=params_prev, verify=False)

        if response.status_code == 401:
            print("🔄 Token expired during previous fall fetch. Refreshing...")
            from helpers.auth import refresh_jwt_token
            jwt_token = refresh_jwt_token()
            headers["CBA-JWT"] = f"Bearer {jwt_token}"
            response = requests.get(FALLS_PREV_URL, headers=headers, params=params_prev, verify=False)

        if response.status_code == 200:
            prev_data = response.json()
            if "data" in prev_data and prev_data["data"]:
                new_fall = prev_data["data"][0]
                if new_fall["id"] not in known_fall_ids:
                    all_falls.append(new_fall)
                    known_fall_ids.add(new_fall["id"])
                    print(f"✅ Retrieved Previous Fall: {new_fall['data']} (Total: {len(all_falls)})")
                else:
                    break
            else:
                break
        else:
            print(f"⚠️ Error fetching previous falls! Status Code: {response.status_code}")
            break

    # Fetch detailed data and store it in the dictionary
    print("🔍 Fetching detailed data for each fall...")
    for fall in all_falls:
        fall_id = fall["id"]
        details = fetch_fall_details(fall_id, jwt_token)
        if details:
            fall_details[fall_id] = details

    # Save everything to database
    save_fall_data(patient_id, patient_name, all_falls, fall_details)

    print(f"\n✅ Total Falls Retrieved: {len(all_falls)}")
    return all_falls

# Function to fetch full fall details
def fetch_fall_details(fall_id, jwt_token):
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    params = {
        "_dc": get_timestamp(),
        "id": fall_id,
        "page": 1,
        "start": 0,
        "limit": 25
    }
    
    response = requests.get(FALLS_DETAILS_URL, headers=headers, params=params, verify=False)

    if response.status_code == 401:
        print("🔄 Token expired while fetching fall details. Refreshing...")
        from helpers.auth import refresh_jwt_token
        jwt_token = refresh_jwt_token()
        headers["CBA-JWT"] = f"Bearer {jwt_token}"
        response = requests.get(FALLS_DETAILS_URL, headers=headers, params=params, verify=False)

    print(f"📡 Fetching details for Fall ID {fall_id}")

    try:
        detailed = response.json()
        return detailed  # Return data instead of just printing
    except Exception as e:
        print(f"⚠️ Error parsing detailed response for Fall ID {fall_id}: {e}")
        return None
