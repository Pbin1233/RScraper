import requests
import json
import time
from datetime import datetime
import sqlite3

# API Endpoint for alternative diary retrieval
ALTERNATIVE_DIARIO_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/portlet/diarioparametri/get"

# API Endpoint
ALTERNATIVE_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/portlet/diarioparametri/get"

# Function to generate a timestamp
def get_timestamp():
    return str(int(time.time() * 1000))

def get_current_time():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

def fetch_data(patient_id, jwt_token, is_diary, start_date="2020-06-01T00:00:00", end_date=get_current_time(), limit=25):
    """
    Fetch all diary or vitals entries using the alternative API.
    Handles pagination using `idDiarioLimit` and `dateDiarioLimit` for diaries, 
    or `idParametriLimit` and `dateParametriLimit` for vitals.
    """
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    all_entries = []
    known_ids = set()
    has_next = True
    id_limit = None
    date_limit = None

    while has_next:
        params = {
            "_dc": get_timestamp(),
            "idRicovero": patient_id,
            "idProfiloPwdDe": 20,
            "idProfilo": 3,
            "dal": start_date,
            "al": get_current_time(),
            "maxResults": 200,
            "soloWarning": "false",
            "parametri": "true" if not is_diary else "false",
            "diari": "true" if is_diary else "false",
            "daCompletare": "false",
            "indicazioniAss": "false" if not is_diary else "true",  # Adjust based on type
            "parolaChiave": "",
            "next": "true",
            "prev": "false",
            "page": 1,
            "limit": limit
        }

        # Apply correct pagination parameters
        if id_limit and date_limit:
            if is_diary:
                params["idDiarioLimit"] = id_limit
                params["dateDiarioLimit"] = date_limit
            else:
                params["idParametriLimit"] = id_limit
                params["dateParametriLimit"] = date_limit

        response = requests.get(ALTERNATIVE_URL, headers=headers, params=params, verify=False)

        print(f"\n📡 Request Params: {json.dumps(params, indent=2)}")

        if response.status_code == 200:
            data = response.json()
            print(f"📥 API Response:\n{json.dumps(data, indent=2)}")

            if "data" in data and "lista" in data["data"]:
                new_entries = data["data"]["lista"]

                for entry in new_entries:
                    entry_id = entry["id"]
                    if entry_id not in known_ids:
                        all_entries.append(entry)
                        known_ids.add(entry_id)

                print(f"✅ Retrieved {len(new_entries)} entries.")

                # Check pagination flag
                has_next = data["data"].get("hasNext", False)

                # Update pagination parameters for next request
                if new_entries:
                    last_entry = new_entries[-1]
                    id_limit = last_entry["id"]
                    date_limit = last_entry["dataOra"].replace(" ", "T")

            else:
                print("🚨 No more entries found!")
                break
            
        if response.status_code == 401:
            raise requests.exceptions.HTTPError("Token expired", response=response)
        elif response.status_code != 200:
            print(f"❌ Error fetching data! Status Code: {response.status_code}, Response: {response.text}")
            break

    return all_entries

# Dictionary mapping diary types to their correct tables
diary_types = {
    13: "diario_medico",
    14: "diario_infermieristico",
    15: "diario_sociale",
    16: "diario_assistenziale",
    17: "diario_riabilitativo"
}

