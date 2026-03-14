import sqlite3
import pickle
import os

class BotDB:
    def __init__(self):
        # إعداد مسار Volume الخاص بـ Northflank
        self.base_dir = "/app/data"
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir, exist_ok=True)

        self.db_path = os.path.join(self.base_dir, "monopoly_royal.db")
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor() # تم حذف السطر الخاطئ هنا
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('CREATE TABLE IF NOT EXISTS ranks (gid TEXT, uid TEXT, rank TEXT, PRIMARY KEY(gid, uid))')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS locks (gid TEXT, feature TEXT, status INTEGER DEFAULT 0, PRIMARY KEY(gid, feature))')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS replies (gid TEXT, word TEXT, reply TEXT, media_id BLOB DEFAULT NULL, PRIMARY KEY(gid, word))')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS settings (gid TEXT, key TEXT, value TEXT, PRIMARY KEY(gid, key))')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS activity (gid TEXT, uid TEXT, count INTEGER DEFAULT 0, PRIMARY KEY(gid, uid))')
        # جدول جديد لتخزين العقوبات (حظر، كتم، إلخ)
        self.cursor.execute('CREATE TABLE IF NOT EXISTS punishments (gid TEXT, uid TEXT, type TEXT, PRIMARY KEY(gid, uid))')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS image_blacklist (hash TEXT PRIMARY KEY)')
        self.conn.commit()

    # --- دالة جديدة لدعم نظام العقوبات الحقيقي ---
    def set_punishment(self, gid, uid, p_type):
        """تسجيل عقوبة للمستخدم في قاعدة البيانات"""
        if p_type == "none":
            self.cursor.execute("DELETE FROM punishments WHERE gid=? AND uid=?", (str(gid), str(uid)))
        else:
            self.cursor.execute("INSERT OR REPLACE INTO punishments (gid, uid, type) VALUES (?, ?, ?)", (str(gid), str(uid), p_type))
        self.conn.commit()

    def get_punishment(self, gid, uid):
        """جلب حالة العقوبة الحالية للعضو"""
        self.cursor.execute("SELECT type FROM punishments WHERE gid=? AND uid=?", (str(gid), str(uid)))
        row = self.cursor.fetchone()
        return row[0] if row else "سجل نظيف ✅"

    # --- بقية الدوال كما هي مع تأكد من النوع (Type Casting) ---
    def increase_messages(self, gid, uid):
        self.cursor.execute("INSERT OR IGNORE INTO activity (gid, uid, count) VALUES (?, ?, 0)", (str(gid), str(uid)))
        self.cursor.execute("UPDATE activity SET count = count + 1 WHERE gid=? AND uid=?", (str(gid), str(uid)))
        self.conn.commit()

    def get_user_messages(self, gid, uid):
        self.cursor.execute("SELECT count FROM activity WHERE gid=? AND uid=?", (str(gid), str(uid)))
        row = self.cursor.fetchone()
        return row[0] if row else 0

    def get_top_active(self, gid, limit=5):
        self.cursor.execute("SELECT uid, count FROM activity WHERE gid=? ORDER BY count DESC LIMIT ?", (str(gid), limit))
        return self.cursor.fetchall()

    def set_rank(self, gid, uid, rank):
        self.cursor.execute("INSERT OR REPLACE INTO ranks (gid, uid, rank) VALUES (?, ?, ?)", (str(gid), str(uid), rank))
        self.conn.commit()

    def get_rank(self, gid, uid):
        self.cursor.execute("SELECT rank FROM ranks WHERE gid=? AND uid=? LIMIT 1", (str(gid), str(uid)))
        row = self.cursor.fetchone()
        return row[0] if row else "عضو"

    def get_rank_value(self, gid, uid):
        rank_name = self.get_rank(gid, uid)
        ranks_weight = {"المنشئ": 5, "مالك": 4, "مدير": 3, "ادمن": 2, "مميز": 1, "عضو": 0}
        return ranks_weight.get(rank_name, 0)

    def toggle_lock(self, gid, feature, status):
        self.cursor.execute("INSERT OR REPLACE INTO locks (gid, feature, status) VALUES (?, ?, ?)", (str(gid), feature, status))
        self.conn.commit()

    def is_locked(self, gid, feature):
        self.cursor.execute("SELECT status FROM locks WHERE gid=? AND feature=?", (str(gid), feature))
        row = self.cursor.fetchone()
        return row[0] == 1 if row else False

    def set_reply(self, gid, word, reply_text, media_id=None):
        m_data = pickle.dumps(media_id) if media_id else None
        self.cursor.execute("INSERT OR REPLACE INTO replies (gid, word, reply, media_id) VALUES (?, ?, ?, ?)", (str(gid), word, reply_text, m_data))
        self.conn.commit()

    def get_reply_data(self, gid, word):
        self.cursor.execute("SELECT reply, media_id FROM replies WHERE gid=? AND word=?", (str(gid), word))
        row = self.cursor.fetchone()
        if row:
            reply_text, m_data = row
            try: media_obj = pickle.loads(m_data) if m_data else None
            except: media_obj = None
            return reply_text, media_obj
        return None

    def set_setting(self, gid, key, value):
        self.cursor.execute("INSERT OR REPLACE INTO settings (gid, key, value) VALUES (?, ?, ?)", (str(gid), key, value))
        self.conn.commit()

    def get_setting(self, gid, key):
        self.cursor.execute("SELECT value FROM settings WHERE gid=? AND key=?", (str(gid), key))
        row = self.cursor.fetchone()
        return row[0] if row else "off"

db = BotDB()
