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
        self.cursor = self.conn.cursor() 
        self.create_tables()

    def create_tables(self):
        # تم ضبط الإزاحة هنا لتكون تابعة للكلاس مباشرة
        self.cursor.execute('CREATE TABLE IF NOT EXISTS ranks (gid TEXT, uid TEXT, rank TEXT, PRIMARY KEY(gid, uid))')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS locks (gid TEXT, feature TEXT, status INTEGER DEFAULT 0, PRIMARY KEY(gid, feature))')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS replies (gid TEXT, word TEXT, reply TEXT, media_id BLOB DEFAULT NULL, PRIMARY KEY(gid, word))')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS settings (gid TEXT, key TEXT, value TEXT, PRIMARY KEY(gid, key))')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS activity (gid TEXT, uid TEXT, count INTEGER DEFAULT 0, PRIMARY KEY(gid, uid))')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS punishments (gid TEXT, uid TEXT, type TEXT, PRIMARY KEY(gid, uid))')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS image_blacklist (hash TEXT PRIMARY KEY)')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS warns (gid TEXT, uid TEXT, count INTEGER DEFAULT 0, PRIMARY KEY(gid, uid))')
        self.conn.commit()

    # --- الدوال الخاصة بالإنذارات ---
    def add_warn(self, gid, uid):
        self.cursor.execute("INSERT OR IGNORE INTO warns (gid, uid, count) VALUES (?, ?, 0)", (str(gid), str(uid)))
        self.cursor.execute("UPDATE warns SET count = count + 1 WHERE gid=? AND uid=?", (str(gid), str(uid)))
        self.conn.commit()
        self.cursor.execute("SELECT count FROM warns WHERE gid=? AND uid=?", (str(gid), str(uid)))
        row = self.cursor.fetchone()
        return row[0] if row else 0

    def reset_warns(self, gid, uid):
        self.cursor.execute("DELETE FROM warns WHERE gid=? AND uid=?", (str(gid), str(uid)))
        self.conn.commit()

    def get_warns(self, gid, uid):
        self.cursor.execute("SELECT count FROM warns WHERE gid=? AND uid=?", (str(gid), str(uid)))
        row = self.cursor.fetchone()
        return row[0] if row else 0

    def get_setting(self, gid, key):
        self.cursor.execute("SELECT value FROM settings WHERE gid=? AND key=?", (str(gid), key))
        row = self.cursor.fetchone()
        return row[0] if row else "off"

    # إضافة دوال ناقصة يحتاجها ملف app.py بناءً على الكود الذي أرسلته سابقاً
    def increase_messages(self, gid, uid):
        self.cursor.execute("INSERT OR IGNORE INTO activity (gid, uid, count) VALUES (?, ?, 0)", (str(gid), str(uid)))
        self.cursor.execute("UPDATE activity SET count = count + 1 WHERE gid=? AND uid=?", (str(gid), str(uid)))
        self.conn.commit()

    def get_user_messages(self, gid, uid):
        self.cursor.execute("SELECT count FROM activity WHERE gid=? AND uid=?", (str(gid), str(uid)))
        row = self.cursor.fetchone()
        return row[0] if row else 0

    def get_rank(self, gid, uid):
        self.cursor.execute("SELECT rank FROM ranks WHERE gid=? AND uid=?", (str(gid), str(uid)))
        row = self.cursor.fetchone()
        return row[0] if row else "عضو"

db = BotDB()
