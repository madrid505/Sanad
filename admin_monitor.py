import time
from datetime import datetime
from database import db

# قاموس لتخزين وقت دخول المشرفين وبداية الجلسة
# {uid: {'last_act': timestamp, 'session_start': timestamp, 'name': name}}
active_admins = {}

def track_admin_activity(user_id, user_name):
    """تسجيل نشاط المشرف بنظام الجلسات الصافية وتخزين الجلسات التفصيلية"""
    current_time = int(time.time())
    uid = str(user_id)
    ACTIVITY_WINDOW = 600 # 10 دقائق
    
    if uid not in active_admins:
        # بداية جلسة جديدة تماماً
        active_admins[uid] = {
            'last_act': current_time,
            'session_start': current_time,
            'name': user_name
        }
        duration = 0
    else:
        time_diff = current_time - active_admins[uid]['last_act']
        
        if time_diff < ACTIVITY_WINDOW:
            # المشرف لا يزال نشطاً في نفس الجلسة
            duration = time_diff
            active_admins[uid]['last_act'] = current_time
        else:
            # المشرف عاد بعد انقطاع (أكثر من 10 دقائق) -> نغلق الجلسة السابقة ونبدأ جديدة
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
        
        # نسجل الجلسة فقط إذا كانت دقيقة واحدة أو أكثر
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
    """تقرير الرادار الأصلي (كما هو مع الحفاظ على تنسيقك الملكي)"""
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
    """دالة التقرير التفصيلي الجديد (لأمر تقرير)"""
    today = datetime.now().strftime("%Y-%m-%d")
    sessions = db.get_daily_sessions(today)
    
    if not sessions:
        return "📭 **| لا يوجد جلسات مفصلة مسجلة لليوم بعد.**"
    
    report = f"📂 **| سـجـل الـجـلـسـات الـتـفـصـيـلي ({today})**\n━━━━━━━━━━━━━━\n"
    
    # تنظيم البيانات حسب اسم المشرف
    organized = {}
    for name, start, end, dur in sessions:
        if name not in organized: organized[name] = []
        organized[name].append(f"⏰ `{start} ← {end}` ({dur} دقيقة)")
    
    for admin_name, logs in organized.items():
        report += f"👤 **{admin_name}:**\n" + "\n".join(f"   {l}" for l in logs) + "\n───\n"
        
    return report + "━━━━━━━━━━━━━━"
