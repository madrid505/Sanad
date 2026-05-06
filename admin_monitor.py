import time
from datetime import datetime
from database import db

# قاموس لتخزين وقت نشاط المشرفين في الذاكرة الحية
active_admins = {}

def track_admin_activity(user_id, user_name):
    """تسجيل نشاط المشرف بنظام الجلسات الصافية"""
    current_time = int(time.time())
    uid = str(user_id)
    ACTIVITY_WINDOW = 600 # 10 دقائق كحد أقصى بين الرسائل
    
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
            # إذا انقطع النشاط لأكثر من 10 دقائق، نحفظ القديمة ونبدأ جديدة
            save_finished_session(uid)
            active_admins[uid] = {
                'last_act': current_time,
                'session_start': current_time,
                'name': user_name
            }
            duration = 0

    db.update_admin_stats(uid, seconds=duration, add_msg=True)

def save_finished_session(uid):
    """حفظ الجلسة المنتهية من الذاكرة إلى قاعدة البيانات"""
    uid_str = str(uid)
    if uid_str in active_admins:
        data = active_admins[uid_str]
        start_ts = data['session_start']
        end_ts = data['last_act']
        duration_mins = round((end_ts - start_ts) / 60)
        
        # نحفظ فقط الجلسات التي استمرت دقيقة أو أكثر
        if duration_mins >= 1:
            start_dt = datetime.fromtimestamp(start_ts)
            end_dt = datetime.fromtimestamp(end_ts)
            
            db.add_session_log(
                uid_str, 
                data['name'], 
                start_dt.strftime("%H:%M"), 
                end_dt.strftime("%H:%M"), 
                duration_mins, 
                start_dt.strftime("%Y-%m-%d")
            )

def get_admin_report():
    """تقرير الرادار العام لجميع المشرفين"""
    stats = db.get_all_admins_stats()
    if not stats:
        return "📭 **| السجل الإمبراطوري فارغ.. لا نشاط للمشرفين اليوم.**"

    total_all_msgs = sum(s[2] for s in stats)
    current_ts = int(time.time())
    report = "⚔️ **| رادار الإدارة (24س)**\n━━━━━━━━━━━━━━\n"

    for uid, name, msgs, seconds, last_act in stats:
        uid_str = str(uid)
        
        # التعديل الذكي: إنهاء الجلسة إذا غاب المشرف أكثر من 10 دقائق عند طلب التقرير
        if uid_str in active_admins:
            if (current_ts - active_admins[uid_str]['last_act']) > 600:
                save_finished_session(uid_str)
                del active_admins[uid_str]

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        time_str = f"{hours}س و {minutes}د" if hours > 0 else f"{minutes}د"
        
        actual_last_act = active_admins[uid_str]['last_act'] if uid_str in active_admins else last_act
        diff = current_ts - actual_last_act
        
        last_seen = "الآن 🟢" if diff < 60 else f"منذ {diff // 60} د" if diff < 3600 else f"منذ {diff // 3600} س"
        percentage = (msgs / total_all_msgs * 100) if total_all_msgs > 0 else 0
        
        if msgs < 5: status, rank_icon = "خامل جداً 😴", "⚠️"
        elif msgs < 20: status, rank_icon = "مجتهد 👍", "✅"
        else: status, rank_icon = "شعلة نشاط 🔥", "🏆"

        report += f"👤 **المشرف:** {name}\n💬 **الرسائل:** {msgs} ({percentage:.1f}%)\n⏳ **التواجد:** {time_str}\n🕒 **آخر ظهور:** {last_seen}\n{rank_icon} **الحالة:** {status}\n━━━━━━━━━━━━━━\n"

    return report + f"📢 **إجمالي الرسائل:** {total_all_msgs}\n⚖️ يتم التصفير تلقائياً كل 24س."

def get_detailed_session_report():
    """تقرير الجلسات العام المفصل لجميع المشرفين"""
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
    """توليد تقرير المجهر لمشرف واحد مع الفحص اللحظي لنشاط الجلسة"""
    admin_data = db.find_admin(query)
    
    if not admin_data:
        return f"❌ **| عذراً.. لا يوجد مشرف مسجل بهذا الاسم أو الآيدي: ({query})**"
    
    uid, name, username, msgs, seconds, last_act = admin_data
    today = datetime.now().strftime("%Y-%m-%d")
    current_ts = int(time.time())
    uid_str = str(uid)

    # --- التعديل الجديد: التحقق من "صلاحية" الجلسة المستمرة الآن ---
    if uid_str in active_admins:
        # إذا غاب أكثر من 10 دقائق، نغلق الجلسة فوراً قبل عرض التقرير
        if (current_ts - active_admins[uid_str]['last_act']) > 600:
            save_finished_session(uid_str)
            del active_admins[uid_str]
    
    # حساب وقت التواجد
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    time_str = f"{hours}س و {minutes}د" if hours > 0 else f"{minutes}د"
    
    actual_last_act = active_admins[uid_str]['last_act'] if uid_str in active_admins else last_act
    diff = current_ts - actual_last_act
    
    last_seen = "الآن 🟢" if diff < 60 else f"منذ {diff // 60} د" if diff < 3600 else f"منذ {diff // 3600} س"
    
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

    if sessions:
        found_any = True
        for start, end, dur in sessions:
            res += f"{counter}- من `{start}` إلى `{end}` ({dur} دقيقة)\n"
            counter += 1
    
    # عرض الجلسة النشطة "فقط" إذا كانت فعلاً ضمن نافذة الـ 10 دقائق
    if uid_str in active_admins:
        found_any = True
        start_ts = active_admins[uid_str]['session_start']
        start_dt = datetime.fromtimestamp(start_ts).strftime("%H:%M")
        res += f"{counter}- من `{start_dt}` ← إلى الآن (جلسة مستمرة 🟢)\n"

    if not found_any:
        res += "• لا يوجد جلسات مسجلة حتى الآن."
            
    res += f"\n━━━━━━━━━━━━━━"
    return res
