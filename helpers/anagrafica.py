import sqlite3
import requests
import json
import os
import time
from dotenv import load_dotenv
from helpers.auth import get_jwt_token_selenium

# Load environment variables
load_dotenv()

# API Endpoints
PERSONAL_DATA_URL = "https://pvc03.cbacloud.it:4445/cba/css/cs/ws/genOsp/users/get"
USER_ADDRESS_URL = "https://pvc03.cbacloud.it:4445/cba/css/cs/ws/genOsp/userAddress/cbox"
HOSPITALIZATION_URL = "https://pvc03.cbacloud.it:4445/cba/css/cs/ws/ricoveri/search"
RESIDENCE_URL = "https://pvc03.cbacloud.it:4445/cba/css/cs/ws/genOsp/residenza/search"
HOSPITAL_ASSIGNMENTS_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/genOsp/residenza/search"
CONTACTS_URL = "https://pvc03.cbacloud.it:4445/cba/css/cs/ws/genOsp/prsrif/get"
REGIONAL_PARAMS_URL = "https://pvc03.cbacloud.it:4445/cba/css/cs/ws/genOsp/parametriRegionali/get"
PATIENT_ABSENCES_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/assenze/listByUtente"


# SQLite database connection
DB_NAME = "borromea.db"

def request_access_to_patient(cod_ospite, jwt_token):
    """Request access to a patient's records."""
    url = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/consultazionecartella/new"
    payload = {
        "codOspite": cod_ospite,
        "richiedente": os.getenv("RICHIEDENTE_ID", "542"),
        "idOrganizzazione": os.getenv("ID_ORGANIZZAZIONE", "2")
    }
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    response = requests.post(url, headers=headers, json=payload, verify=False)
    result = response.json()
    if result.get("success"):
        print(f"📥 Access request submitted for codOspite {cod_ospite}. ID: {result['data'].get('id')}")
        return True
    else:
        print(f"❌ Failed to request access for codOspite {cod_ospite}")
        return False

def fetch_additional_info(url, params, jwt_token):
    """Helper function to fetch additional data from an API endpoint with retry on token expiration."""
    headers = {"CBA-JWT": f"Bearer {jwt_token}", "Content-Type": "application/json"}
    response = requests.get(url, headers=headers, params=params, verify=False)

    if response.status_code == 401:
        print("🔄 Token expired during additional info fetch. Refreshing...")
        from helpers.auth import refresh_jwt_token
        jwt_token = refresh_jwt_token()
        headers["CBA-JWT"] = f"Bearer {jwt_token}"
        response = requests.get(url, headers=headers, params=params, verify=False)

    return response.json().get("data", [])


def fetch_personal_data(selected_cod_ospite, jwt_token):
    """Fetch complete personal data for a patient using multiple API endpoints."""
    if not selected_cod_ospite:
        print(f"⚠️ No codOspite provided. Cannot fetch personal data.")
        return None

    headers = {"CBA-JWT": f"Bearer {jwt_token}", "Content-Type": "application/json"}
    params = {"_dc": str(int(time.time() * 1000)), "id": selected_cod_ospite, "page": 1, "start": 0, "limit": 25}

    response = requests.get(PERSONAL_DATA_URL, headers=headers, params=params, verify=False)

    if response.status_code == 401:
        print("🔄 Token expired during personal data fetch. Refreshing...")
        from helpers.auth import refresh_jwt_token
        jwt_token = refresh_jwt_token()
        headers["CBA-JWT"] = f"Bearer {jwt_token}"
        response = requests.get(PERSONAL_DATA_URL, headers=headers, params=params, verify=False)

    if response.status_code != 200 or not response.json().get("success"):
        print(f"⚠️ Failed to fetch personal data for codOspite {selected_cod_ospite}")
        return None

    personal_data = response.json().get("data", {})

    # If data is False, request access and retry once
    if personal_data is False:
        print(f"🔒 No access to patient {selected_cod_ospite}. Attempting to request access...")
        if request_access_to_patient(selected_cod_ospite, jwt_token):
            time.sleep(2)  # Optional: wait before retrying
            response = requests.get(PERSONAL_DATA_URL, headers=headers, params=params, verify=False)
            personal_data = response.json().get("data", {})
            if personal_data is False:
                print("❌ Still no access after request.")
                return None

    # Fetch Additional Details
    address_data = fetch_additional_info(USER_ADDRESS_URL, {"codOspite": selected_cod_ospite, "tipoIndirizzo": "R"}, jwt_token)
    hospitalization_data = fetch_additional_info(HOSPITALIZATION_URL, {"codospite": selected_cod_ospite, "soloTipologieAbilitate": "true"}, jwt_token)

    hospital = hospitalization_data[0] if hospitalization_data else {}
    residence_data = fetch_additional_info(RESIDENCE_URL, {"idRicovero": hospital.get("idRicoveroCU", None), "tipoRecord": "U"}, jwt_token)
    contacts_data = fetch_additional_info(CONTACTS_URL, {"codospite": selected_cod_ospite}, jwt_token)

    # Fetch Hospital Assignments
    assignments_data = fetch_additional_info(HOSPITAL_ASSIGNMENTS_URL, {"idRicovero": hospital.get("id", None)}, jwt_token)

    # Fetch Patient Absences
    absences_data = fetch_additional_info(PATIENT_ABSENCES_URL, {"idRicovero": hospital.get("id", "")}, jwt_token)

    # Fetch Regional Parameters
    regional_params = fetch_additional_info(REGIONAL_PARAMS_URL, {"idRicovero": hospital.get("idRicoveroCU", None)}, jwt_token)

    # Extract Key Data
    address = address_data[0]["valore"] if address_data else None
    residence = residence_data[0] if residence_data else {}
    regional_data = regional_params[0] if isinstance(regional_params, list) and len(regional_params) > 0 else {}

    # ✅ Fix: Ensure `contacts`, `assignments`, and `absences` are valid lists
    contacts = contacts_data if isinstance(contacts_data, list) else []
    assignments = assignments_data if isinstance(assignments_data, list) else []
    absences = absences_data if isinstance(absences_data, list) else []

    # Save to Database
    save_personal_data(personal_data, address, hospital, residence, regional_data, contacts, assignments, absences)

