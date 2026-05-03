import time
from database import db # استدعاء نسخة قاعدة البيانات من ملفك

def track_admin_activity(u_id):
    """تحديث أرقام نشاط المشرف بصمت"""
    now = int(time.time())
    
    # جلب البيانات الحالية (نحصل على 7 قيم بفضل التعديل الأخير)
    row = db.get_user_from_radar(u_id)
    if not row: return

    # ترتيب القيم حسب database.py:
    # 0:full_name, 1:username, 2:history, 3:admin_msgs, 4:admin_actions, 5:total_seconds, 6:last_activity
    
    # 1. تحديث عداد الرسائل
    db.cursor.execute("UPDATE users_radar SET admin_msgs = admin_msgs + 1 WHERE uid = ?", (str(u_id),))

    # 2. حساب مدة التواجد (إذا كان النشاط خلال آخر 15 دقيقة)
    last_act = row[6] if row[6] else 0
    total_sec = row[5] if row[5] else 0

    if last_act > 0 and (now - last_act) < 900:
        added_time = now - last_act
        db.cursor.execute("UPDATE users_radar SET total_seconds = total_seconds + ? WHERE uid = ?", (added_time, str(u_id)))
    
    # 3. تحديث وقت النشاط الأخير دائماً
    db.cursor.execute("UPDATE users_radar SET last_activity = ? WHERE uid = ?", (now, str(u_id)))
    db.conn.commit()

def get_admin_report():
    """توليد التقرير الرقمي للمالك"""
    # نجلب المشرفين الذين أرسلوا رسالة واحدة على الأقل اليوم
    db.cursor.execute("SELECT full_name, admin_msgs, admin_actions, total_seconds FROM users_radar WHERE admin_msgs > 0")
    rows = db.cursor.fetchall()
    
    if not rows:
        return "📊 **رادار المشرفين:** لا يوجد نشاط مسجل للمشرفين حالياً."

    report = "👑 **تقرير الرادار الإداري** 👑\n"
    report += "━━━━━━━━━━━━━━\n"
    
    for r in rows:
        name = r[0]
        msgs = r[1]
        actions = r[2]
        seconds = r[3]
        
        # تحويل الثواني لساعات ودقائق
        h = seconds // 3600
        m = (seconds % 3600) // 60
        
        report += (
            f"👤 **المشرف:** {name}\n"
            f"💬 الرسائل: `{msgs}`\n"
            f"⏳ مدة التواجد: `{h}س و {m}د`\n"
            f"━━━━━━━━━━━━━━\n"
        )
    return report
