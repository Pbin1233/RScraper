import sqlite3
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Output containers
results_by_year = defaultdict(list)
csv_rows = []

# HTML icons
STATUS_ICONS = {
    "ok": "✅",
    "warn": "⚠️",
    "missing": "❌",
    "todo": "ℹ️"
}

today_str = datetime.today().strftime("%d-%m-%Y")

def extract_year_or_status(dal, al):
    if al is None:
        return "Still Active"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(al, fmt).year
        except ValueError:
            continue
    return "unknown"

def check_indicatore_generale_1(cursor, hospitalization_id, data_dal):
    check_results = {}

    # --- Medical Domain ---

    # Diario medico
    cursor.execute("""
        SELECT testoDiario, tipologia FROM diario_medico
        WHERE patient_id = ? AND date(dataOra) = date(?)
    """, (hospitalization_id, data_dal))
    diario_entries = cursor.fetchall()
    diario_ok = any("Valutazione all'ingresso" == row[1] for row in diario_entries)
    diario_warning = any("ingresso" in (row[0] or "").lower() for row in diario_entries)
    check_results["diario_medico"] = "ok" if diario_ok else ("warn" if diario_warning else "missing")

    # Esame obiettivo
    cursor.execute("""
        SELECT id FROM esame_obiettivo
        WHERE patient_id = ? AND date(data) = date(?)
    """, (hospitalization_id, data_dal))
    check_results["esame_obiettivo"] = "ok" if cursor.fetchone() else "missing"

    # Scheda dolore: NRS or PAINAD
    cursor.execute("""
        SELECT id FROM nrs WHERE patient_id = ? AND date(data) = date(?)
        UNION
        SELECT id FROM painad WHERE patient_id = ? AND date(data) = date(?)
    """, (hospitalization_id, data_dal, hospitalization_id, data_dal))
    check_results["scheda_dolore"] = "ok" if cursor.fetchone() else "missing"

    # CIRS
    cursor.execute("""
        SELECT id FROM cirs WHERE patient_id = ? AND date(data) = date(?)
    """, (hospitalization_id, data_dal))
    check_results["cirs"] = "ok" if cursor.fetchone() else "missing"

    # GBS (placeholder)
    check_results["gbs"] = "todo"

    # Lesioni da pressione (LDP)
    trigger_lesione_check = False
    for testo, tipologia in diario_entries:
        if tipologia == "Valutazione all'ingresso" or ("ricovero" in (testo or "").lower()):
            if any(word in (testo or "").lower() for word in ["ldp", "lesione", "lesioni"]):
                trigger_lesione_check = True
                break
    if trigger_lesione_check:
        cursor.execute("""
            SELECT presInIngr FROM lesioni
            WHERE patient_id = ? AND date(data) = date(?)
        """, (hospitalization_id, data_dal))
        lesione_rows = cursor.fetchall()
        if lesione_rows:
            if any(row[0] == "T" for row in lesione_rows if row[0] is not None):
                check_results["ldp"] = "ok"
            else:
                check_results["ldp"] = "warn"
        else:
            check_results["ldp"] = "missing"
    else:
        check_results["ldp"] = "ok"

    # Catetere / Stomia / Ossigeno (placeholder)
    check_results["catetere_stomia_ossigeno"] = "todo"

    # --- Nursing Domain ---

    # Diario infermieristico
    cursor.execute("""
        SELECT testoDiario FROM diario_infermieristico
        WHERE patient_id = ? AND date(dataOra) = date(?)
    """, (hospitalization_id, data_dal))
    diario_infermieristico = cursor.fetchall()
    check_results["diario_infermieristico"] = (
        "ok" if any("ingresso" in (t[0] or "").lower() for t in diario_infermieristico)
        else "missing"
    )

    # Scheda ingresso infermieristica
    cursor.execute("""
        SELECT id FROM pairaccoltadati
        WHERE patient_id = ? AND date(data) = date(?)
    """, (hospitalization_id, data_dal))
    check_results["scheda_ingresso_infermieristica"] = "ok" if cursor.fetchone() else "missing"

    # Barthel
    cursor.execute("""
        SELECT id FROM barthel
        WHERE patient_id = ? AND date(data) = date(?)
    """, (hospitalization_id, data_dal))
    check_results["barthel"] = "ok" if cursor.fetchone() else "missing"

    # Braden
    cursor.execute("""
        SELECT id FROM braden
        WHERE patient_id = ? AND date(data) = date(?)
    """, (hospitalization_id, data_dal))
    check_results["braden"] = "ok" if cursor.fetchone() else "missing"

    # MUST
    cursor.execute("""
        SELECT id FROM must
        WHERE patient_id = ? AND date(data) = date(?)
    """, (hospitalization_id, data_dal))
    check_results["must"] = "ok" if cursor.fetchone() else "missing"

    # Rischio disfagia (placeholder)
    check_results["rischio_disfagia"] = "todo"

    # --- Educational Domain ---

    # Diario educatore
    cursor.execute("""
        SELECT testoDiario, tipologia FROM diario_sociale
        WHERE patient_id = ? AND date(dataOra) BETWEEN date(?) AND date(?, '+6 days')
    """, (hospitalization_id, data_dal, data_dal))
    entries = cursor.fetchall()
    if any(row[1] == "Valutazione all'ingresso" for row in entries):
        check_results["diario_educatore"] = "ok"
    elif any("ingresso" in (row[0] or "").lower() for row in entries):
        check_results["diario_educatore"] = "warn"
    else:
        check_results["diario_educatore"] = "missing"

    # Scheda biografica
    cursor.execute("""
        SELECT id FROM schede_biografiche
        WHERE patient_id = ? AND date(data) BETWEEN date(?) AND date(?, '+6 days')
    """, (hospitalization_id, data_dal, data_dal))
    check_results["scheda_biografica"] = "ok" if cursor.fetchone() else "missing"

    # MMSE (placeholder)
    check_results["mmse"] = "todo"

    # --- Physiotherapy Domain ---

    # Diario fisioterapista
    cursor.execute("""
        SELECT id FROM diario_riabilitativo
        WHERE patient_id = ? AND date(dataOra) BETWEEN date(?) AND date(?, '+6 days')
    """, (hospitalization_id, data_dal, data_dal))
    check_results["diario_fisioterapista"] = "ok" if cursor.fetchone() else "missing"

    # Scheda anamnesi
    cursor.execute("""
        SELECT id FROM fisioterapia
        WHERE patient_id = ? AND date(data) BETWEEN date(?) AND date(?, '+6 days')
    """, (hospitalization_id, data_dal, data_dal))
    check_results["scheda_anamnesi"] = "ok" if cursor.fetchone() else "missing"

    # Conley or Tinetti
    cursor.execute("""
        SELECT id FROM conley
        WHERE patient_id = ? AND date(data) BETWEEN date(?) AND date(?, '+6 days')
        UNION
        SELECT id FROM tinetti
        WHERE patient_id = ? AND date(data) BETWEEN date(?) AND date(?, '+6 days')
    """, (hospitalization_id, data_dal, data_dal, hospitalization_id, data_dal, data_dal))
    check_results["conley_tinetti"] = "ok" if cursor.fetchone() else "missing"

    # Morse (if fall history present) — placeholder
    check_results["morse_if_falls"] = "todo"

    # --- Follow-up checks for PAI after 14 days ---
    cursor.execute("""
        SELECT DISTINCT date(data) FROM pai
        WHERE patient_id = ? AND date(data) >= date(?, '+14 days')
    """, (hospitalization_id, data_dal))
    pai_entries = cursor.fetchall()

    pai_date_map = {}  # maps 'PAI_01' → '2023-02-10'

    for idx, (pai_date,) in enumerate(pai_entries, 1):
        prefix = f"PAI_{idx:02}"

        pai_date_map[prefix] = pai_date  # full datetime object

        # Scheda dolore (nrs or painad)
        cursor.execute("""
            SELECT id FROM nrs WHERE patient_id = ? AND date(data) BETWEEN date(?, '-6 days') AND date(?)
            UNION
            SELECT id FROM painad WHERE patient_id = ? AND date(data) BETWEEN date(?, '-6 days') AND date(?)
        """, (hospitalization_id, pai_date, pai_date, hospitalization_id, pai_date, pai_date))
        check_results[f"{prefix}_scheda_dolore"] = "ok" if cursor.fetchone() else "missing"

        # CIRS
        cursor.execute("""
            SELECT id FROM cirs
            WHERE patient_id = ? AND date(data) BETWEEN date(?, '-6 days') AND date(?)
        """, (hospitalization_id, pai_date, pai_date))
        check_results[f"{prefix}_cirs"] = "ok" if cursor.fetchone() else "missing"

        # GBS (placeholder)
        check_results[f"{prefix}_gbs"] = "todo"

        # Barthel
        cursor.execute("""
            SELECT id FROM barthel
            WHERE patient_id = ? AND date(data) BETWEEN date(?, '-6 days') AND date(?)
        """, (hospitalization_id, pai_date, pai_date))
        check_results[f"{prefix}_barthel"] = "ok" if cursor.fetchone() else "missing"

        # Braden
        cursor.execute("""
            SELECT id FROM braden
            WHERE patient_id = ? AND date(data) BETWEEN date(?, '-6 days') AND date(?)
        """, (hospitalization_id, pai_date, pai_date))
        check_results[f"{prefix}_braden"] = "ok" if cursor.fetchone() else "missing"

        # MUST
        cursor.execute("""
            SELECT id FROM must
            WHERE patient_id = ? AND date(data) BETWEEN date(?, '-6 days') AND date(?)
        """, (hospitalization_id, pai_date, pai_date))
        check_results[f"{prefix}_must"] = "ok" if cursor.fetchone() else "missing"

        # Diario infermieristico: disfagia keywords
        cursor.execute("""
            SELECT testoDiario FROM diario_infermieristico
            WHERE patient_id = ? AND date(dataOra) BETWEEN date(?, '-6 days') AND date(?)
        """, (hospitalization_id, pai_date, pai_date))
        entries = cursor.fetchall()
        if any(any(word in (row[0] or "").lower() for word in ["bedside", "rischio disfagia", "gestione della disfagia"]) for row in entries):
            check_results[f"{prefix}_disfagia_diario"] = "ok"
        else:
            check_results[f"{prefix}_disfagia_diario"] = "missing"

        # MMSE (placeholder)
        check_results[f"{prefix}_mmse"] = "todo"

        # NPI, CDR (placeholder)
        check_results[f"{prefix}_npi_cdr"] = "todo"

        # Conley or Tinetti
        cursor.execute("""
            SELECT id FROM conley
            WHERE patient_id = ? AND date(data) BETWEEN date(?, '-6 days') AND date(?)
            UNION
            SELECT id FROM tinetti
            WHERE patient_id = ? AND date(data) BETWEEN date(?, '-6 days') AND date(?)
        """, (hospitalization_id, pai_date, pai_date, hospitalization_id, pai_date, pai_date))
        check_results[f"{prefix}_conley_tinetti"] = "ok" if cursor.fetchone() else "missing"

    return check_results, pai_date_map

