import time
from database import db

def track_admin_activity(u_id):
    """تحديث أرقام نشاط المشرف بصمت بطريقة ملكية آمنة"""
    now = int(time.time())
    uid_str = str(u_id)
    
    # 1. جلب البيانات الحالية (نستخدم الدالة الموجودة في database.py)
    row = db.get_user_from_radar(uid_str)
    if not row:
        return

    # ترتيب القيم: 0:name, 1:un, 2:history, 3:msgs, 4:actions, 5:total_sec, 6:last_act
    last_act = row[6] if len(row) > 6 and row[6] else 0
    
    # 2. تحديث عداد الرسائل ووقت النشاط
    # نستخدم execute مباشرة من db لضمان الـ Thread-Safety إذا كان ملفك يدعم ذلك
    try:
        # زيادة الرسائل وتحديث الوقت الأخير
        db.cursor.execute(
            "UPDATE users_radar SET admin_msgs = admin_msgs + 1, last_activity = ? WHERE uid = ?", 
            (now, uid_str)
        )

        # 3. حساب مدة التواجد الذكي (إذا كان النشاط خلال آخر 15 دقيقة)
        if last_act > 0 and (now - last_act) < 900:
            added_time = now - last_act
            db.cursor.execute(
                "UPDATE users_radar SET total_seconds = total_seconds + ? WHERE uid = ?", 
                (added_time, uid_str)
            )
        
        db.conn.commit()
    except Exception as e:
        print(f"⚠️ خطأ في تحديث نشاط الرادار: {e}")

def get_admin_report():
    """توليد التقرير الرقمي الإمبراطوري للمالك"""
    try:
        # نجلب المشرفين النشطين (الذين لديهم رسائل أو تواجد زمن)
        db.cursor.execute(
            "SELECT full_name, admin_msgs, total_seconds FROM users_radar WHERE admin_msgs > 0 ORDER BY admin_msgs DESC"
        )
        rows = db.cursor.fetchall()
        
        if not rows:
            return "📊 **رادار المشرفين:** لا يوجد نشاط مسجل للمشرفين في مجموعة التبادل حالياً."

        report = "👑 **تـقـريـر الـرادار الإداري** 👑\n"
        report += "━━━━━━━━━━━━━━\n"
        
        for r in rows:
            name = r[0]
            msgs = r[1]
            seconds = r[2] if r[2] else 0
            
            # تحويل الثواني لساعات ودقائق بشكل أنيق
            h = seconds // 3600
            m = (seconds % 3600) // 60
            
            # تقييم الأداء (لمسة ملكية)
            status = "🔥 نشط جداً" if msgs > 50 else "✅ متفاعل"
            
            report += (
                f"👤 **المشرف:** {name}\n"
                f"💬 الرسائل: `{msgs}`\n"
                f"⏳ التواجد: `{h}س و {m}د`\n"
                f"📊 الحالة: {status}\n"
                f"━━━━━━━━━━━━━━\n"
            )
        
        report += f"⏰ تم التحديث: `{time.strftime('%H:%M')}`"
        return report
    except Exception as e:
        return f"❌ خطأ في توليد التقرير: {str(e)}"