def save_personal_data(personal_data, address, hospital, residence, regional_data, contacts, assignments, absences):
    """Saves fetched personal data, emergency contacts, hospital assignments, and absences into SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        ### ✅ STEP 1: Save Personal Data
        cursor.execute("""
            INSERT OR REPLACE INTO personal_data (
                codOspite, nome, cognome, sesso, dataNascita, codiceFiscale,
                cittadinanza, comuneNascita, desComuneNascita, desProvinciaNascita, desNazioneNascita,
                statoCivile, gradoIstruzione, professione, telefono1, telefono2, email,

                -- Additional Fields
                codiceRegionale, codiceSanitario, lingua, testamento,
                codiceAccoglienza, codiceProfilo,

                -- Address & Residence
                indirizzo, cap, comune_residenza, provincia_residenza,

                -- Hospitalization
                ricovero_id, ricovero_dal, ricovero_al, tipo_ricovero,
                reparto, sede, idSede, idReparto,

                -- Regional Parameters
                idTipoProvenienza, motivoIngresso, iniziativaRichiesta, tipoRicovero,
                sosiaProfessione, sosiaSituazionePens
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            personal_data.get("codOspite"),
            personal_data.get("nome"),
            personal_data.get("cognome"),
            personal_data.get("sesso"),
            personal_data.get("dataNascita"),
            personal_data.get("codiceFiscale"),
            personal_data.get("cittadinanza"),
            personal_data.get("comuneNascita"),
            personal_data.get("desComuneNascita"),
            personal_data.get("desProvinciaNascita"),
            personal_data.get("desNazioneNascita"),
            personal_data.get("desStatoCivile"),
            personal_data.get("desGradoIstruzione"),
            personal_data.get("desProfessione"),
            personal_data.get("telefono1"),
            personal_data.get("telefono2"),
            personal_data.get("email"),

            # ✅ Additional Fields
            personal_data.get("codiceRegionale", ""),
            personal_data.get("codiceSanitario", ""),
            personal_data.get("lingua", ""),
            personal_data.get("testamento", ""),
            personal_data.get("codiceAccoglienza", ""),
            personal_data.get("codiceProfilo", ""),

            # ✅ Insert Address & Residence
            address,
            residence.get("cap", ""),
            residence.get("desComune", ""),
            residence.get("provincia", ""),

            # ✅ Insert Hospitalization Data
            hospital.get("id", ""),
            hospital.get("dal", ""),
            hospital.get("al", ""),
            hospital.get("tipoRicovero", ""),
            residence.get("desReparto", ""),
            residence.get("desSede", ""),
            residence.get("idSede", ""),
            residence.get("idReparto", ""),

            # ✅ Insert Regional Parameters
            regional_data.get("idTipoProvenienza", ""),
            regional_data.get("motivoIngresso", ""),
            regional_data.get("iniziativaRichiesta", ""),
            regional_data.get("tipoRicovero", ""),
            regional_data.get("sosiaProfessione", ""),
            regional_data.get("sosiaSituazionePens", "")
        ))

        ### ✅ STEP 2: Save Emergency Contacts
        cursor.execute("DELETE FROM emergency_contacts WHERE codOspite = ?", (personal_data.get("codOspite"),))
        for contact in contacts:
            cursor.execute("""
                INSERT INTO emergency_contacts (
                    codOspite, nomePersona, telefono1, telefono2, telefono3, fax, email, note,
                    delegaDenaro, garante, rating, gradoParentela, desGradoParentela, dataNascita,
                    comuneNascita, nazioneNascita, codiceFiscale, indirizzo, cap, comune, provincia,
                    desComune, desNazione
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                contact.get("codOspite"),
                contact.get("nomePersona"),
                contact.get("telefono1", ""),
                contact.get("telefono2", ""),
                contact.get("telefono3", ""),
                contact.get("fax", ""),
                contact.get("email", ""),
                contact.get("note", ""),
                contact.get("delegaDenaro", ""),
                contact.get("garante", ""),
                contact.get("rating", ""),
                contact.get("gradoParentela", ""),
                contact.get("desGradoParentela", ""),
                contact.get("dataNascita", ""),
                contact.get("comuneNascita", ""),
                contact.get("nazioneNascita", ""),
                contact.get("codiceFiscale", ""),
                contact.get("indirizzo", {}).get("indirizzo", "") if isinstance(contact.get("indirizzo"), dict) else "",
                contact.get("indirizzo", {}).get("cap", "") if isinstance(contact.get("indirizzo"), dict) else "",
                contact.get("indirizzo", {}).get("comune", "") if isinstance(contact.get("indirizzo"), dict) else "",
                contact.get("indirizzo", {}).get("provincia", "") if isinstance(contact.get("indirizzo"), dict) else "",
                contact.get("desComuneNascita", ""),
                contact.get("desNazioneNascita", "")
            ))

        ### ✅ STEP 3: Save Hospital Assignments
        cursor.execute("DELETE FROM hospital_assignments WHERE idRicovero = ?", (hospital.get("id"),))
        for assignment in assignments:
            cursor.execute("""
                INSERT INTO hospital_assignments (
                    idRicovero, dataDal, dataAl, idSede, idReparto, idStanza, idLetto,
                    desSede, desReparto, tipoMov, desStato, desStanza, numeroStanza,
                    stanzaAdibita, numeroLetti, desLetto, numeroLetto, idResidenza
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                assignment.get("idRicovero"),
                assignment.get("dataDal"),
                assignment.get("dataAl", ""),
                assignment.get("idSede"),
                assignment.get("idReparto"),
                assignment.get("idStanza"),
                assignment.get("idLetto"),
                assignment.get("desSede"),
                assignment.get("desReparto"),
                assignment.get("tipoMov"),
                assignment.get("desStato"),
                assignment.get("desStanza"),
                assignment.get("numeroStanza"),
                assignment.get("stanzaAdibita"),
                assignment.get("numeroLetti"),
                assignment.get("desLetto"),
                assignment.get("numeroLetto"),
                assignment.get("idResidenza")
            ))

        ### ✅ STEP 4: Save Patient Absences
        cursor.execute("DELETE FROM patient_absences WHERE idRicovero = ?", (hospital.get("id"),))
        for absence in absences:
            cursor.execute("""
                INSERT INTO patient_absences (
                    idRicovero, dal, al, motivoUscita, idAssenzaCo,
                    codiceOspedale, desMotivo, desOspedale, idAssenzaCollegata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                absence.get("idRicovero"),
                absence.get("dal"),
                absence.get("al", ""),
                absence.get("motivoUscita"),
                absence.get("idAssenzaCo"),
                absence.get("codiceOspedale", ""),
                absence.get("desMotivo"),
                absence.get("desOspedale", ""),
                absence.get("idAssenzaCollegata")
            ))

        conn.commit()
        print(f"✅ Personal data, {len(contacts)} emergency contacts, {len(assignments)} hospital assignments, and {len(absences)} absences saved.")

    except sqlite3.Error as e:
        print(f"🚨 SQLite Error: {e}")

    finally:
        conn.close()

        return True

def main():
    """Main script execution to fetch and store patient personal data."""
    create_database()  # Ensure table is created

    # Fetch JWT token
    jwt_token = get_jwt_token_selenium()
    if not jwt_token:
        print("❌ Could not retrieve JWT token. Exiting.")
        return

    patient_id = input("Enter patient ID to fetch personal data: ").strip()

    if not patient_id.isdigit():
        print("❌ Invalid patient ID. Please enter a numeric value.")
        return

    personal_data = fetch_personal_data(patient_id, jwt_token)

    if personal_data:
        save_personal_data(personal_data)
    else:
        print("⚠️ No personal data found for the given patient ID.")


if __name__ == "__main__":
    main()
