import sqlite3
import os

class RadarDB:
    def __init__(self):
        # مسار التخزين المتوافق مع Northflank
        self.base_dir = "/app/data"
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir, exist_ok=True)

        self.db_path = os.path.join(self.base_dir, "monopoly_radar_core.db")
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor() 
        self.create_tables()

    def create_tables(self):
        # جدول الرادار المطور: يحتوي على الاسم الحالي، اليوزر، وتاريخ التغييرات (History)
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users_radar (
            uid TEXT PRIMARY KEY, 
            full_name TEXT, 
            username TEXT,
            history TEXT DEFAULT ''
        )''')
        self.conn.commit()

    def get_user_from_radar(self, uid):
        """جلب البيانات المخزنة للمقارنة"""
        self.cursor.execute("SELECT full_name, username, history FROM users_radar WHERE uid=?", (str(uid),))
        return self.cursor.fetchone()

    def sync_user_to_radar(self, uid, full_name, username, updated_history=None):
        """تحديث البيانات وحفظ سجل التغييرات"""
        if updated_history is not None:
            self.cursor.execute("INSERT OR REPLACE INTO users_radar (uid, full_name, username, history) VALUES (?, ?, ?, ?)", 
                                (str(uid), str(full_name), str(username), str(updated_history)))
        else:
            self.cursor.execute("INSERT OR IGNORE INTO users_radar (uid, full_name, username, history) VALUES (?, ?, ?, '')", (str(uid), str(full_name), str(username)))
            self.cursor.execute("UPDATE users_radar SET full_name=?, username=? WHERE uid=?", (str(full_name), str(username), str(uid)))
        self.conn.commit()

db = RadarDB()
