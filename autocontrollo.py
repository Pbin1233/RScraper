import sqlite3
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Output containers
results_by_year = defaultdict(list)
csv_rows = []

STATUS_ICONS = {
    "ok": "✅",
    "warn": "⚠️",
    "missing": "❌",
    "todo": "ℹ️"
}

def format_label(key, strip_prefix=None):
    if strip_prefix and key.startswith(strip_prefix):
        key = key[len(strip_prefix):]
    return key.replace("_", " ").capitalize()

def build_dropdown(ricovero_id, check, status):
    real_status = status.replace(" (manual)", "") if isinstance(status, str) else ""
    is_manual = status.endswith(" (manual)") if isinstance(status, str) else False

    def option(value, label):
        selected = "selected" if is_manual and value == real_status else ""
        return f'<option value="{value}" {selected}>{label}</option>'

    return f"""
    <select data-ricovero="{ricovero_id}" data-checkkey="{check}">
      <option value="">--</option>
      <option value="_clear_">🗑️ Cancella override</option>
      {option("ok", "✅ ok")}
      {option("warn", "⚠️ warn")}
      {option("missing", "❌ missing")}
      {option("todo", "ℹ️ todo")}
    </select>
    """

def render_check_block(f, title, checks, ricovero_id, strip_prefix=None):
    f.write(f"<h2>{title}</h2><ul>")
    for key, status in checks.items():
        if not isinstance(status, str):
            continue  # Skip intervals or unexpected non-status entries
        label = format_label(key, strip_prefix)
        clean_status = status.replace(" (manual)", "") if isinstance(status, str) else status
        icon = STATUS_ICONS.get(clean_status, "")
        dropdown = build_dropdown(ricovero_id, key, status)
        f.write(f"<li>{icon} {label}: {status} {dropdown}</li>")
    f.write("</ul>")

def parse_date(d):
    try:
        return datetime.strptime(d, "%Y-%m-%d %H:%M:%S")
    except Exception:
        try:
            return datetime.strptime(d, "%Y-%m-%d")
        except Exception:
            return datetime.min  # fallback for sorting

all_records = sum(results_by_year.values(), [])  # flatten list of lists
all_records.sort(key=lambda r: parse_date(r['al']), reverse=True)  # latest first

today_str = datetime.today().strftime("%d-%m-%Y")

