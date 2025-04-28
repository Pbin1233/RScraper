import sqlite3
from datetime import datetime, timedelta
import urllib3
import requests
from helpers import (
    auth, fetch_patient_list, anagrafica, alimentazione, diari_parametri, terapia,
    tinetti, morse, must, nrs, painad, pi_pai,
    contenzioni, gbs, lesioni, mmse, mna, conley,
    cirs, ingresso, attivita, barthel, braden, cadute
)



DB_PATH = "borromea.db"
ALL_DATA_TYPES = [
    "diari", "parametri", "anagrafica", "terapia",
    "tinetti", "morse", "must", "nrs", "painad", "pi_pai",
    "contenzioni", "gbs", "lesioni", "mmse", "mna", "conley",
    "cirs", "ingresso", "attivita", "barthel", "braden", "cadute"
]

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

jwt_token = None


def is_past_hospitalization(ricovero):
    if ricovero.get("al"):
        al_date = datetime.fromisoformat(ricovero["al"])
        return (datetime.now() - al_date).days > 2
    return False


def ensure_scrape_status_table():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scrape_status (
            ricovero_id TEXT PRIMARY KEY,
            scraped_at TEXT,
            data_types TEXT
        )
    """)
    conn.commit()
    conn.close()


def ensure_anagrafica_table():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scrape_status_anagrafica (
            codOspite TEXT PRIMARY KEY,
            scraped_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def was_anagrafica_scraped(cod_ospite):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM scrape_status_anagrafica WHERE codOspite = ?", (cod_ospite,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def mark_anagrafica_scraped(cod_ospite):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT OR REPLACE INTO scrape_status_anagrafica (codOspite, scraped_at)
        VALUES (?, ?)
    """, (cod_ospite, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_scraped_types(ricovero_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT data_types FROM scrape_status WHERE ricovero_id = ?", (ricovero_id,))
    row = cursor.fetchone()
    conn.close()
    return set(row[0].split(",")) if row and row[0] else set()


def mark_type_scraped(ricovero_id, data_type):
    current = get_scraped_types(ricovero_id)
    current.add(data_type)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT OR REPLACE INTO scrape_status (ricovero_id, scraped_at, data_types)
        VALUES (?, ?, ?)
    """, (ricovero_id, datetime.now().isoformat(), ",".join(sorted(current))))
    conn.commit()
    conn.close()


def safe_fetch(func, *args, **kwargs):
    global jwt_token
    try:
        return func(*args, jwt_token=jwt_token, **kwargs)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("⚠️ Token expired. Attempting to refresh...")
            try:
                new_token = auth.get_jwt_token_selenium(keep_browser_open=False)
                if not new_token:
                    raise RuntimeError("❌ Failed to retrieve new token after expiration")
                jwt_token = new_token
                print("✅ New JWT Token Retrieved. Retrying request...")
                
                # Retry original function call
                retried_result = func(*args, jwt_token=jwt_token, **kwargs)

                # Validate the retried result here
                if retried_result is None:
                    raise RuntimeError("❌ Retried request after token refresh returned None. Stopping scrape.")
                return retried_result
            except Exception as refresh_error:
                print(f"❌ Critical: Failed to refresh token properly: {refresh_error}")
                raise RuntimeError("❌ Token refresh failure, stopping script") from refresh_error
        else:
            raise
    except requests.exceptions.ConnectionError as e:
        print(f"🚫 Connection failed: {e}")
        return None

def main():
    global jwt_token
    print("🔐 Getting token...")
    jwt_token = auth.get_jwt_token_selenium(keep_browser_open=False)
    if not jwt_token:
        print("❌ JWT Token retrieval failed.")
        return

    ensure_scrape_status_table()
    ensure_anagrafica_table()
    patients = safe_fetch(fetch_patient_list.fetch_patient_list)
    if not patients:
        print("❌ Failed to retrieve patient list.")
        return

    for patient in patients:
        ricoveri = safe_fetch(anagrafica.fetch_all_hospitalizations, patient["codOspite"])
        if not ricoveri:
            continue

        if not was_anagrafica_scraped(patient["codOspite"]):
            print(f"📋 Fetching personal data for {patient['codOspite']}...")
            try:
                result = safe_fetch(anagrafica.fetch_personal_data, patient["codOspite"])
                if result:
                    mark_anagrafica_scraped(patient["codOspite"])
                    print("✅ Personal data saved.")
                else:
                    print("⚠️ Failed to save personal data.")
            except Exception as e:
                print(f"❌ Error during personal data fetch: {e}")

        past_ricoveri = [r for r in ricoveri if is_past_hospitalization(r)]
        for ricovero in past_ricoveri:
            ricovero_id = ricovero["id"]
            scraped = get_scraped_types(ricovero_id)

            # 🔥 Skip hospitalization if everything already scraped
            if all(data_type in scraped for data_type in ALL_DATA_TYPES):
                print(f"✅ All data already scraped for ricovero {ricovero_id}, skipping...")
                continue

            print(f"\n📦 Checking ricovero {ricovero_id}")

            # Alimentazione (temporarily disabled)
            # if "alimentazione" not in scraped:
            #     try:
            #         start_date = safe_fetch(
            #             alimentazione.get_default_start_date,
            #             patient["codOspite"],
            #             ricovero_id
            #         )
            #         if start_date:
            #             total = safe_fetch(
            #                 alimentazione.fetch_alimentazione,
            #                 ricovero_id,
            #                 start_date=start_date,
            #                 infinite=True,
            #                 skip_partial_check=True
            #             )
            #             if total and total > 0:
            #                 print(f"✅ {total} alimentazione entries downloaded")
            #                 mark_type_scraped(ricovero_id, "alimentazione")
            #             else:
            #                 print("⚠️ No alimentazione data saved (empty)")
            #     except Exception as e:
            #         print(f"❌ Error scraping alimentazione: {e}")

            # Diaries
            if "diari" not in scraped:
                try:
                    diary_entries = safe_fetch(diari_parametri.fetch_data, ricovero_id, is_diary=True)
                    if diary_entries is not None:
                        diari_parametri.save_data(ricovero_id, diary_entries, is_diary=True)
                        print(f"✅ {len(diary_entries)} diary entries saved")
                        mark_type_scraped(ricovero_id, "diari")
                    else:
                        print("⚠️ No diary entries saved")
                except Exception as e:
                    print(f"❌ Error scraping diary entries: {e}")

            # Parametri
            if "parametri" not in scraped:
                try:
                    parametri_entries = safe_fetch(diari_parametri.fetch_data, ricovero_id, is_diary=False)
                    if parametri_entries is not None:
                        diari_parametri.save_data(ricovero_id, parametri_entries, is_diary=False)
                        print(f"✅ {len(parametri_entries)} parameter entries saved")
                        mark_type_scraped(ricovero_id, "parametri")
                    else:
                        print("⚠️ No parameter entries saved")
                except Exception as e:
                    print(f"❌ Error scraping parameters: {e}")

            # Terapia
            if "terapia" not in scraped:
                try:
                    result = safe_fetch(terapia.fetch_medications, ricovero_id)
                    if result is not None:
                        print(f"✅ Terapia data saved")
                        mark_type_scraped(ricovero_id, "terapia")
                    else:
                        print("⚠️ No terapia data saved")
                except Exception as e:
                    print(f"❌ Error scraping terapia: {e}")

            # Tinetti
            if "tinetti" not in scraped:
                try:
                    result = safe_fetch(tinetti.fetch_tinetti, ricovero_id, patient.get("nominativo", ""))
                    if result is not None:
                        print(f"✅ Tinetti data saved")
                        mark_type_scraped(ricovero_id, "tinetti")
                    else:
                        print(f"⚠️ No Tinetti data saved")
                except Exception as e:
                    print(f"❌ Error scraping Tinetti: {e}")

            # Morse
            if "morse" not in scraped:
                try:
                    result = safe_fetch(morse.fetch_morse, ricovero_id, patient.get("nominativo", ""))
                    if result is not None:
                        print(f"✅ Morse data saved")
                        mark_type_scraped(ricovero_id, "morse")
                    else:
                        print(f"⚠️ No Morse data saved")
                except Exception as e:
                    print(f"❌ Error scraping Morse: {e}")

            # MUST
            if "must" not in scraped:
                try:
                    result = safe_fetch(must.fetch_must, ricovero_id, patient.get("nominativo", ""))
                    if result is not None:
                        print(f"✅ MUST data saved")
                        mark_type_scraped(ricovero_id, "must")
                    else:
                        print(f"⚠️ No MUST data saved")
                except Exception as e:
                    print(f"❌ Error scraping MUST: {e}")

            # NRS
            if "nrs" not in scraped:
                try:
                    result = safe_fetch(nrs.fetch_nrs, ricovero_id, patient.get("nominativo", ""))
                    if result is not None:
                        print(f"✅ NRS data saved")
                        mark_type_scraped(ricovero_id, "nrs")
                    else:
                        print(f"⚠️ No NRS data saved")
                except Exception as e:
                    print(f"❌ Error scraping NRS: {e}")

            # PAINAD
            if "painad" not in scraped:
                try:
                    result = safe_fetch(painad.fetch_painad, ricovero_id, patient.get("nominativo", ""))
                    if result is not None:
                        print(f"✅ PAINAD data saved")
                        mark_type_scraped(ricovero_id, "painad")
                    else:
                        print(f"⚠️ No PAINAD data saved")
                except Exception as e:
                    print(f"❌ Error scraping PAINAD: {e}")

            # PI/PAI
            if "pi_pai" not in scraped:
                try:
                    pi_ok = False
                    pai_ok = False

                    try:
                        result_pi = safe_fetch(pi_pai.fetch_pi, ricovero_id, patient.get("nominativo", ""))
                        if result_pi is not None:
                            pi_ok = True
                    except Exception as e:
                        print(f"❌ Error scraping PI: {e}")

                    try:
                        result_pai = safe_fetch(pi_pai.fetch_pai, ricovero_id, patient.get("nominativo", ""))
                        if result_pai is not None:
                            pai_ok = True
                    except Exception as e:
                        print(f"❌ Error scraping PAI: {e}")

                    if pi_ok and pai_ok:
                        print(f"✅ PI and PAI data saved")
                        mark_type_scraped(ricovero_id, "pi_pai")
                    else:
                        print(f"⚠️ PI or PAI data incomplete, not marking as scraped")
                except Exception as e:
                    print(f"❌ Error scraping PI/PAI: {e}")

            # Contenzioni
            if "contenzioni" not in scraped:
                try:
                    result = safe_fetch(contenzioni.fetch_contenzioni, ricovero_id, patient.get("nominativo", ""))
                    if result is not None:
                        print(f"✅ Contenzioni data saved")
                        mark_type_scraped(ricovero_id, "contenzioni")
                    else:
                        print(f"⚠️ No Contenzioni data saved")
                except Exception as e:
                    print(f"❌ Error scraping Contenzioni: {e}")

            # GBS
            if "gbs" not in scraped:
                try:
                    result = safe_fetch(gbs.fetch_gbs, ricovero_id, patient.get("nominativo", ""))
                    if result is not None:
                        print(f"✅ GBS data saved")
                        mark_type_scraped(ricovero_id, "gbs")
                    else:
                        print(f"⚠️ No GBS data saved")
                except Exception as e:
                    print(f"❌ Error scraping GBS: {e}")

            # Lesioni
            if "lesioni" not in scraped:
                try:
                    result = safe_fetch(lesioni.fetch_lesioni, ricovero_id, patient.get("nominativo", ""))
                    if result is not None:
                        print(f"✅ Lesioni data saved")
                        mark_type_scraped(ricovero_id, "lesioni")
                    else:
                        print(f"⚠️ No Lesioni data saved")
                except Exception as e:
                    print(f"❌ Error scraping Lesioni: {e}")

            # MMSE
            if "mmse" not in scraped:
                try:
                    result = safe_fetch(mmse.fetch_mmse, ricovero_id, patient.get("nominativo", ""))
                    if result is not None:
                        print(f"✅ MMSE data saved")
                        mark_type_scraped(ricovero_id, "mmse")
                    else:
                        print(f"⚠️ No MMSE data saved")
                except Exception as e:
                    print(f"❌ Error scraping MMSE: {e}")

            # MNA
            if "mna" not in scraped:
                try:
                    result = safe_fetch(mna.fetch_mna, ricovero_id, patient.get("nominativo", ""))
                    if result is not None:
                        print(f"✅ MNA data saved")
                        mark_type_scraped(ricovero_id, "mna")
                    else:
                        print(f"⚠️ No MNA data saved")
                except Exception as e:
                    print(f"❌ Error scraping MNA: {e}")

            # Conley
            if "conley" not in scraped:
                try:
                    result = safe_fetch(conley.fetch_conley, ricovero_id, patient.get("nominativo", ""))
                    if result is not None:
                        print(f"✅ Conley data saved")
                        mark_type_scraped(ricovero_id, "conley")
                    else:
                        print(f"⚠️ No Conley data saved")
                except Exception as e:
                    print(f"❌ Error scraping Conley: {e}")

            # CIRS
            if "cirs" not in scraped:
                try:
                    result = safe_fetch(cirs.fetch_cirs, ricovero_id, patient.get("nominativo", ""))
                    if result is not None:
                        print(f"✅ CIRS data saved")
                        mark_type_scraped(ricovero_id, "cirs")
                    else:
                        print(f"⚠️ No CIRS data saved")
                except Exception as e:
                    print(f"❌ Error scraping CIRS: {e}")

            # Ingresso (schede biografiche, cartella, pairaccoltadati, fisioterapia)
            if "ingresso" not in scraped:
                try:
                    ingresso_ok = False
                    try:
                        result1 = safe_fetch(ingresso.fetch_schede_biografiche, ricovero_id)
                        if result1 is not None:
                            ingresso_ok = True
                    except Exception as e:
                        print(f"❌ Error fetching schede biografiche: {e}")
                    
                    try:
                        result2 = safe_fetch(ingresso.fetch_cartella, ricovero_id)
                        if result2 is not None:
                            ingresso_ok = True
                    except Exception as e:
                        print(f"❌ Error fetching cartella: {e}")
                    
                    try:
                        result3 = safe_fetch(ingresso.fetch_pairaccoltadati, ricovero_id)
                        if result3 is not None:
                            ingresso_ok = True
                    except Exception as e:
                        print(f"❌ Error fetching pairaccoltadati: {e}")
                    
                    try:
                        result4 = safe_fetch(ingresso.fetch_fisioterapia, ricovero_id)
                        if result4 is not None:
                            ingresso_ok = True
                    except Exception as e:
                        print(f"❌ Error fetching fisioterapia: {e}")

                    if ingresso_ok:
                        print(f"✅ Ingresso data saved")
                        mark_type_scraped(ricovero_id, "ingresso")
                    else:
                        print(f"⚠️ No Ingresso data saved")
                except Exception as e:
                    print(f"❌ Error scraping Ingresso data: {e}")

            # Attivita
            if "attivita" not in scraped:
                try:
                    ricovero_start = datetime.fromisoformat(ricovero["dal"]) if ricovero.get("dal") else datetime.now() - timedelta(days=30)
                    result = safe_fetch(attivita.fetch_attivita, ricovero_id, ricovero_start=ricovero_start)
                    if result and result > 0:
                        print(f"✅ Attività data saved")
                        mark_type_scraped(ricovero_id, "attivita")
                    else:
                        print(f"⚠️ No Attività data saved")
                except Exception as e:
                    print(f"❌ Error scraping Attività: {e}")

            # Barthel
            if "barthel" not in scraped:
                try:
                    result = safe_fetch(barthel.fetch_barthel, ricovero_id, patient.get("nominativo", ""))
                    if result is not None:
                        print(f"✅ Barthel data saved")
                        mark_type_scraped(ricovero_id, "barthel")
                    else:
                        print(f"⚠️ No Barthel data saved")
                except Exception as e:
                    print(f"❌ Error scraping Barthel: {e}")

            # Braden
            if "braden" not in scraped:
                try:
                    result = safe_fetch(braden.fetch_braden, ricovero_id, patient.get("nominativo", ""))
                    if result is not None:
                        print(f"✅ Braden data saved")
                        mark_type_scraped(ricovero_id, "braden")
                    else:
                        print(f"⚠️ No Braden data saved")
                except Exception as e:
                    print(f"❌ Error scraping Braden: {e}")

            # Cadute
            if "cadute" not in scraped:
                try:
                    result = safe_fetch(cadute.fetch_falls, ricovero_id, patient.get("nominativo", ""))
                    if result is not None:
                        print(f"✅ Cadute data saved")
                        mark_type_scraped(ricovero_id, "cadute")
                    else:
                        print(f"⚠️ No Cadute data saved")
                except Exception as e:
                    print(f"❌ Error scraping Cadute: {e}")

    print("\n✅ Auto-scrape complete.")


if __name__ == "__main__":
    main()
