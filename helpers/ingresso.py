import sqlite3
import requests
import time
from datetime import datetime, timezone

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

def get_timestamp():
    return str(int(time.time() * 1000))

def get_current_time():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

def get_testata_id(id_ricovero, tipo_testata, jwt_token):
    url = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/testate/get"
    params = {
        "_dc": str(int(time.time() * 1000)),
        "al": datetime.now().isoformat(),
        "tipoTestata": tipo_testata,
        "idRicovero": id_ricovero,
        "idProfilo": 3,
        "compilatore": 27,
        "soloUnaTestata": "F",
        "extraParams": "",
        "page": 1,
        "start": 0,
        "limit": 25
    }
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://pvc003.zucchettihc.it:4445/cba/login.html",
        "Origin": "https://pvc003.zucchettihc.it:4445",
        "Connection": "keep-alive"
    }
    response = requests.get(url, headers=headers, params=params, verify=False)
    response.raise_for_status()
    data = response.json().get("data", [])
    return data[0]["id"] if data else None


def fetch_schede_biografiche(id_ricovero, jwt_token):
    url = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/anamnesi/schedebiografiche/list"
    params = {
        "_dc": str(int(time.time() * 1000)),
        "idRicovero": id_ricovero,
        "attuali": "T",
        "page": 1,
        "start": 0,
        "limit": 25
    }
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",  # ✅ Must be CBA-JWT not Authorization
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://pvc003.zucchettihc.it:4445/cba/login.html",
        "Origin": "https://pvc003.zucchettihc.it:4445",
        "Connection": "keep-alive"
    }
    response = requests.get(url, headers=headers, params=params, verify=False)
    response.raise_for_status()
    return response.json()["data"] or {}

