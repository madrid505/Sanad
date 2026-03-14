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
        self.cursor.execute('CREATE TABLE IF NOT EXISTS ranks (gid TEXT, uid TEXT, rank TEXT, PRIMARY KEY(gid, uid))')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS locks (gid TEXT, feature TEXT, status INTEGER DEFAULT 0, PRIMARY KEY(gid, feature))')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS replies (gid TEXT, word TEXT, reply TEXT, media_id BLOB DEFAULT NULL, PRIMARY KEY(gid, word))')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS settings (gid TEXT, key TEXT, value TEXT, PRIMARY KEY(gid, key))')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS activity (gid TEXT, uid TEXT, count INTEGER DEFAULT 0, PRIMARY KEY(gid, uid))')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS punishments (gid TEXT, uid TEXT, type TEXT, PRIMARY KEY(gid, uid))')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS image_blacklist (hash TEXT PRIMARY KEY)')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS warns (gid TEXT, uid TEXT, count INTEGER DEFAULT 0, PRIMARY KEY(gid, uid))')
        self.conn.commit()

    # --- إدارة الرتب والقيم ---
    def get_rank(self, gid, uid):
        self.cursor.execute("SELECT rank FROM ranks WHERE gid=? AND uid=?", (str(gid), str(uid)))
        row = self.cursor.fetchone()
        return row[0] if row else "عضو"

    def set_rank(self, gid, uid, rank_name):
        self.cursor.execute("INSERT OR REPLACE INTO ranks (gid, uid, rank) VALUES (?, ?, ?)", (str(gid), str(uid), rank_name))
        self.conn.commit()

    def get_rank_value(self, gid, uid):
        rank = self.get_rank(gid, uid)
        ranks_order = {"عضو": 0, "مميز": 1, "ادمن": 2, "مدير": 3, "مالك": 4, "المنشئ": 5}
        return ranks_order.get(rank, 0)

    # --- إدارة التفاعل (المتفاعلين) ---
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

    # --- إدارة الردود المبرمجة ---
    def set_reply(self, gid, word, reply_text, media_id=None):
        # تحويل الميديا إلى bytes إذا كانت موجودة للتخزين في BLOB
        m_id = pickle.dumps(media_id) if media_id else None
        self.cursor.execute("INSERT OR REPLACE INTO replies (gid, word, reply, media_id) VALUES (?, ?, ?, ?)", (str(gid), word, reply_text, m_id))
        self.conn.commit()

    def get_reply_data(self, gid, word):
        self.cursor.execute("SELECT reply, media_id FROM replies WHERE gid=? AND word=?", (str(gid), word))
        row = self.cursor.fetchone()
        if row:
            rep_text = row[0]
            media = pickle.loads(row[1]) if row[1] else None
            return rep_text, media
        return None

    # --- إدارة الإنذارات ---
    def add_warn(self, gid, uid):
        self.cursor.execute("INSERT OR IGNORE INTO warns (gid, uid, count) VALUES (?, ?, 0)", (str(gid), str(uid)))
        self.cursor.execute("UPDATE warns SET count = count + 1 WHERE gid=? AND uid=?", (str(gid), str(uid)))
        self.conn.commit()
        return self.get_warns(gid, uid)

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

db = BotDB()