def check_indicatore_generale_2(cursor, hospitalization_id, data_dal):
    from datetime import datetime, timedelta

    results = {}

    # Get all PAI + PI dates (sorted, distinct)
    cursor.execute("""
        SELECT DISTINCT date(data) FROM pai WHERE patient_id = ?
        UNION
        SELECT DISTINCT date(data) FROM pi WHERE patient_id = ?
        ORDER BY date(data)
    """, (hospitalization_id, hospitalization_id))
    pai_dates_raw = cursor.fetchall()
    pai_dates = [datetime.strptime(d[0], "%Y-%m-%d") for d in pai_dates_raw]

    if not pai_dates:
        results["ig2_timing_first_pai"] = "missing"
        results["ig2_interval_spacing"] = "missing"
        results["ig2_activities_medical"] = "missing"
        results["ig2_activities_educator"] = "missing"
        results["ig2_activities_fkt"] = "missing"
        return results

    # Check first PAI within 30 days of ricovero
    try:
        dal_date = datetime.strptime(data_dal.split(" ")[0], "%Y-%m-%d")
    except ValueError:
        results["ig2_timing_first_pai"] = "error"
        return results

    if (pai_dates[0] - dal_date).days > 30:
        results["ig2_timing_first_pai"] = "warn"
    else:
        results["ig2_timing_first_pai"] = "ok"

    # Check interval spacing
    interval_valid = all((pai_dates[i+1] - pai_dates[i]).days <= 187 for i in range(len(pai_dates)-1))
    results["ig2_interval_spacing"] = "ok" if interval_valid else "warn"

    # Activity issues: track per interval
    medical_issues = []
    educator_issues = []
    fkt_issues = []

    for i in range(len(pai_dates)-1):
        start = pai_dates[i]
        end = pai_dates[i+1]
        delta_days = (end - start).days
        weeks = max(delta_days // 7, 1)

        cursor.execute("""
            SELECT title, description FROM attivita
            WHERE idRicovero = ? AND date(data) BETWEEN date(?) AND date(?)
        """, (hospitalization_id, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")))
        activities = cursor.fetchall()

        titles = [t.strip().upper() for t, _ in activities]

        # Medical match
        if not any(t in ["MED", "CTRL PRESS"] for t in titles):
            medical_issues.append((start.strftime("%d-%m-%Y"), end.strftime("%d-%m-%Y")))

        # Educator match
        educator_count = sum(t in ["CRUCI", "CORO"] for t in titles)
        if educator_count < weeks:
            educator_issues.append((start.strftime("%d-%m-%Y"), end.strftime("%d-%m-%Y")))

        # FKT match
        fkt_count = sum(t in ["MOBPASS", "PASPOST", "D ASS", "CYC"] for t in titles)
        if fkt_count < (2 * weeks):
            fkt_issues.append((start.strftime("%d-%m-%Y"), end.strftime("%d-%m-%Y")))

    # Add final results
    results["ig2_activities_medical"] = "ok" if not medical_issues else "warn"
    results["ig2_activities_educator"] = "ok" if not educator_issues else "warn"
    results["ig2_activities_fkt"] = "ok" if not fkt_issues else "warn"

    if medical_issues:
        results["ig2_activities_medical_intervals"] = medical_issues
    if educator_issues:
        results["ig2_activities_educator_intervals"] = educator_issues
    if fkt_issues:
        results["ig2_activities_fkt_intervals"] = fkt_issues

    return results

# Connect to the database
conn = sqlite3.connect("borromea.db")
cursor = conn.cursor()

# Load patient list with names
cursor.execute("SELECT codOspite, nome, cognome FROM personal_data")
patients = cursor.fetchall()

for codOspite, nome, cognome in patients:
    cursor.execute("""
        SELECT id, dal, al FROM hospitalizations_history WHERE codOspite = ?
    """, (codOspite,))
    hospitalizations = cursor.fetchall()

    for hospitalization_id, dal, al in hospitalizations:
        year = extract_year_or_status(dal, al)
        checks, pai_dates = check_indicatore_generale_1(cursor, hospitalization_id, dal)
        ig2 = check_indicatore_generale_2(cursor, hospitalization_id, dal)
        all_checks = {**checks, **ig2}

        record = {
            'codOspite': codOspite,
            'nome': nome,
            'cognome': cognome,
            'ricovero_id': hospitalization_id,
            'dal': dal,
            'al': al,
            'year': year,
            'checks': all_checks,
            'pai_dates': pai_dates  # save it for HTML
        }
        results_by_year[year].append(record)

        csv_row = {
            'codOspite': codOspite,
            'nome': nome,
            'cognome': cognome,
            'ricovero_id': hospitalization_id,
            'dal': dal,
            'al': al,
            'year': year,
            **all_checks
        }
        csv_rows.append(csv_row)

# Write CSV
with open("autocontrollo.csv", mode='w', newline='', encoding='utf-8') as f:
    all_fieldnames = set()
    for row in csv_rows:
        all_fieldnames.update(row.keys())
    fieldnames = sorted(all_fieldnames)

    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(csv_rows)


# Write HTML
with open("autocontrollo.html", mode='w', encoding='utf-8') as f:
    f.write(f"<h1>Autocontrollo ({today_str})</h1>")

    for year in sorted(results_by_year.keys(), key=lambda y: (y != "Still Active", -int(y) if isinstance(y, int) else 0)):
        f.write(f"<h2>Hospitalizations ending in {year}</h2>")
        
        for rec in results_by_year[year]:
            f.write(f"<div><h3>{rec['nome']} {rec['cognome']} (codOspite: {rec['codOspite']})</h3>")
            f.write(f"<p><b>Hospitalization {rec['ricovero_id']}</b> (dal: {rec['dal']} - al: {rec['al']})</p>")
            f.write("<h4>Indicatore Generale 1</h4>")
            f.write("<ul>")
            grouped_pai = defaultdict(list)

            for check, status in rec["checks"].items():
                icon = STATUS_ICONS.get(status, '') if isinstance(status, str) else ''
                
                if check.startswith("PAI_"):
                    parts = check.split("_", 2)
                    group_key = f"{parts[0]} {parts[1]}"
                    field_name = parts[2].replace('_', ' ').capitalize()
                    grouped_pai[group_key].append((field_name, icon, status))
                elif not check.startswith("ig2_"):  # only IG1 stuff here
                    f.write(f"<li>{icon} {check.replace('_', ' ').capitalize()}: {status}</li>")
            f.write("</ul>")

            if grouped_pai:
                f.write("<h4>Follow-up PAI checks</h4>")
                f.write("<ul>")
                for pai_label, items in sorted(grouped_pai.items()):
                    pai_date = rec.get("pai_dates", {}).get(pai_label.replace(" ", "_"))
                    label = f"{pai_label} ({pai_date})" if pai_date else pai_label
                    f.write(f"<li><b>{label}</b><ul>")
                    for field_name, icon, status in items:
                        f.write(f"<li>{icon} {field_name}: {status}</li>")
                    f.write("</ul></li>")
                f.write("</ul>")

            # IG2
            f.write("<h4>Indicatore Generale 2</h4>")
            f.write("<ul>")

            IG2_LABELS = {
                "ig2_timing_first_pai": "Primo PAI/PI entro 30 giorni dal ricovero",
                "ig2_interval_spacing": "Intervallo tra PAI/PI max 6 mesi + 7 giorni",
                "ig2_activities_medical": "Attività mediche (es. medicazione LDP, pressione, ossigeno)",
                "ig2_activities_educator": "Attività educatori (min. 1 a settimana)",
                "ig2_activities_fkt": "Attività fisioterapiche (min. 2 a settimana)"
            }

            for check, status in rec["checks"].items():
                # Show only the main IG2 status lines (not _intervals and not lists)
                if check.startswith("ig2_") and not check.endswith("_intervals") and isinstance(status, str):
                    icon = STATUS_ICONS.get(status, '')
                    label = IG2_LABELS.get(check, check.replace('_', ' ').capitalize())
                    f.write(f"<li>{icon} {label}: {status}</li>")

                    # If interval breakdown exists, show them nested
                    interval_key = f"{check}_intervals"
                    if interval_key in rec["checks"] and isinstance(rec["checks"][interval_key], list):
                        for start, end in rec["checks"][interval_key]:
                            f.write(f"<li style='margin-left: 20px'>⏱️ Tra {start} e {end}</li>")

            f.write("</ul>")

    f.write("</body></html>")

conn.close()
