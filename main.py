import requests
import json
import time
import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from helpers.auth import get_jwt_token_selenium, refresh_jwt_token
from helpers.fetch_patient_list import fetch_patient_list
from helpers.anagrafica import fetch_all_hospitalizations
from helpers.alimentazione import get_default_start_date
from helpers import cadute, diari_parametri, terapia, alimentazione, anagrafica, contenzioni, lesioni, pi_pai, painad, nrs, cirs, ingresso, barthel, braden, tinetti, conley, morse, must, mna, mmse, gbs, attivita
import urllib3

load_dotenv()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

jwt_token = None

def main():
    """Main execution flow for patient data retrieval and analysis."""
    print("🔄 Automating login and data retrieval...")

    global jwt_token
    jwt_token = get_jwt_token_selenium(keep_browser_open=False)
    if not jwt_token:
        print("❌ Could not retrieve JWT token. Exiting.")
        if driver:
            driver.quit()
        return

    print(f"🔑 Using JWT Token: {jwt_token[:50]}... (truncated)")

    def safe_fetch(func, *args, **kwargs):
        """Calls a function with the current JWT token, refreshes token if unauthorized."""
        global jwt_token
        try:
            return func(*args, jwt_token=jwt_token, **kwargs)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print("⚠️ Token expired. Attempting to refresh...")
                jwt_token = get_jwt_token_selenium(keep_browser_open=False)
                return func(*args, jwt_token=jwt_token, **kwargs)
            else:
                raise
        except requests.exceptions.ConnectionError as e:
            print(f"🚫 Connection failed: {e}")
            return None
    
    patients = safe_fetch(fetch_patient_list)
    if not patients:
        print("⚠️ No patients found.")
        return

    while True:
        if not patients:
            print("⚠️ No valid patient list available. Trying to refresh...")
            patients = safe_fetch(fetch_patient_list)
            if not patients:
                print("❌ Unable to fetch patient list. Please check your connection or credentials.")
                return

        print("\n📌 Please choose a patient by number:")
        for idx, patient in enumerate(patients, start=1):
            print(f"{idx}. {patient['nominativo']} (idRicovero: {patient['idRicovero']}, codOspite: {patient['codOspite']})")

        print("\n🔄 Enter 'R' to refresh patient list or 'Q' to quit.")
        choice = input("Enter the number of the patient you want to select: ").strip()

        if choice.lower() == 'q':
            print("👋 Exiting program.")
            return

        if choice.lower() == 'r':
            print("🔄 Refreshing patient list...")
            patients = safe_fetch(fetch_patient_list)
            if not patients:
                print("❌ Unable to refresh patient list. Please try again or restart.")
            continue

        if not choice.isdigit() or not (1 <= int(choice) <= len(patients)):
            print("❌ Invalid selection!")
            continue

        selected_patient = patients[int(choice) - 1]
        selected_cod_ospite = selected_patient["codOspite"]

        hospitalizations = fetch_all_hospitalizations(selected_cod_ospite, jwt_token)
        id_ricoveros = [h["id"] for h in hospitalizations]

        if not id_ricoveros:
            print("⚠️ No hospitalizations found for this patient.")
            continue

        print(f"\n✅ Selected: {selected_patient['nominativo']}")

        data_types = {
            "1": "Cadute",
            "2": "Diari",
            "3": "Terapia",
            "4": "Alimentazione/Idratazione",
            "5": "Parametri",
            "6": "Anagrafica",
            "7": "Contenzioni",
            "8": "Lesioni",
            "9": "PI/PAI",
            "10": "PAINAD",
            "11": "NRS",
            "12": "CIRS",
            "13": "Ingresso",
            "14": "Barthel",
            "15": "Braden",
            "16": "Tinetti",
            "17": "Conley",
            "18": "Morse",
            "19": "MUST",
            "20": "MNA",
            "21": "Alimentazione/Idratazione (recent)",
            "22": "MMSE",
            "23": "GBS",
            "24": "Attività",
            "A": "all",
        }

        print("\n📌 Select data categories to scrape:")
        for key, value in data_types.items():
            print(f"{key}. {value}")

        selected_data = input("\nEnter choices (e.g. 1,3) or 'A' for all: ").strip().upper()
        selected_data = selected_data.replace(" ", "").split(",")

        if "A" in selected_data:
            selected_data = list(data_types.keys())[:-1]  # remove 'A'

        if not all(item in data_types for item in selected_data):
            print("❌ Invalid input.")
            continue

        print("\n📡 Fetching selected data...")

        # Loop over each hospitalization (idRicovero) for the selected patient
        for selected_id_ricovero in id_ricoveros:
            print(f"\n🏥 Processing idRicovero: {selected_id_ricovero}")

            if "1" in selected_data:
                print("📡 Fetching fall history...")
                cadute_data = safe_fetch(cadute.fetch_falls, selected_id_ricovero, selected_patient['nominativo'])
                if cadute_data:
                    print("✅ Fall history saved.")
                else:
                    print("⚠️ No fall history found.")

            if "2" in selected_data:
                print("📡 Fetching diaries...")
                data_entries = safe_fetch(diari_parametri.fetch_data, selected_id_ricovero, is_diary=True)
                if data_entries:
                    diari_parametri.save_data(selected_id_ricovero, data_entries, is_diary=True)
                    print(f"✅ {len(data_entries)} diary entries saved.")
                else:
                    print("⚠️ No diary entries found.")

            if "3" in selected_data:
                print("📡 Fetching therapy...")
                safe_fetch(terapia.fetch_medications, selected_id_ricovero)

            if "4" in selected_data:
                print("📡 Fetching alimentazione/idratazione...")
                intake_data = safe_fetch(alimentazione.fetch_alimentazione, selected_id_ricovero, infinite=True, skip_partial_check=True)
                print(f"✅ {intake_data} records saved.")
    
            if "5" in selected_data:
                print("📡 Fetching parameters...")
                parametri_data = safe_fetch(diari_parametri.fetch_data, selected_id_ricovero, is_diary=False)
                if parametri_data:
                    diari_parametri.save_data(selected_id_ricovero, parametri_data, is_diary=False)
                    print(f"✅ {len(parametri_data)} parameters saved.")
                else:
                    print("⚠️ No parameter data.")

            if "7" in selected_data:
                print("📡 Fetching contenzioni...")
                contenzioni_data = safe_fetch(contenzioni.fetch_contenzioni, selected_id_ricovero, selected_patient['nominativo'])
                if contenzioni_data:
                    print("✅ Contenzioni saved.")
                else:
                    print("⚠️ No contenzioni found.")

            if "8" in selected_data:
                print("📡 Fetching lesioni...")
                lesioni_data = safe_fetch(lesioni.fetch_lesioni, selected_id_ricovero, selected_patient['nominativo'])
                if lesioni_data:
                    print("✅ Lesioni saved.")
                else:
                    print("⚠️ No lesioni found.")

            if "9" in selected_data:
                print("📡 Fetching PI (Piani Individuali)...")
                pi_data = safe_fetch(pi_pai.fetch_pi, selected_id_ricovero, selected_patient['nominativo'])
                if pi_data:
                    print("✅ PI saved.")
                else:
                    print("⚠️ No PI data found.")

                print("📡 Fetching PAI (Piani Assistenziali)...")
                pai_data = safe_fetch(pi_pai.fetch_pai, selected_id_ricovero, selected_patient['nominativo'])
                if pai_data:
                    print("✅ PAI saved.")
                else:
                    print("⚠️ No PAI data found.")

            if "10" in selected_data:
                print("📡 Fetching PAINAD tests...")
                painad_data = safe_fetch(painad.fetch_painad, selected_id_ricovero, selected_patient['nominativo'])
                if painad_data:
                    print("✅ PAINAD data saved.")
                else:
                    print("⚠️ No PAINAD data found.")

            if "11" in selected_data:
                print("📡 Fetching NRS...")
                nrs_data = safe_fetch(nrs.fetch_nrs, selected_id_ricovero, selected_patient['nominativo'])
                if nrs_data:
                    print("✅ NRS data saved.")
                else:
                    print("⚠️ No NRS data found.")

            if "12" in selected_data:
                print("📡 Fetching CIRS...")
                cirs_data = safe_fetch(cirs.fetch_cirs, selected_id_ricovero, selected_patient['nominativo'])
                if cirs_data:
                    print("✅ CIRS data saved.")
                else:
                    print("⚠️ No CIRS data found.")

            if "13" in selected_data:
                print(f"\n🏥 Processing idRicovero: {selected_id_ricovero}")

                # 🧠 Esame neurologico
                print("📡 Fetching Esame Neurologico...")
                neurologico_data = safe_fetch(ingresso.fetch_esame_neurologico, selected_id_ricovero, selected_patient["nominativo"])
                if neurologico_data:
                    ingresso.save_esame_neurologico(neurologico_data, selected_id_ricovero)
                    print("✅ Esame Neurologico saved.")
                else:
                    print("⚠️ No Esame Neurologico found.")

                # 🫀 Esame obiettivo
                print("📡 Fetching Esame Obiettivo...")
                obiettivo_data = safe_fetch(ingresso.fetch_esame_obiettivo, selected_id_ricovero, selected_patient["nominativo"])
                if obiettivo_data:
                    ingresso.save_esame_obiettivo(obiettivo_data, selected_id_ricovero)
                    print("✅ Esame Obiettivo saved.")
                else:
                    print("⚠️ No Esame Obiettivo found.")

                # 🧾 Schede biografiche
                print("📡 Fetching Schede Biografiche...")
                schede_data = safe_fetch(ingresso.fetch_schede_biografiche, selected_id_ricovero)
                if schede_data:
                    ingresso.save_schede_biografiche(schede_data, selected_id_ricovero)
                    print(f"✅ {len(schede_data)} schede biografiche saved.")
                else:
                    print("⚠️ No Schede Biografiche found.")

                # 🗂 Cartella
                print("📡 Fetching Cartella...")
                cartella_id = ingresso.get_testata_id(selected_id_ricovero, "CartellaEntrata", jwt_token)
                if cartella_id:
                    cartella_data = safe_fetch(ingresso.fetch_cartella, cartella_id)
                    if cartella_data:
                        ingresso.save_cartella(cartella_data, selected_id_ricovero)
                        print("✅ Cartella data saved.")
                    else:
                        print("⚠️ No Cartella data found.")
                else:
                    print("⚠️ No Cartella testata ID found.")

                # 📋 Pair Accolta Dati
                print("📡 Fetching Pair Accolta Dati...")
                pair_id = ingresso.get_testata_id(selected_id_ricovero, "PaiRaccoltaDati", jwt_token)
                if pair_id:
                    pair_data = safe_fetch(ingresso.fetch_pairaccoltadati, pair_id)
                    if pair_data:
                        ingresso.save_pairaccoltadati(pair_data, selected_id_ricovero)
                        print("✅ Pair Accolta Dati saved.")
                    else:
                        print("⚠️ No Pair Accolta Dati found.")
                else:
                    print("⚠️ No Pair testata ID found.")

                # 🦵 Fisioterapia
                print("📡 Fetching Fisioterapia...")
                fkt_id = ingresso.get_testata_id(selected_id_ricovero, "Fkt", jwt_token)
                if fkt_id:
                    fkt_data = safe_fetch(ingresso.fetch_fisioterapia, fkt_id)
                    if fkt_data:
                        ingresso.save_fisioterapia(fkt_data, selected_id_ricovero)
                        print("✅ Fisioterapia data saved.")
                    else:
                        print("⚠️ No Fisioterapia data found.")
                else:
                    print("⚠️ No Fisioterapia testata ID found.")

            if "14" in selected_data:
                print("📡 Fetching Barthel...")
                barthel_data = safe_fetch(barthel.fetch_barthel, selected_id_ricovero, selected_patient['nominativo'])
                if barthel_data:
                    print("✅ Barthel data saved.")
                else:
                    print("⚠️ No Barthel data found.")

            if "15" in selected_data:
                print("📡 Fetching Braden...")
                braden_data = safe_fetch(braden.fetch_braden, selected_id_ricovero, selected_patient['nominativo'])
                if braden_data:
                    print("✅ Braden data saved.")
                else:
                    print("⚠️ No Braden data found.")

            if "16" in selected_data:
                print("📡 Fetching Tinetti...")
                tinetti_data = safe_fetch(tinetti.fetch_tinetti, selected_id_ricovero, selected_patient['nominativo'])
                if tinetti_data:
                    print("✅ Tinetti data saved.")
                else:
                    print("⚠️ No Tinetti data found.")

            if "17" in selected_data:
                print("📡 Fetching Conley...")
                conley_data = safe_fetch(conley.fetch_conley, selected_id_ricovero, selected_patient['nominativo'])
                if conley_data:
                    print("✅ Conley data saved.")
                else:
                    print("⚠️ No Conley data found.")

            if "18" in selected_data:
                print("📡 Fetching Morse...")
                morse_data = safe_fetch(morse.fetch_morse, selected_id_ricovero, selected_patient['nominativo'])
                if morse_data:
                    print("✅ Morse data saved.")
                else:
                    print("⚠️ No Morse data found.")

            if "19" in selected_data:
                print("📡 Fetching MUST...")
                must_data = safe_fetch(must.fetch_must, selected_id_ricovero, selected_patient['nominativo'])
                if must_data:
                    print("✅ MUST data saved.")
                else:
                    print("⚠️ No MUST data found.")

            if "20" in selected_data:
                print("📡 Fetching MNA...")
                mna_data = safe_fetch(mna.fetch_mna, selected_id_ricovero, selected_patient['nominativo'])
                if mna_data:
                    print("✅ MNA data saved.")
                else:
                    print("⚠️ No MNA data found.")


            if "21" in selected_data:
                print("📡 Fetching alimentazione/idratazione from default start...")
                start_date = safe_fetch(get_default_start_date, selected_patient["codOspite"], selected_id_ricovero)
                intake_data = safe_fetch(alimentazione.fetch_alimentazione, selected_id_ricovero, start_date=start_date, infinite=True, skip_partial_check=False)
                print(f"✅ {intake_data} records saved.")

            if "22" in selected_data:
                print("📡 Fetching MMSE...")
                from helpers import mmse  # Import here if not global
                mmse_data = safe_fetch(mmse.fetch_mmse, selected_id_ricovero, selected_patient['nominativo'])
                if mmse_data:
                    print("✅ MMSE data saved.")
                else:
                    print("⚠️ No MMSE data found.")

            if "23" in selected_data:
                print("📡 Fetching GBS...")
                from helpers import gbs  # Optional: import at top if preferred
                gbs_data = safe_fetch(gbs.fetch_gbs, selected_id_ricovero, selected_patient['nominativo'])
                if gbs_data:
                    print("✅ GBS data saved.")
                else:
                    print("⚠️ No GBS data found.")

            if "24" in selected_data:
                print("📡 Fetching attività...")
                ricovero_data = next((h for h in hospitalizations if h["id"] == selected_id_ricovero), None)
                if ricovero_data:
                    ricovero_start = datetime.fromisoformat(ricovero_data["dal"])
                    ricovero_end = datetime.fromisoformat(ricovero_data["al"]) if ricovero_data.get("al") else None
                    total_atti = safe_fetch(attivita.fetch_attivita, selected_id_ricovero, ricovero_start=ricovero_start, ricovero_end=ricovero_end)
                    print(f"✅ {total_atti} attività entries saved.")
                else:
                    print("⚠️ Ricovero info not found.")

        # Fetch anagrafica only once — it’s not per ricovero
        if "6" in selected_data:
            print("📡 Fetching personal data...")
            try:
                personal_data = safe_fetch(anagrafica.fetch_personal_data, selected_cod_ospite)
                if personal_data:
                    print("✅ Personal data saved.")
                else:
                    print("⚠️ No personal data found.")
            except Exception as e:
                print(f"❌ Failed to fetch or save personal data: {e}")

        print("✅ Data collection complete.")


if __name__ == "__main__":
    main()  
