import time
from datetime import datetime
from database import db

# قاموس لتخزين وقت دخول المشرفين وبداية الجلسة
active_admins = {}

def track_admin_activity(user_id, user_name):
    """تسجيل نشاط المشرف بنظام الجلسات الصافية وتخزين الجلسات التفصيلية"""
    current_time = int(time.time())
    uid = str(user_id)
    ACTIVITY_WINDOW = 600 # 10 دقائق (إذا انقطع أكثر من 10 دقائق تعتبر جلسة جديدة)
    
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
            # إغلاق الجلسة السابقة وحفظها لأن الانقطاع زاد عن 10 دقائق
            save_finished_session(uid)
            # بدء جلسة جديدة فوراً من هذه اللحظة
            active_admins[uid] = {
                'last_act': current_time,
                'session_start': current_time,
                'name': user_name
            }
            duration = 0

    db.update_admin_stats(uid, seconds=duration, add_msg=True)

def save_finished_session(uid):
    """حفظ الجلسة المنتهية في قاعدة البيانات (توثيق كامل)"""
    if uid in active_admins:
        data = active_admins[uid]
        start_ts = data['session_start']
        end_ts = data['last_act']
        duration_mins = round((end_ts - start_ts) / 60)
        
        # نسجل الجلسة حتى لو كانت دقيقة واحدة لضمان الرصد الكامل
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
    """تقرير الرادار العام (إحصائيات مجمعة للكل)"""
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
    """تقرير الجلسات العام لجميع المشرفين (الجرد التاريخي الكامل لليوم)"""
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
        # عرض كل الجلسات بلا استثناء
        report += f"👤 **{admin_name}:**\n" + "\n".join(f"   • {l}" for l in logs) + "\n───\n"
        
    return report + "━━━━━━━━━━━━━━"

def get_specific_admin_report(query):
    """توليد تقرير شامل ومفصل (مجهر) لمشرف واحد - يعرض كافة الجلسات"""
    admin_data = db.find_admin(query)
    
    if not admin_data:
        return f"❌ **| عذراً.. لا يوجد مشرف مسجل بهذا الاسم أو الآيدي: ({query})**"
    
    uid, name, username, msgs, seconds, last_act = admin_data
    today = datetime.now().strftime("%Y-%m-%d")
    current_ts = int(time.time())
    
    # حساب وقت التواجد الإجمالي
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    time_str = f"{hours}س و {minutes}د" if hours > 0 else f"{minutes}د"
    
    # حساب آخر ظهور لحظياً
    diff = current_ts - last_act
    last_seen = "الآن 🟢" if diff < 60 else f"منذ {diff // 60} د" if diff < 3600 else f"منذ {diff // 3600} س"
    
    # جلب جميع جلسات المشرف لليوم من قاعدة البيانات
    sessions = db.get_admin_sessions(uid, today)
    
    # بناء التقرير الإمبراطوري الشامل
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
    
    if not sessions:
        res += "• لا يوجد جلسات مغلقة مسجلة حتى الآن."
    else:
        # هنا التعديل: عرض (كل) الجلسات مهما كان عددها مع ترقيمها
        for i, (start, end, dur) in enumerate(sessions, 1):
            res += f"{i}- من `{start}` إلى `{end}` ({dur} دقيقة)\n"
            
    res += f"\n━━━━━━━━━━━━━━"
    return res
