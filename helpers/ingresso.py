import sqlite3
import requests
import time
from datetime import datetime, timezone

def get_timestamp():
    return str(int(time.time() * 1000))

def get_current_time():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

def fetch_esame_obiettivo_details(test_id, jwt_token):
    url = "https://pvc03.cbacloud.it:4445/cba/css/cs/ws/anamnesi/esameobiettivo/get"
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    params = {
        "_dc": get_timestamp(),
        "id": test_id,
        "page": 1,
        "start": 0,
        "limit": 25
    }

    response = requests.get(url, headers=headers, params=params, verify=False)
    print(f"📡 Fetching EsameObiettivo ID {test_id}: {response.url}")
    if response.status_code == 200:
        return response.json().get("data", {})
    else:
        print(f"⚠️ Failed to fetch EsameObiettivo ID {test_id}: {response.status_code}")
        return None

def fetch_esame_obiettivo(patient_id, patient_name, jwt_token):
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    testate_url = "https://pvc03.cbacloud.it:4445/cba/css/cs/ws/testate/get"
    prev_url = "https://pvc03.cbacloud.it:4445/cba/css/cs/ws/testate/prev"
    all_testate = []
    known_ids = set()
    details_map = {}

    params = {
        "_dc": get_timestamp(),
        "tipoTestata": "EsameObiettivo",
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

    r = requests.get(testate_url, headers=headers, params=params, verify=False)
    if r.status_code == 200:
        for d in r.json().get("data", []):
            if d["id"] not in known_ids:
                all_testate.append(d)
                known_ids.add(d["id"])

    if not all_testate:
        print("⚠️ No esame_obiettivo entries found.")
        return []

    while True and all_testate:
        last = all_testate[-1]
        params_prev = {
            "_dc": get_timestamp(),
            "id": last["id"],
            "data": last["data"].replace(" ", "T"),
            "tipoTestata": "EsameObiettivo",
            "idRicovero": patient_id,
            "idProfilo": 3,
            "compilatore": 27
        }
        r = requests.get(prev_url, headers=headers, params=params_prev, verify=False)
        if r.status_code == 200:
            prev = r.json().get("data", [])
            if not prev:
                break
            new = prev[0]
            if new["id"] not in known_ids:
                all_testate.append(new)
                known_ids.add(new["id"])
            else:
                break
        else:
            break

    for t in all_testate:
        d = fetch_esame_obiettivo_details(t["id"], jwt_token)
        if d:
            details_map[t["id"]] = d

    save_esame_obiettivo_data(patient_id, patient_name, all_testate, details_map)
    return all_testate

    
def save_esame_obiettivo_data(patient_id, patient_name, testate_data, details_map):
    conn = sqlite3.connect("borromea.db")
    cursor = conn.cursor()

    for t in testate_data:
        test_id = t["id"]
        d = details_map.get(test_id, {})

        cursor.execute("""
            INSERT OR REPLACE INTO esame_obiettivo (
                id, patient_id, data, compilatore, compilatoreNominativo, compilatoreFigProf,
                codEnte, codOspite, tipoScheda, condGen, statoNutizioneKg, statoNutrizioneBmi,
                statoNutrizioneAltezza, statoSang, statoIdr, modificazionePeso, cute, occhi, vista,
                udito, denti, dentiAltro, lingua, collo, tiroide, pressioneArtOrto, pressioneArtClino,
                soffiCarotidei, soffiAortici, soffiFemorali, polsi, polsiIposfigmia, polsiAssenti,
                torace, addome, fegato, milza, sistemaLinfoGhiand, apparatoOssa, apparatoOssaDolore,
                apparatoOssaLimitazioneFunz, artiNormali, artiEdemi, artiVarici, artiFlebopatie,
                artiCompstasi, artiAmputazione, artiProtesi, piedi, piediDeform, apparatoUrogenit,
                repertoProst, esplorazioneRettale, decubiti, cuore, pressioneArtCuore, mammelle,
                masseMuscolari, sensorio, cmAspetto, cmAnnessi, cmManifestazioni, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            test_id,
            patient_id,
            d.get("data"),
            d.get("compilatore"),
            d.get("compilatoreNominativo"),
            d.get("compilatoreFigProf"),
            d.get("codEnte"),
            d.get("codOspite"),
            d.get("tipoScheda"),
            d.get("condGen"),
            d.get("statoNutizioneKg"),
            d.get("statoNutrizioneBmi"),
            d.get("statoNutrizioneAltezza"),
            d.get("statoSang"),
            d.get("statoIdr"),
            d.get("modificazionePeso"),
            d.get("cute"),
            d.get("occhi"),
            d.get("vista"),
            d.get("udito"),
            d.get("denti"),
            d.get("dentiAltro"),
            d.get("lingua"),
            d.get("collo"),
            d.get("tiroide"),
            d.get("pressioneArtOrto"),
            d.get("pressioneArtClino"),
            d.get("soffiCarotidei"),
            d.get("soffiAortici"),
            d.get("soffiFemorali"),
            d.get("polsi"),
            d.get("polsiIposfigmia"),
            d.get("polsiAssenti"),
            d.get("torace"),
            d.get("addome"),
            d.get("fegato"),
            d.get("milza"),
            d.get("sistemaLinfoGhiand"),
            d.get("apparatoOssa"),
            d.get("apparatoOssaDolore"),
            d.get("apparatoOssaLimitazioneFunz"),
            d.get("artiNormali"),
            d.get("artiEdemi"),
            d.get("artiVarici"),
            d.get("artiFlebopatie"),
            d.get("artiCompstasi"),
            d.get("artiAmputazione"),
            d.get("artiProtesi"),
            d.get("piedi"),
            d.get("piediDeform"),
            d.get("apparatoUrogenit"),
            d.get("repertoProst"),
            d.get("esplorazioneRettale"),
            d.get("decubiti"),
            d.get("cuore"),
            d.get("pressioneArtCuore"),
            d.get("mammelle"),
            d.get("masseMuscolari"),
            d.get("sensorio"),
            d.get("cmAspetto"),
            d.get("cmAnnessi"),
            d.get("cmManifestazioni"),
            d.get("note")
        ))


    conn.commit()
    conn.close()
    print("✅ Esame Obiettivo entries saved.")



def fetch_neuro_details(test_id, jwt_token):
    url = "https://pvc03.cbacloud.it:4445/cba/css/cs/ws/anamnesi/esameneurologico/get"
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    params = {
        "_dc": get_timestamp(),
        "id": test_id,
        "page": 1,
        "start": 0,
        "limit": 25
    }

    response = requests.get(url, headers=headers, params=params, verify=False)
    print(f"📡 Fetching EsameNeurologico ID {test_id}: {response.url}")
    if response.status_code == 200:
        return response.json().get("data", {})
    else:
        print(f"⚠️ Failed to fetch ID {test_id}: {response.status_code}")
        return None

def save_neuro_data(patient_id, patient_name, testate_data, details_map):
    conn = sqlite3.connect("borromea.db")
    cursor = conn.cursor()

    for t in testate_data:
        test_id = t["id"]
        d = details_map.get(test_id, {})

        cursor.execute("""
            INSERT OR REPLACE INTO esame_neurologico (
                id, patient_id, data, compilatore, compilatoreNominativo,
                compilatoreFigProf, statoCoscienza, comportamento,
                coscienzaMalattia, linguaggio, statoEmotivo, disturbi,
                stazioneEretta, tonoDX, tonoSX, nominativo, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            test_id,
            patient_id,
            d.get("data"),
            d.get("compilatore"),
            d.get("compilatoreNominativo"),
            d.get("compilatoreFigProf"),
            d.get("statoCoscienza"),
            d.get("comportamento"),
            d.get("coscienzaMalattia"),
            d.get("linguaggio"),
            d.get("statoEmotivo"),
            d.get("disturbi"),
            d.get("stazioneEretta"),
            d.get("tonoDX"),
            d.get("tonoSX"),
            d.get("nominativo"),
            d.get("note")
        ))

    conn.commit()
    conn.close()
    print("✅ All Esame Neurologico entries saved.")

def fetch_esame_neurologico(patient_id, patient_name, jwt_token):
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    testate_url = "https://pvc03.cbacloud.it:4445/cba/css/cs/ws/testate/get"
    prev_url = "https://pvc03.cbacloud.it:4445/cba/css/cs/ws/testate/prev"
    all_testate = []
    known_ids = set()
    details_map = {}

    params = {
        "_dc": get_timestamp(),
        "tipoTestata": "EsameNeurologico",
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

    r = requests.get(testate_url, headers=headers, params=params, verify=False)
    if r.status_code == 200:
        for d in r.json().get("data", []):
            if d["id"] not in known_ids:
                all_testate.append(d)
                known_ids.add(d["id"])

    if not all_testate:
        print("⚠️ No esame_neurologico entries found.")
        return []

    while True:
        last = all_testate[-1]
        params_prev = {
            "_dc": get_timestamp(),
            "id": last["id"],
            "data": last["data"].replace(" ", "T"),
            "tipoTestata": "EsameNeurologico",
            "idRicovero": patient_id,
            "idProfilo": 3,
            "compilatore": 27
        }
        r = requests.get(prev_url, headers=headers, params=params_prev, verify=False)
        if r.status_code == 200:
            prev = r.json().get("data", [])
            if not prev:
                break
            new = prev[0]
            if new["id"] not in known_ids:
                all_testate.append(new)
                known_ids.add(new["id"])
            else:
                break
        else:
            break

    for t in all_testate:
        d = fetch_neuro_details(t["id"], jwt_token)
        if d:
            details_map[t["id"]] = d

    save_neuro_data(patient_id, patient_name, all_testate, details_map)
    return all_testate
