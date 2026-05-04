import time
from datetime import datetime
from database import db

# قاموس لتخزين وقت دخول المشرفين (لحساب مدة التواجد لحظياً)
active_admins = {}

def track_admin_activity(user_id):
    """تسجيل نشاط المشرف بنظام الجلسات الصافية (10 دقائق)"""
    current_time = int(time.time())
    uid = str(user_id)
    
    # تحديد "نافذة النشاط" بـ 600 ثانية (10 دقائق)
    ACTIVITY_WINDOW = 600 
    
    if uid not in active_admins:
        active_admins[uid] = current_time
        duration = 0
    else:
        time_diff = current_time - active_admins[uid]
        if 0 < time_diff < ACTIVITY_WINDOW:
            duration = time_diff
        else:
            duration = 0
        active_admins[uid] = current_time

    db.update_admin_stats(uid, seconds=duration, add_msg=True)

def get_admin_report():
    """توليد التقرير المرعب بنظام النسب المئوية وآخر ظهور"""
    stats = db.get_all_admins_stats()
    if not stats:
        return "📭 **| السجل الإمبراطوري فارغ.. لا نشاط للمشرفين اليوم.**"

    total_all_msgs = sum(s[2] for s in stats)
    current_ts = int(time.time())
    
    report = "⚔️ **| رادار الإدارة  (24س)**\n"
    report += "━━━━━━━━━━━━━━\n"

    for uid, name, msgs, seconds, last_act in stats:
        # 1. حساب مدة التواجد (تنسيق احترافي للوقت الصافي)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        
        if hours > 0:
            time_str = f"{hours}س و {minutes}د"
        else:
            time_str = f"{minutes}د"
        
        # 2. حساب وقت آخر ظهور بدقة
        diff = current_ts - last_act
        if diff < 60:
            last_seen = "الآن 🟢"
        elif diff < 3600:
            last_seen = f"منذ {diff // 60} د"
        else:
            last_seen = f"منذ {diff // 3600} س"

        # 3. حساب نسبة الاستحواذ
        percentage = (msgs / total_all_msgs * 100) if total_all_msgs > 0 else 0
        
        # 4. تحديد الحالة والتقييم
        if msgs < 5:
            status = "خامل جداً 😴 (تحت المراجعة)"
            rank_icon = "⚠️"
        elif msgs < 20:
            status = "مجتهد 👍"
            rank_icon = "✅"
        else:
            status = "شعلة نشاط 🔥 (ملكي)"
            rank_icon = "🏆"

        # إضافة بيانات المشرف للتقرير باستخدام التنسيق الجديد
        report += f"👤 **المشرف:** {name}\n"
        report += f"💬 **الرسائل:** {msgs} ({percentage:.1f}%)\n"
        report += f"⏳ **التواجد:** {time_str}\n" # هنا استخدمنا الحسبة الجديدة
        report += f"🕒 **آخر ظهور:** {last_seen}\n"
        report += f"{rank_icon} **الحالة:** {status}\n"
        report += "━━━━━━━━━━━━━━\n"

    report += f"📢 **إجمالي رسائل الإدارة:** {total_all_msgs}\n"
    report += f"⏰ **توقيت التحديث:** {datetime.now().strftime('%H:%M')}\n"
    report += "⚖️ **ملاحظة:** يتم تصفير العدادات تلقائياً كل 24س."
    
    return report