def save_data(patient_id, entries, is_diary):
    """
    Save fetched data into the correct table: diaries go to their respective tables, vitals go to `vitals_alternative`.
    """
    if not entries:
        print("🚨 No entries found. Nothing to save.")
        return

    conn = sqlite3.connect("borromea.db")
    cursor = conn.cursor()

    rows_inserted = 0  # Track number of rows inserted

    for entry in entries:
        if is_diary:
            diary_type = entry.get("idTipoDiario")
            table_name = diary_types.get(diary_type, "diario_medico")  # ✅ correct mapping

            query = f"""
            INSERT OR REPLACE INTO {table_name} (
                id, patient_id, idRicovero, compilatoreNominativo, compilatoreFigProf, tipo,
                nomeForm, dataOra, testoDiario, coloreS2, coloreLabel, tipologia  -- ✅ Added tipologia
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """

            values = (
                entry["id"], patient_id, entry["idRicovero"], entry["compilatoreNominativo"],
                entry["compilatoreFigProf"], entry["tipo"], entry["nomeForm"], entry["dataOra"],
                entry["testoDiario"], entry["coloreS2"], entry["coloreLabel"], entry.get("tipologia")  # ✅ Include tipologia
            )

        else:
            table_name = "vitals_alternative"

            query = f"""
            INSERT OR REPLACE INTO vitals_alternative (
                id, patient_id, idRicovero, compilatoreNominativo, compilatoreFigProf, nomeForm, dataOra,
                pressioneMaxOrto, pressioneMinOrto, pressioneMaxClino, pressioneMinClino,
                pressioneMaxNoSpec, pressioneMinNoSpec, frequenza, freqRespiratoria, temperatura, curvaGli, peso,
                spo2, spo2ot, spo2NoSpec, oSpo2ot, diuresi, alvo, sonno, mobilita, comportamento,
                comportamentoAttivita, avpu, altezza, tipoRespirazione, tipoFreqCardiaca, dolore, bmi, inr, ciclo,
                warningPressioneMaxOrto, warningPressioneMinOrto, warningPressioneMaxClino, warningPressioneMinClino,
                warningFrequenza, warningFreqRespiratoria, warningTemperatura, warningCurvaGli, warningPeso,
                warningSpo2, warningSpo2ot, warningDiuresi, warningAlvo, warningSonno, warningMobilita,
                warningComportamento, warningTipoRespirazione, warningTipoFreqCardiaca, warningBmi, warningInr,
                testAlcool, testDroga, testGravidanza, descrizioneDroga, turno, tipologia, listIndex
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """

            values = (
                entry["id"], patient_id, entry["idRicovero"], entry["compilatoreNominativo"],
                entry["compilatoreFigProf"], entry["nomeForm"], entry["dataOra"],
                entry.get("pressioneMaxOrto"), entry.get("pressioneMinOrto"),
                entry.get("pressioneMaxClino"), entry.get("pressioneMinClino"),
                entry.get("pressioneMaxNoSpec"), entry.get("pressioneMinNoSpec"),
                entry.get("frequenza"), entry.get("freqRespiratoria"), entry.get("temperatura"),
                entry.get("curvaGli"), entry.get("peso"), entry.get("spo2"), entry.get("spo2ot"),
                entry.get("spo2NoSpec"), entry.get("oSpo2ot"), entry.get("diuresi"), entry.get("alvo"),
                entry.get("sonno"), entry.get("mobilita"), entry.get("comportamento"),
                entry.get("comportamentoAttivita"), entry.get("avpu"), entry.get("altezza"),
                entry.get("tipoRespirazione"), entry.get("tipoFreqCardiaca"), entry.get("dolore"),
                entry.get("bmi"), entry.get("inr"), entry.get("ciclo"),
                entry.get("warningPressioneMaxOrto"), entry.get("warningPressioneMinOrto"),
                entry.get("warningPressioneMaxClino"), entry.get("warningPressioneMinClino"),
                entry.get("warningFrequenza"), entry.get("warningFreqRespiratoria"),
                entry.get("warningTemperatura"), entry.get("warningCurvaGli"), entry.get("warningPeso"),
                entry.get("warningSpo2"), entry.get("warningSpo2ot"), entry.get("warningDiuresi"),
                entry.get("warningAlvo"), entry.get("warningSonno"), entry.get("warningMobilita"),
                entry.get("warningComportamento"), entry.get("warningTipoRespirazione"),
                entry.get("warningTipoFreqCardiaca"), entry.get("warningBmi"), entry.get("warningInr"),
                entry.get("testAlcool"), entry.get("testDroga"), entry.get("testGravidanza"),
                entry.get("descrizioneDroga"), entry.get("turno"), entry.get("tipologia"),
                entry.get("listIndex")
            )


        print(f"\n🔍 Executing Query for {table_name}...\n")

        try:
            cursor.execute(query, values)
            rows_inserted += cursor.rowcount
        except sqlite3.Error as e:
            print(f"❌ SQLite Error: {e}")

    conn.commit()
    conn.close()
    print(f"✅ {rows_inserted} rows successfully inserted into {table_name}.")
