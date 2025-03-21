import requests
import json
import time
import os
import sqlite3
from dotenv import load_dotenv
from helpers.auth import get_jwt_token_selenium, refresh_jwt_token
from helpers.fetch_patient_list import fetch_patient_list
from helpers import cadute, diari_parametri, terapia, alimentazione, anagrafica, contenzioni, lesioni
import urllib3

load_dotenv()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def main():
    """Main execution flow for patient data retrieval and analysis."""
    print("🔄 Automating login and data retrieval...")

    jwt_token = get_jwt_token_selenium()
    if not jwt_token:
        print("❌ Could not retrieve JWT token. Exiting.")
        return

    print(f"🔑 Using JWT Token: {jwt_token[:50]}... (truncated)")

    def safe_fetch(func, *args, **kwargs):
        """Calls a function with the current JWT token, refreshes token if unauthorized."""
        nonlocal jwt_token
        try:
            return func(*args, jwt_token=jwt_token, **kwargs)
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 401:
                print("⚠️ Token expired. Attempting to refresh...")
                jwt_token = refresh_jwt_token()
                return func(*args, jwt_token=jwt_token, **kwargs)
            else:
                raise

    patients = fetch_patient_list(jwt_token)
    if not patients:
        print("⚠️ No patients found.")
        return

    while True:
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
            patients = fetch_patient_list(jwt_token)
            continue

        if not choice.isdigit() or not (1 <= int(choice) <= len(patients)):
            print("❌ Invalid selection!")
            continue

        selected_patient = patients[int(choice) - 1]
        selected_id_ricovero = selected_patient["idRicovero"]
        selected_cod_ospite = selected_patient["codOspite"]
        print(f"\n✅ Selected: {selected_patient['nominativo']}")

        data_types = {
            "1": "cadute",
            "2": "diari",
            "3": "terapia",
            "4": "alimentazione/idratazione",
            "5": "parametri",
            "6": "anagrafica",
            "7": "contenzioni",
            "8": "lesioni",
            "A": "all"
        }

        print("\n📌 Select data categories to scrape:")
        for key, value in data_types.items():
            print(f"{key}. {value.capitalize()}")

        selected_data = input("\nEnter choices (e.g. 1,3) or 'A' for all: ").strip().upper()
        selected_data = selected_data.replace(" ", "").split(",")

        if "A" in selected_data:
            selected_data = list(data_types.keys())[:-1]  # remove 'A'

        if not all(item in data_types for item in selected_data):
            print("❌ Invalid input.")
            continue

        print("\n📡 Fetching selected data...")

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
            print("📡 Fetching alimentation...")
            safe_fetch(alimentazione.fetch_intake, selected_id_ricovero)
            print("✅ Dietary records fetched.")

        if "5" in selected_data:
            print("📡 Fetching parameters...")
            parametri_data = safe_fetch(diari_parametri.fetch_data, selected_id_ricovero, is_diary=False)
            if parametri_data:
                diari_parametri.save_data(selected_id_ricovero, parametri_data, is_diary=False)
                print(f"✅ {len(parametri_data)} parameters saved.")
            else:
                print("⚠️ No parameter data.")

        if "6" in selected_data:
            print("📡 Fetching personal data...")
            personal_data = safe_fetch(anagrafica.fetch_personal_data, selected_cod_ospite)
            if personal_data:
                anagrafica.save_personal_data(personal_data, selected_cod_ospite)
                print("✅ Personal data saved.")
            else:
                print("⚠️ No personal data found.")

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


        print("✅ Data collection complete.")

if __name__ == "__main__":
    main()  
