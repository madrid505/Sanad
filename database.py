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
        # 1. إنشاء الجداول الأساسية
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users_radar (
            uid TEXT PRIMARY KEY, 
            full_name TEXT, 
            username TEXT, 
            history TEXT DEFAULT '',
            admin_msgs INTEGER DEFAULT 0,
            admin_actions INTEGER DEFAULT 0,
            total_seconds INTEGER DEFAULT 0,
            last_activity INTEGER DEFAULT 0
        )''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS exit_logs (
            uid TEXT PRIMARY KEY, full_name TEXT, username TEXT, exit_date TEXT
        )''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS user_ranks (
            chat_id TEXT, user_id TEXT, rank TEXT, PRIMARY KEY (chat_id, user_id)
        )''')
        
        # 2. التأكد من وجود أعمدة المراقبة (للترقية من نسخ قديمة)
        columns = [
            ("admin_msgs", "INTEGER DEFAULT 0"),
            ("admin_actions", "INTEGER DEFAULT 0"),
            ("total_seconds", "INTEGER DEFAULT 0"),
            ("last_activity", "INTEGER DEFAULT 0")
        ]
        for col_name, col_type in columns:
            try:
                self.cursor.execute(f"ALTER TABLE users_radar ADD COLUMN {col_name} {col_type}")
            except:
                pass 

        self.conn.commit()

    # --- دوال الرادار المطورة ---
    def get_user_from_radar(self, uid):
        self.cursor.execute("SELECT full_name, username, history, admin_msgs, admin_actions, total_seconds, last_activity FROM users_radar WHERE uid=?", (str(uid),))
        return self.cursor.fetchone()

    def sync_user_to_radar(self, uid, full_name, username, updated_history=None):
        uid_str = str(uid)
        # نستخدم INSERT OR IGNORE لضمان وجود المستخدم أولاً
        self.cursor.execute("INSERT OR IGNORE INTO users_radar (uid, full_name, username, history) VALUES (?, ?, ?, '')", 
                            (uid_str, str(full_name), str(username)))
        
        # التحديث الذكي: نحدث الاسم واليوزر والسجل فقط، دون لمس العدادات
        if updated_history is not None:
            self.cursor.execute("UPDATE users_radar SET full_name=?, username=?, history=? WHERE uid=?", 
                                (str(full_name), str(username), str(updated_history), uid_str))
        else:
            self.cursor.execute("UPDATE users_radar SET full_name=?, username=? WHERE uid=?", 
                                (str(full_name), str(username), uid_str))
        self.conn.commit()

    # --- دوال الرتب الملكية ---
    def set_rank(self, chat_id, user_id, rank_name):
        self.cursor.execute("INSERT OR REPLACE INTO user_ranks (chat_id, user_id, rank) VALUES (?, ?, ?)",
                            (str(chat_id), str(user_id), str(rank_name)))
        self.conn.commit()

    def get_rank(self, chat_id, user_id):
        self.cursor.execute("SELECT rank FROM user_ranks WHERE chat_id = ? AND user_id = ?", (str(chat_id), str(user_id)))
        result = self.cursor.fetchone()
        return result[0] if result else "عضو 👤"

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
