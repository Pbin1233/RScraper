import sqlite3

def check_indicatore_generale_1(cursor, hospitalization_id, data_dal):
    print(f"    ➤ [Check: INDICATORE GENERALE 1 on {data_dal}]")

    # Diario medico
    cursor.execute("""
        SELECT testoDiario, tipologia FROM diario_medico
        WHERE patient_id = ? AND date(dataOra) = date(?)
    """, (hospitalization_id, data_dal))
    diario_entries = cursor.fetchall()
    diario_ok = any("Valutazione all'ingresso" == row[1] for row in diario_entries)
    diario_warning = any("ingresso" in (row[0] or "").lower() for row in diario_entries)

    if diario_ok:
        print("      ✅ Diario medico: Valutazione all'ingresso found.")
    elif diario_warning:
        print("      ⚠️ Diario medico: 'ingresso' found, but not 'Valutazione all'ingresso'.")
    else:
        print("      ❌ Diario medico: Missing.")

    # Esame obiettivo
    cursor.execute("""
        SELECT id FROM esame_obiettivo
        WHERE patient_id = ? AND date(data) = date(?)
    """, (hospitalization_id, data_dal))
    if cursor.fetchone():
        print("      ✅ Esame obiettivo medico: Present.")
    else:
        print("      ❌ Esame obiettivo medico: Missing.")

    # Scheda dolore: NRS or PAINAD
    cursor.execute("""
        SELECT id FROM nrs WHERE patient_id = ? AND date(data) = date(?)
        UNION
        SELECT id FROM painad WHERE patient_id = ? AND date(data) = date(?)
    """, (hospitalization_id, data_dal, hospitalization_id, data_dal))
    if cursor.fetchone():
        print("      ✅ Scheda dolore (NRS/PAINAD): Present.")
    else:
        print("      ❌ Scheda dolore: Missing.")

    # CIRS
    cursor.execute("""
        SELECT id FROM cirs WHERE patient_id = ? AND date(data) = date(?)
    """, (hospitalization_id, data_dal))
    if cursor.fetchone():
        print("      ✅ CIRS: Present.")
    else:
        print("      ❌ CIRS: Missing.")

    # GBS (placeholder)
    print("      ℹ️ GBS: Check not implemented yet.")

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
                print("      ✅ LDP: Lesione documentata correttamente.")
            else:
                print("      ⚠️ LDP: Lesione present but presInIngr != 'T'.")
        else:
            print("      ❌ LDP: Lesione mentioned but not found in lesioni table.")

    # Catetere / Stomia / Ossigeno → placeholder
    print("      ℹ️ Catetere/Stomia/Ossigeno: Check not implemented yet.")


# Connect to the database
conn = sqlite3.connect("borromea.db")
cursor = conn.cursor()

# Step 1: Get all patients with names
cursor.execute("SELECT codOspite, nome, cognome FROM personal_data")
patients = cursor.fetchall()

for codOspite, nome, cognome in patients:
    print(f"\n--- Patient: {nome} {cognome} (codOspite: {codOspite}) ---")
    
    # Step 2: Get hospitalizations with dal and al
    cursor.execute("""
        SELECT id, dal, al FROM hospitalizations_history WHERE codOspite = ?
    """, (codOspite,))
    hospitalizations = cursor.fetchall()
    
    for hospitalization_id, dal, al in hospitalizations:
        print(f"  Hospitalization ID: {hospitalization_id} | dal: {dal} | al: {al}")
        
        check_indicatore_generale_1(cursor, hospitalization_id, dal)

# Clean up
conn.close()
