import time
from datetime import datetime
from database import db

# قاموس لتخزين وقت دخول المشرفين (لحساب مدة التواجد لحظياً)
active_admins = {}

def track_admin_activity(user_id):
    """تسجيل نشاط المشرف وحفظ وقت تواجده"""
    current_time = int(time.time())
    uid = str(user_id)
    
    if uid not in active_admins:
        active_admins[uid] = current_time
        duration = 0
    else:
        duration = current_time - active_admins[uid]
        active_admins[uid] = current_time

    # تحديث قاعدة البيانات (إضافة رسالة + ثواني التواجد + وقت النشاط)
    db.update_admin_stats(uid, seconds=duration, add_msg=True)

def get_admin_report():
    """توليد التقرير المرعب بنظام النسب المئوية وآخر ظهور"""
    stats = db.get_all_admins_stats()
    if not stats:
        return "📭 **| السجل الإمبراطوري فارغ.. لا نشاط للمشرفين اليوم.**"

    # حساب إجمالي الرسائل للمجموعة لحساب النسب المئوية
    total_all_msgs = sum(s[2] for s in stats)
    current_ts = int(time.time())
    
    report = "⚔️ **| رادار الإدارة  (24س)**\n"
    report += "━━━━━━━━━━━━━━\n"

    for uid, name, msgs, seconds, last_act in stats:
        # 1. حساب مدة التواجد
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        
        # 2. حساب وقت آخر ظهور بدقة
        diff = current_ts - last_act
        if diff < 60:
            last_seen = "الآن 🟢"
        elif diff < 3600:
            last_seen = f"منذ {diff // 60} د"
        else:
            last_seen = f"منذ {diff // 3600} س"

        # 3. حساب نسبة الاستحواذ (التنافس)
        percentage = (msgs / total_all_msgs * 100) if total_all_msgs > 0 else 0
        
        # 4. تحديد الحالة والتقييم (الضرب بيد من حديد)
        if msgs < 5:
            status = "خامل جداً 😴 (تحت المراجعة)"
            rank_icon = "⚠️"
        elif msgs < 20:
            status = "مجتهد 👍"
            rank_icon = "✅"
        else:
            status = "شعلة نشاط 🔥 (ملكي)"
            rank_icon = "🏆"

        # إضافة بيانات المشرف للتقرير
        report += f"👤 **المشرف:** {name}\n"
        report += f"💬 **الرسائل:** {msgs} ({percentage:.1f}%)\n"
        report += f"⏳ **التواجد:** {hours}س و {minutes}د\n"
        report += f"🕒 **آخر ظهور:** {last_seen}\n"
        report += f"{rank_icon} **الحالة:** {status}\n"
        report += "━━━━━━━━━━━━━━\n"

    report += f"📢 **إجمالي رسائل الإدارة:** {total_all_msgs}\n"
    report += f"⏰ **توقيت التحديث:** {datetime.now().strftime('%H:%M')}\n"
    report += "⚖️ **ملاحظة:** يتم تصفير العدادات تلقائياً كل 24س."
    
    return report
