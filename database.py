import sqlite3
import os

class RadarDB:
    def __init__(self):
        # مسار التخزين المتوافق مع Northflank Volume
        self.base_dir = "/app/data"
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir, exist_ok=True)

        self.db_path = os.path.join(self.base_dir, "monopoly_radar_core.db")
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor() 
        self.create_tables()

    def create_tables(self):
        # 1. جدول الرادار الأساسي
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users_radar (
            uid TEXT PRIMARY KEY, 
            full_name TEXT, 
            username TEXT,
            history TEXT DEFAULT ''
        )''')
        # 2. جدول أرشيف المغادرين (الأرشيف الأسود)
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS exit_logs (
            uid TEXT PRIMARY KEY,
            full_name TEXT,
            username TEXT,
            exit_date TEXT
        )''')
        self.conn.commit()

    # --- دوال الرادار ---
    def get_user_from_radar(self, uid):
        self.cursor.execute("SELECT full_name, username, history FROM users_radar WHERE uid=?", (str(uid),))
        return self.cursor.fetchone()

    def sync_user_to_radar(self, uid, full_name, username, updated_history=None):
        if updated_history is not None:
            self.cursor.execute("INSERT OR REPLACE INTO users_radar (uid, full_name, username, history) VALUES (?, ?, ?, ?)", 
                                (str(uid), str(full_name), str(username), str(updated_history)))
        else:
            self.cursor.execute("INSERT OR IGNORE INTO users_radar (uid, full_name, username, history) VALUES (?, ?, ?, '')", (str(uid), str(full_name), str(username)))
            self.cursor.execute("UPDATE users_radar SET full_name=?, username=? WHERE uid=?", (str(full_name), str(username), str(uid)))
        self.conn.commit()

    # --- دوال سجل المغادرين ---
    def add_to_exit_logs(self, uid, full_name, username, exit_date):
        self.cursor.execute("INSERT OR REPLACE INTO exit_logs (uid, full_name, username, exit_date) VALUES (?, ?, ?, ?)",
                            (str(uid), str(full_name), str(username), str(exit_date)))
        self.conn.commit()

    def get_recent_exits(self, limit=10):
        self.cursor.execute("SELECT uid, full_name, username, exit_date FROM exit_logs ORDER BY exit_date DESC LIMIT ?", (limit,))
        rows = self.cursor.fetchall()
        return [{'id': r[0], 'name': r[1], 'un': r[2], 'date': r[3]} for r in rows]

    def get_all_exits(self):
        self.cursor.execute("SELECT uid, full_name, username FROM exit_logs")
        rows = self.cursor.fetchall()
        return [{'id': r[0], 'name': r[1], 'un': r[2]} for r in rows]

    def update_exit_user_data(self, uid, new_name, new_un):
        self.cursor.execute("UPDATE exit_logs SET full_name=?, username=? WHERE uid=?", (str(new_name), str(new_un), str(uid)))
        self.conn.commit()

db = RadarDB()
