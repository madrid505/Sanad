import time
from datetime import datetime
from database import db

# قاموس لتخزين وقت دخول المشرفين وبداية الجلسة
active_admins = {}

def track_admin_activity(user_id, user_name):
    """تسجيل نشاط المشرف بنظام الجلسات الصافية وتخزين الجلسات التفصيلية"""
    current_time = int(time.time())
    uid = str(user_id)
    ACTIVITY_WINDOW = 600 # 10 دقائق
    
    if uid not in active_admins:
        active_admins[uid] = {
            'last_act': current_time,
            'session_start': current_time,
            'name': user_name
        }
        duration = 0
    else:
        time_diff = current_time - active_admins[uid]['last_act']
        
        if time_diff < ACTIVITY_WINDOW:
            duration = time_diff
            active_admins[uid]['last_act'] = current_time
        else:
            save_finished_session(uid)
            active_admins[uid] = {
                'last_act': current_time,
                'session_start': current_time,
                'name': user_name
            }
            duration = 0

    db.update_admin_stats(uid, seconds=duration, add_msg=True)

def save_finished_session(uid):
    """حفظ الجلسة المنتهية في قاعدة البيانات"""
    if uid in active_admins:
        data = active_admins[uid]
        start_ts = data['session_start']
        end_ts = data['last_act']
        duration_mins = round((end_ts - start_ts) / 60)
        
        if duration_mins >= 1:
            start_dt = datetime.fromtimestamp(start_ts)
            end_dt = datetime.fromtimestamp(end_ts)
            
            db.add_session_log(
                uid, 
                data['name'], 
                start_dt.strftime("%H:%M"), 
                end_dt.strftime("%H:%M"), 
                duration_mins, 
                start_dt.strftime("%Y-%m-%d")
            )

def get_admin_report():
    """تقرير الرادار العام للكل"""
    stats = db.get_all_admins_stats()
    if not stats:
        return "📭 **| السجل الإمبراطوري فارغ.. لا نشاط للمشرفين اليوم.**"

    total_all_msgs = sum(s[2] for s in stats)
    current_ts = int(time.time())
    report = "⚔️ **| رادار الإدارة (24س)**\n━━━━━━━━━━━━━━\n"

    for uid, name, msgs, seconds, last_act in stats:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        time_str = f"{hours}س و {minutes}د" if hours > 0 else f"{minutes}د"
        
        diff = current_ts - last_act
        last_seen = "الآن 🟢" if diff < 60 else f"منذ {diff // 60} د" if diff < 3600 else f"منذ {diff // 3600} س"
        percentage = (msgs / total_all_msgs * 100) if total_all_msgs > 0 else 0
        
        if msgs < 5: status, rank_icon = "خامل جداً 😴", "⚠️"
        elif msgs < 20: status, rank_icon = "مجتهد 👍", "✅"
        else: status, rank_icon = "شعلة نشاط 🔥", "🏆"

        report += f"👤 **المشرف:** {name}\n💬 **الرسائل:** {msgs} ({percentage:.1f}%)\n⏳ **التواجد:** {time_str}\n🕒 **آخر ظهور:** {last_seen}\n{rank_icon} **الحالة:** {status}\n━━━━━━━━━━━━━━\n"

    return report + f"📢 **إجمالي الرسائل:** {total_all_msgs}\n⚖️ يتم التصفير تلقائياً كل 24س."

def get_detailed_session_report():
    """تقرير الجلسات العام لجميع المشرفين"""
    today = datetime.now().strftime("%Y-%m-%d")
    sessions = db.get_daily_sessions(today)
    
    if not sessions:
        return "📭 **| لا يوجد جلسات مفصلة مسجلة لليوم بعد.**"
    
    report = f"📂 **| سـجـل الـجـلـسـات الـتـفـصـيـلي ({today})**\n━━━━━━━━━━━━━━\n"
    organized = {}
    for name, start, end, dur in sessions:
        if name not in organized: organized[name] = []
        organized[name].append(f"⏰ `{start} ← {end}` ({dur} دقيقة)")
    
    for admin_name, logs in organized.items():
        report += f"👤 **{admin_name}:**\n" + "\n".join(f"   • {l}" for l in logs) + "\n───\n"
        
    return report + "━━━━━━━━━━━━━━"

def get_specific_admin_report(query):
    """توليد تقرير شامل ومفصل (مجهر) لمشرف واحد - يعرض كافة الجلسات بما فيها النشطة الآن"""
    admin_data = db.find_admin(query)
    
    if not admin_data:
        return f"❌ **| عذراً.. لا يوجد مشرف مسجل بهذا الاسم أو الآيدي: ({query})**"
    
    uid, name, username, msgs, seconds, last_act = admin_data
    today = datetime.now().strftime("%Y-%m-%d")
    current_ts = int(time.time())
    uid_str = str(uid)
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    time_str = f"{hours}س و {minutes}د" if hours > 0 else f"{minutes}د"
    
    diff = current_ts - last_act
    last_seen = "الآن 🟢" if diff < 60 else f"منذ {diff // 60} د" if diff < 3600 else f"منذ {diff // 3600} س"
    
    # 1. جلب الجلسات المؤرشفة من الداتا بيز
    sessions = db.get_admin_sessions(uid, today)
    
    res = f"📑 **| كـشـف الـنـشـاط الـتـفـصـيـلي الـكـامـل**\n"
    res += f"━━━━━━━━━━━━━━\n"
    res += f"👤 **الاسم:** {name}\n"
    res += f"🔗 **اليوزر:** {username}\n"
    res += f"🆔 **الآيدي:** `{uid}`\n"
    res += f"━━━━━━━━━━━━━━\n"
    res += f"💬 **الرسائل:** `{msgs}`\n"
    res += f"⏳ **إجمالي التواجد:** `{time_str}`\n"
    res += f"🕒 **آخر نشاط:** {last_seen}\n"
    res += f"━━━━━━━━━━━━━━\n"
    res += f"📜 **سجل الجلسات والحركات (اليوم):**\n"
    
    found_any = False
    counter = 1

    # أولاً: عرض الجلسات المنتهية
    if sessions:
        found_any = True
        for start, end, dur in sessions:
            res += f"{counter}- من `{start}` إلى `{end}` ({dur} دقيقة)\n"
            counter += 1
    
    # ثانياً: التحقق إذا كان المشرف لديه جلسة "مفتوحة" الآن في الذاكرة
    if uid_str in active_admins:
        found_any = True
        start_ts = active_admins[uid_str]['session_start']
        start_dt = datetime.fromtimestamp(start_ts).strftime("%H:%M")
        res += f"{counter}- من `{start_dt}` ← إلى الآن (جلسة مستمرة 🟢)\n"

    if not found_any:
        res += "• لا يوجد جلسات مسجلة حتى الآن."
            
    res += f"\n━━━━━━━━━━━━━━"
    return res