def save_schede_biografiche(data, id_ricovero):
    conn = sqlite3.connect("borromea.db")
    c = conn.cursor()
    for item in data:
        c.execute("""
            INSERT OR REPLACE INTO schede_biografiche (
                id, patient_id, idRicovero, codArea, descrizione, note, coefficiente, data,
                compilatore, compilatoreNominativo, compilatoreFigProf, ordinamento, tipoBlocco,
                permessiAnnulla, bozza
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item.get("id"),
            id_ricovero,
            item.get("idRicovero"),
            item.get("codArea"),
            item.get("descrizione"),
            item.get("note"),
            item.get("coefficiente"),
            item.get("data"),
            item.get("compilatore"),
            item.get("compilatoreNominativo"),
            item.get("compilatoreFigProf"),
            item.get("ordinamento"),
            str(item.get("tipoBlocco")),
            str(item.get("permessiAnnulla")),
            item.get("bozza")
        ))
    conn.commit()
    conn.close()

def fetch_cartella(id_ricovero, jwt_token):
    url = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/ce/cartella/get"
    params = {
        "_dc": str(int(time.time() * 1000)),
        "id": id_ricovero,
        "page": 1,
        "start": 0,
        "limit": 25
    }
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://pvc003.zucchettihc.it:4445/cba/login.html",
        "Origin": "https://pvc003.zucchettihc.it:4445",
        "Connection": "keep-alive"
    }
    response = requests.get(url, headers=headers, params=params, verify=False)
    response.raise_for_status()
    return response.json()["data"] or {}

def save_cartella(data, id_ricovero):
    conn = sqlite3.connect("borromea.db")
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO cartella (
            id, patient_id, idRicovero, data, peso, statoCoscienza, respiro, abitudiniAlcool,
            abitudiniFumo, diuresiRegolare, ausiliPannolone, ausiliUrocontrol, ausiliCatetere,
            mobilizzazione, protesi, ausilio1, ausilio2, tipoAusili, igienePersonale,
            visoManiBocca, intima, bagnoDoccia, vestirsi, farmaciSonno, dolore, compilatore,
            compilatoreNominativo, compilatoreFigProf, note
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("id"),
        id_ricovero,
        data.get("idRicovero"),
        data.get("data"),
        data.get("peso"),
        data.get("statoCoscienza"),
        data.get("respiro"),
        data.get("abitudiniAlcool"),
        data.get("abitudiniFumo"),
        data.get("diuresiRegolare"),
        data.get("ausiliPannolone"),
        data.get("ausiliUrocontrol"),
        data.get("ausiliCatetere"),
        data.get("mobilizzazione"),
        data.get("protesi"),
        data.get("ausilio1"),
        data.get("ausilio2"),
        data.get("tipoAusili"),
        data.get("igienePersonale"),
        data.get("visoManiBocca"),
        data.get("intima"),
        data.get("bagnoDoccia"),
        data.get("vestirsi"),
        data.get("farmaciSonno"),
        data.get("dolore"),
        data.get("compilatore"),
        data.get("compilatoreNominativo"),
        data.get("compilatoreFigProf"),
        data.get("note")
    ))
    conn.commit()
    conn.close()


def fetch_pairaccoltadati(id_ricovero, jwt_token):
    url = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/ce/pairaccoltadati/get"
    params = {
        "_dc": str(int(time.time() * 1000)),
        "id": id_ricovero,
        "page": 1,
        "start": 0,
        "limit": 25
    }
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://pvc003.zucchettihc.it:4445/cba/login.html",
        "Origin": "https://pvc003.zucchettihc.it:4445",
        "Connection": "keep-alive"
    }
    response = requests.get(url, headers=headers, params=params, verify=False)
    response.raise_for_status()
    return response.json()["data"] or {}

def save_pairaccoltadati(data, id_ricovero):
    conn = sqlite3.connect("borromea.db")
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO pairaccoltadati (
            id, patient_id, idRicovero, data, compilatore, compilatoreNominativo,
            compilatoreFigProf, pressioneMax, pressioneMin, frequenzaCardiaca,
            temperatura, peso, altezza, respiro, edemi, problemiMinzione,
            problemiAlvo, personaCollabora, siEsprimeChiaramente,
            occhiali, problemiUdito, conosceSistemiSicurezza,
            microclimaAutonomo, rischioCadute, rischioInfezione
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("id"),
        id_ricovero,
        data.get("idRicovero"),
        data.get("data"),
        data.get("compilatore"),
        data.get("compilatoreNominativo"),
        data.get("compilatoreFigProf"),
        data.get("pressioneMax"),
        data.get("pressioneMin"),
        data.get("frequenzaCardiaca"),
        data.get("temperatura"),
        data.get("peso"),
        data.get("altezza"),
        data.get("respiro"),
        data.get("edemi"),
        data.get("problemiMinzione"),
        data.get("problemiAlvo"),
        data.get("personaCollabora"),
        data.get("siEsprimeChiaramente"),
        data.get("occhiali"),
        data.get("problemiUdito"),
        data.get("conosceSistemiSicurezza"),
        data.get("microclimaAutonomo"),
        data.get("rischioCadute"),
        data.get("rischioInfezione")
    ))
    conn.commit()
    conn.close()


def fetch_fisioterapia(id_ricovero, jwt_token):
    url = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/fisioterapia/sfkt/get"
    params = {
        "_dc": str(int(time.time() * 1000)),
        "id": id_ricovero,
        "page": 1,
        "start": 0,
        "limit": 25
    }
    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://pvc003.zucchettihc.it:4445/cba/login.html",
        "Origin": "https://pvc003.zucchettihc.it:4445",
        "Connection": "keep-alive"
    }
    response = requests.get(url, headers=headers, params=params, verify=False)
    response.raise_for_status()
    return response.json()["data"] or {}

import json

def save_fisioterapia(data, id_ricovero):
    conn = sqlite3.connect("borromea.db")
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO fisioterapia (
            id, patient_id, idRicovero, data, compilatore, compilatoreNominativo,
            compilatoreFigProf, listaModelli, agendaFunzione
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("id"),
        id_ricovero,
        data.get("idRicovero"),
        data.get("data"),
        data.get("compilatore"),
        data.get("compilatoreNominativo"),
        data.get("compilatoreFigProf"),
        json.dumps(data.get("lstModelli", [])),
        data.get("agendaFunzione")
    ))
    conn.commit()
    conn.close()


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

    save_esame_obiettivo(list(details_map.values()), patient_id)
    return all_testate

def save_esame_obiettivo(data, id_ricovero):
    conn = sqlite3.connect("borromea.db")
    c = conn.cursor()
    for item in data:
        c.execute("""
            INSERT OR REPLACE INTO esame_obiettivo (
                id, patient_id, data, compilatore, compilatoreNominativo, compilatoreFigProf,
                codEnte, codOspite, tipoScheda, condGen, statoNutizioneKg, statoNutrizioneBmi,
                statoNutrizioneAltezza, statoSang, statoIdr, modificazionePeso, cute, occhi,
                vista, udito, denti, dentiAltro, lingua, collo, tiroide, pressioneArtOrto,
                pressioneArtClino, soffiCarotidei, soffiAortici, soffiFemorali, polsi,
                polsiIposfigmia, polsiAssenti, torace, addome, fegato, milza, sistemaLinfoGhiand,
                apparatoOssa, apparatoOssaDolore, apparatoOssaLimitazioneFunz, artiNormali,
                artiEdemi, artiVarici, artiFlebopatie, artiCompstasi, artiAmputazione, artiProtesi,
                piedi, piediDeform, apparatoUrogenit, repertoProst, esplorazioneRettale,
                decubiti, cuore, pressioneArtCuore, mammelle, masseMuscolari, sensorio,
                cmAspetto, cmAnnessi, cmManifestazioni, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item.get("id"),
            id_ricovero,
            item.get("data"),
            item.get("compilatore"),
            item.get("compilatoreNominativo"),
            item.get("compilatoreFigProf"),
            item.get("codEnte"),
            item.get("codOspite"),
            item.get("tipoScheda"),
            item.get("condGen"),
            item.get("statoNutizioneKg"),
            item.get("statoNutrizioneBmi"),
            item.get("statoNutrizioneAltezza"),
            item.get("statoSang"),
            item.get("statoIdr"),
            item.get("modificazionePeso"),
            item.get("cute"),
            item.get("occhi"),
            item.get("vista"),
            item.get("udito"),
            item.get("denti"),
            item.get("dentiAltro"),
            item.get("lingua"),
            item.get("collo"),
            item.get("tiroide"),
            item.get("pressioneArtOrto"),
            item.get("pressioneArtClino"),
            item.get("soffiCarotidei"),
            item.get("soffiAortici"),
            item.get("soffiFemorali"),
            item.get("polsi"),
            item.get("polsiIposfigmia"),
            item.get("polsiAssenti"),
            item.get("torace"),
            item.get("addome"),
            item.get("fegato"),
            item.get("milza"),
            item.get("sistemaLinfoGhiand"),
            item.get("apparatoOssa"),
            item.get("apparatoOssaDolore"),
            item.get("apparatoOssaLimitazioneFunz"),
            item.get("artiNormali"),
            item.get("artiEdemi"),
            item.get("artiVarici"),
            item.get("artiFlebopatie"),
            item.get("artiCompstasi"),
            item.get("artiAmputazione"),
            item.get("artiProtesi"),
            item.get("piedi"),
            item.get("piediDeform"),
            item.get("apparatoUrogenit"),
            item.get("repertoProst"),
            item.get("esplorazioneRettale"),
            item.get("decubiti"),
            item.get("cuore"),
            item.get("pressioneArtCuore"),
            item.get("mammelle"),
            item.get("masseMuscolari"),
            item.get("sensorio"),
            item.get("cmAspetto"),
            item.get("cmAnnessi"),
            item.get("cmManifestazioni"),
            item.get("note")
        ))
    conn.commit()
    conn.close()


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

    save_esame_neurologico(list(details_map.values()), patient_id)
    return all_testate

def save_esame_neurologico(data, id_ricovero):
    conn = sqlite3.connect("borromea.db")
    c = conn.cursor()
    for item in data:
        c.execute("""
            INSERT OR REPLACE INTO esame_neurologico (
                id, patient_id, data, compilatore, compilatoreNominativo, compilatoreFigProf,
                statoCoscienza, comportamento, coscienzaMalattia, linguaggio, statoEmotivo,
                disturbi, stazioneEretta, tonoDX, tonoSX, nominativo, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item.get("id"),
            id_ricovero,
            item.get("data"),
            item.get("compilatore"),
            item.get("compilatoreNominativo"),
            item.get("compilatoreFigProf"),
            item.get("statoCoscienza"),
            item.get("comportamento"),
            item.get("coscienzaMalattia"),
            item.get("linguaggio"),
            item.get("statoEmotivo"),
            item.get("disturbi"),
            item.get("stazioneEretta"),
            item.get("tonoDX"),
            item.get("tonoSX"),
            item.get("nominativo"),
            item.get("note")
        ))
    conn.commit()
    conn.close()

