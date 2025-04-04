import sqlite3
import requests
from datetime import datetime, timedelta

ATTIVITA_URL = "https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/attivita/pianifica/listpianificazioneutente"
DB_PATH = "borromea.db"

def isoformat_z(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")

def get_db_bounds(id_ricovero):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT MIN(startDate), MAX(startDate) FROM attivita WHERE idRicovero = ?", (id_ricovero,))
    row = cursor.fetchone()
    conn.close()
    min_d = datetime.fromisoformat(row[0]) if row[0] else None
    max_d = datetime.fromisoformat(row[1]) if row[1] else None
    return min_d, max_d

def save_to_db(entries):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for e in entries:
        cursor.execute("""
            INSERT OR REPLACE INTO attivita (
                id, idPianificazione, idAttivita, title, description, data, dalle, alle,
                color, compilatore, idRicovero, codImg, allDay,
                calendarId, startDate, endDate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            e["id"], e["idPianificazione"], e["idAttivita"], e["title"], e["description"],
            e["data"], e["dalle"], e["alle"], e["color"], e["compilatore"],
            e["idRicovero"], e["codImg"], e["allDay"], e["calendarId"],
            e["startDate"], e["endDate"]
        ))
    conn.commit()
    conn.close()

def fetch_attivita(id_ricovero, jwt_token, ricovero_start, ricovero_end=None):
    ricovero_end = ricovero_end or datetime.now()

    print(f"📆 Fetching attività from {ricovero_start.date()} to {ricovero_end.date()}")

    headers = {
        "CBA-JWT": f"Bearer {jwt_token}",
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest"
    }

    params = {
        "_dc": str(int(datetime.utcnow().timestamp() * 1000)),
        "idRicovero": id_ricovero,
        "calendar": "Ext.calendar.model.Calendar-1",
        "startDate": isoformat_z(ricovero_start),
        "endDate": isoformat_z(ricovero_end + timedelta(days=1))
    }

    try:
        res = requests.get(ATTIVITA_URL, headers=headers, params=params, verify=False)
        res.raise_for_status()
        data = res.json().get("data", [])
    except Exception as e:
        print(f"❌ Error during attività request: {e}")
        return 0

    if not data:
        print("⛔ No attività data returned.")
        return 0

    save_to_db(data)
    print(f"✅ {len(data)} attività entries saved.")
    return len(data)