html_file = open("autocontrollo.html", "w", encoding="utf-8")
html_file.write(f"<h1>Autocontrollo ({today_str})</h1>")

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

    # GBS ingresso (within 4 days from dal)
    cursor.execute("""
        SELECT id FROM gbs
        WHERE patient_id = ? AND date(data) BETWEEN date(?) AND date(?, '+3 days')
    """, (hospitalization_id, data_dal, data_dal))
    check_results["gbs"] = "ok" if cursor.fetchone() else "missing"

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

    # MMSE ingresso (within 15 days from dal)
    cursor.execute("""
        SELECT id FROM mmse
        WHERE patient_id = ? AND date(data) BETWEEN date(?) AND date(?, '+14 days')
    """, (hospitalization_id, data_dal, data_dal))
    check_results["mmse"] = "ok" if cursor.fetchone() else "missing"

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

        # GBS pre-PAI (within 7 days before)
        cursor.execute("""
            SELECT id FROM gbs
            WHERE patient_id = ? AND date(data) BETWEEN date(?, '-6 days') AND date(?)
        """, (hospitalization_id, pai_date, pai_date))
        check_results[f"{prefix}_gbs"] = "ok" if cursor.fetchone() else "missing"

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

        # MMSE pre-PAI (within 7 days before)
        cursor.execute("""
            SELECT id FROM mmse
            WHERE patient_id = ? AND date(data) BETWEEN date(?, '-6 days') AND date(?)
        """, (hospitalization_id, pai_date, pai_date))
        check_results[f"{prefix}_mmse"] = "ok" if cursor.fetchone() else "missing"

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

    # --- Collect PAI and PI dates separately ---
    cursor.execute("SELECT DISTINCT date(data) FROM pai WHERE patient_id = ? ORDER BY date(data)", (hospitalization_id,))
    pai_dates = [datetime.strptime(d[0], "%Y-%m-%d") for d in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT date(data) FROM pi WHERE patient_id = ? ORDER BY date(data)", (hospitalization_id,))
    pi_dates = [datetime.strptime(d[0], "%Y-%m-%d") for d in cursor.fetchall()]

    # --- Check first PAI within 30 days of ricovero ---
    try:
        dal_date = datetime.strptime(data_dal.split(" ")[0], "%Y-%m-%d")
    except ValueError:
        results["ig2_timing_first_pai"] = "error"
        return results

    if not pai_dates:
        results["ig2_timing_first_pai"] = "missing"
    elif (pai_dates[0] - dal_date).days > 30:
        results["ig2_timing_first_pai"] = "warn"
    else:
        results["ig2_timing_first_pai"] = "ok"

    # --- Check PAI date intervals ---
    pai_ok = all((pai_dates[i+1] - pai_dates[i]).days <= 187 for i in range(len(pai_dates)-1))
    results["ig2_interval_spacing_pai"] = "ok" if pai_ok else "warn"

    # --- Check PI date intervals ---
    pi_ok = all((pi_dates[i+1] - pi_dates[i]).days <= 187 for i in range(len(pi_dates)-1))
    results["ig2_interval_spacing_pi"] = "ok" if pi_ok else "warn"

    # --- If fewer than 2 PAI, skip activity check ---
    if len(pai_dates) < 2:
        results["ig2_activities_medical"] = "missing"
        results["ig2_activities_educator"] = "missing"
        results["ig2_activities_fkt"] = "missing"
        return results

    # --- Activity mapping check between each pair of PAI dates ---
    medical_issues = []
    educator_issues = []
    fkt_issues = []

    # Add extended pai_dates list with final boundary (for last interval)
    extended_pai_dates = pai_dates[:]
    if pai_dates:
        if al:
            try:
                discharge_date = datetime.strptime(al.split(" ")[0], "%Y-%m-%d")
            except ValueError:
                discharge_date = datetime.today()
        else:
            discharge_date = datetime.today()
        extended_pai_dates.append(discharge_date)

    for i in range(len(extended_pai_dates) - 1):
        start = extended_pai_dates[i]
        end = extended_pai_dates[i + 1]
        delta_days = (end - start).days
        weeks = max(delta_days // 7, 1)

        cursor.execute("""
            SELECT title FROM attivita
            WHERE idRicovero = ? AND date(data) BETWEEN date(?) AND date(?)
        """, (hospitalization_id, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")))
        titles = [t[0].strip() for t in cursor.fetchall()]

        # --- Category matching ---
        if not any(t in ["MED", "CTRL PRESS"] for t in titles):
            medical_issues.append((start.strftime("%d-%m-%Y"), end.strftime("%d-%m-%Y")))

        educator_count = sum(t in ["CRUCI", "CORO", "musica", "CIN", "TOM", "C BEN", "OLI", "G A.A."] for t in titles)
        if educator_count < weeks*0.9:
            educator_issues.append((start.strftime("%d-%m-%Y"), end.strftime("%d-%m-%Y")))

        fkt_count = sum(t in ["MOBPASS", "PASPOST", "D ASS", "CYC", "GPGR", "MA/MR", "PG"] for t in titles)
        if fkt_count < (2 * weeks)*0.9:
            fkt_issues.append((start.strftime("%d-%m-%Y"), end.strftime("%d-%m-%Y")))

    # --- Final status and intervals ---
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

# Load manual overrides into a dict
cursor.execute("SELECT ricovero_id, check_key, override_status FROM manual_overrides")
override_rows = cursor.fetchall()

manual_overrides = defaultdict(dict)
for ricovero_id, key, status in override_rows:
    manual_overrides[ricovero_id][key] = status

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

        all_checks = {**checks, **ig2}  # define all_checks first

        # Apply manual overrides AFTER defining all_checks
        if hospitalization_id in manual_overrides:
            for key, value in manual_overrides[hospitalization_id].items():
                # Always strip any pre-existing "(manual)" or similar suffix
                current_val = all_checks.get(key, "")
                if "(manual)" in current_val:
                    current_val = current_val.replace(" (manual)", "")

                # Override and tag
                all_checks[key] = f"{value} (manual)"

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
all_records = sum(results_by_year.values(), [])  # flatten
all_records.sort(key=lambda r: parse_date(r['al']), reverse=True)

html_file = open("autocontrollo.html", "w", encoding="utf-8")
html_file.write(f"<h1>Autocontrollo ({today_str})</h1>")

# Group records by year
grouped = defaultdict(list)
for rec in all_records:
    grouped[rec["year"]].append(rec)

# Sort years descending, putting "Still Active" at the end
years_sorted = sorted([y for y in grouped if y != "Still Active"], reverse=True)
if "Still Active" in grouped:
    years_sorted.append("Still Active")

years_sorted = reversed(years_sorted)

# Render HTML grouped by year
for year in years_sorted:
    html_file.write(f"<h2>{year}</h2>")

    for rec in grouped[year]:
        ricovero_id = rec["ricovero_id"]

        ingresso_checks = {}
        pai_checks = {}
        ig2_checks = {}

        for key, status in rec["checks"].items():
            if key.startswith("ig2_"):
                ig2_checks[key] = status
            elif key.startswith("PAI_"):
                pai_checks[key] = status
            else:
                ingresso_checks[key] = status

        # Separate ingresso from PAI in IG1
        ig1_ingresso_checks = {}
        pai_blocks = defaultdict(dict)  # e.g. "PAI_01": { "barthel": "ok", ... }

        for key, status in pai_checks.items():
            if "_" in key:
                prefix, suffix = key.split("_", 1)
                if prefix.startswith("PAI"):
                    pai_blocks[prefix][suffix] = status
            else:
                ig1_ingresso_checks[key] = status

        html_file.write(f"<h3>{rec['nome']} {rec['cognome']} — Ricovero {ricovero_id}</h3>")
        html_file.write(f"<p>Dal: {rec['dal']} | Al: {rec['al']}</p>")

        html_file.write(f"<h3>Indicatore Generale 1</h3>")
        render_check_block(html_file, "Ingresso", ingresso_checks, ricovero_id)
        for pai_label in sorted(pai_blocks.keys()):
            html_file.write(f"<h4 style='margin-left: 20px'>{pai_label.replace('_', ' ')}</h4>")
            html_file.write("<ul style='margin-left: 40px'>")
            for subkey, status in pai_blocks[pai_label].items():
                full_key = f"{pai_label}_{subkey}"
                label = subkey.replace("_", " ").capitalize()
                clean_status = status.replace(" (manual)", "") if isinstance(status, str) else status
                icon = STATUS_ICONS.get(clean_status, "")
                dropdown = build_dropdown(ricovero_id, full_key, status)
                html_file.write(f"<li>{icon} {label}: {status} {dropdown}</li>")
            html_file.write("</ul>")

        render_check_block(html_file, "Indicatore Generale 2", ig2_checks, ricovero_id, strip_prefix="ig2_")

        html_file.write("<hr>")
        
html_file.close()


conn.close()
