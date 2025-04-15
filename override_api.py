import sqlite3
import subprocess

def regenerate_report(self):
    subprocess.run(["python", "autocontrollo.py"])
    return {"status": "regenerated"}

class OverrideAPI:
    def __init__(self, db_path="borromea.db"):
        self.db_path = db_path

    def save_override(self, ricovero_id, check_key, status):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS manual_overrides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ricovero_id INTEGER,
            check_key TEXT,
            override_status TEXT,
            note TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ricovero_id, check_key)
        );
        """)

        if status == "_clear_":
            cursor.execute("""
                DELETE FROM manual_overrides WHERE ricovero_id = ? AND check_key = ?
            """, (int(ricovero_id), check_key))
        else:
            cursor.execute("""
                INSERT INTO manual_overrides (ricovero_id, check_key, override_status)
                VALUES (?, ?, ?)
                ON CONFLICT(ricovero_id, check_key)
                DO UPDATE SET override_status = excluded.override_status
            """, (int(ricovero_id), check_key, status))

        conn.commit()
        conn.close()

        subprocess.run(["python", "autocontrollo.py"])
        return {"success": True}
