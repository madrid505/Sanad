import asyncio
import os
from datetime import datetime, timedelta  # أضفنا timedelta هنا
from telethon import TelegramClient, events, types, functions, errors
from database import db
from admin_monitor import track_admin_activity, get_admin_report

# --- إعدادات البوت الملكي ---
API_ID = 33183154
API_HASH = 'ccb195afa05973cf544600ad3c313b84'
BOT_TOKEN = '8393076766:AAG8TZ-dQ7-7ucc_AcSuNUX-QOuLuKFxFC0'
OWNER_ID = 5010882230
# --- تحديث قائمة المجموعات المسموحة ---
ALLOWED_GROUPS = [
    -1003960606586, 
    -1003721123319, 
    -1002052564369, 
    -1002695848824  # الآيدي الجديد الذي طلبته
]

client = TelegramClient('Monopoly_Radar_V5_1', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
radar_lock = asyncio.Lock()

# --- [1] دالة جلب الرتبة الملكية ---
async def get_user_rank(chat_id, user_id):
    if user_id == OWNER_ID: return "المالك الأساسي 👑"
    # أولاً: جلب الرتبة من قاعدة البيانات (الرتب التي رفعتها أنت يدوياً)
    saved_rank = db.get_rank(str(chat_id), user_id)
    if saved_rank and saved_rank != "عضو 👤":
        return saved_rank
    
    # ثانياً: إذا لم يوجد في القاعدة، نتحقق من تليجرام
    try:
        permissions = await client(functions.channels.GetParticipantRequest(channel=chat_id, participant=user_id))
        if isinstance(permissions.participant, types.ChannelParticipantCreator): return "منشئ المجموعة 🎖️"
        if isinstance(permissions.participant, types.ChannelParticipantAdmin): return "مشرف الإدارة 🛡️"
    except: pass
    return "عضو 👤"


# --- [2] محرك الرادار وكاشف الانتحال الصارم ---
async def check_user_radar(user_id, current_name, current_username):
    async with radar_lock:
        uid_str = str(user_id)
        # الكلمات المفتاحية كاملة كما طلبتها سابقاً
        owner_keywords = ["السلايطة", "Alsalayta", "༺۝༒♛ 🅰🅽🅰🆂 ♛༒۝༻", "المالك الاساسي", "المطور الأساسي"]
        
        if any(key in current_name for key in owner_keywords) and user_id != OWNER_ID:
            alert = f"🚨 **| تـنـبـيـه انـتـحـال خـطـيـر**\n━━━━━━━━━━━━━━\n⚠️ **المستخدم:** [{current_name}](tg://user?id={user_id})\n🆔 **الآيدي:** `{user_id}`\n📢 **يحاول انتحال شخصية المطور!**\n━━━━━━━━━━━━━━"
            for gid in ALLOWED_GROUPS:
                try: await client.send_message(gid, alert)
                except: continue

        old_data = db.get_user_from_radar(uid_str)
        if old_data:
            old_name, old_un, history = old_data[0], old_data[1], old_data[2]

            if str(current_name) != str(old_name) or str(current_username) != str(old_un):
                date_now = datetime.now().strftime("%Y-%m-%d %H:%M")
                updated_history = (history + f"• [{date_now}] اسم: {old_name} | يوزر: {old_un}\n")
                
                msg = (f"🚨 **| رادار كـشـف الـهـويـة**\n━━━━━━━━━━━━━━\n"
                       f"👤 **المستخدم:** [{current_name}](tg://user?id={user_id})\n🆔 **الآيدي:** `{user_id}`\n"
                       f"📜 **تغيير اسم:**\n← من: {old_name}\n→ إلى: {current_name}\n━━━━━━━━━━━━━━")
                
                db.sync_user_to_radar(uid_str, current_name, current_username, updated_history)
                for gid in ALLOWED_GROUPS:
                    try: await client.send_message(gid, msg)
                    except: continue
        else:
            db.sync_user_to_radar(uid_str, current_name, current_username)

# --- [3] دورية الرادار (فحص الـ 10,000 عضو كل 5 دقائق) ---
async def names_patrol_task():
    while True:
        total_checked = 0
        for gid in ALLOWED_GROUPS:
            try:
                async for user in client.iter_participants(gid):
                    if user.bot: continue
                    fn = f"{user.first_name} {user.last_name or ''}".strip()
                    un = f"@{user.username}" if user.username else "لا يوجد"
                    await check_user_radar(user.id, fn, un)
                    total_checked += 1
            except: continue
        
        try: await client.send_message(OWNER_ID, f"🔄 **دورية الرادار:** تم فحص `{total_checked}` عضو بنجاح.")
        except: pass
        await asyncio.sleep(900) # 5 دقائق

# --- [4] جرد المغادرين (فوري عند التشغيل + كل 24 ساعة) ---
async def exits_scheduler_task():
    is_initial = True
    while True:
        try:
            exits = db.get_all_exits()
            updated_count = 0
            for e in exits:
                try:
                    u = await client.get_entity(int(e['id']))
                    db.update_exit_user_data(str(u.id), f"{u.first_name} {u.last_name or ''}".strip(), f"@{u.username}" if u.username else "لا يوجد")
                    updated_count += 1
                    await asyncio.sleep(1) 
                except: continue
            
            report_type = "الأولي" if is_initial else "الدوري (24س)"
            report_msg = (f"🚪 **| جرد المغادرين {report_type}**\n━━━━━━━━━━━━━━\n"
                          f"✅ تم تحديث بيانات `{updated_count}` مغادر.\n"
                          f"⏰ التوقيت: `{datetime.now().strftime('%H:%M')}`\n━━━━━━━━━━━━━━")
            await client.send_message(OWNER_ID, report_msg)
            
        except: pass
        is_initial = False
        await asyncio.sleep(86400) # 24 ساعة

# --- [5] مراقبة سجل الإدارة (صيد المغادرين لحظياً) ---
async def monitor_admin_log():
    last_log_id = {}
    while True:
        for gid in ALLOWED_GROUPS:
            try:
                async for log in client.iter_admin_log(gid, limit=5, leave=True):
                    if gid not in last_log_id: last_log_id[gid] = log.id; continue
                    if log.id <= last_log_id[gid]: continue
                    if not log.user or log.user.bot: continue
                    
                    user = log.user
                    fn = f"{user.first_name} {user.last_name or ''}".strip()
                    un = f"@{user.username}" if user.username else "لا يوجد"
                    date_exit = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    # دمج الرتبة قبل الخروج
                    saved_rank = db.get_rank(str(gid), user.id) if hasattr(db, 'get_rank') else "عضو 👤"
                    db.add_to_exit_logs(str(user.id), fn, un, date_exit)
                    
                    report = (f"🚪 **| سـجـل الـمـغـادرة الـمـلـكـي**\n━━━━━━━━━━━━━━\n"
                              f"👤 **المغادر:** [{fn}](tg://user?id={user.id})\n🆔 `{user.id}`\n"
                              f"🎖️ **الرتبة السابقة:** {saved_rank}\n⏰ وقت الخروج: `{date_exit}`\n\n"
                              f"🔍 [اضغط لعرض البروفايل](tg://user?id={user.id})\n━━━━━━━━━━━━━━")
                    await client.send_message(OWNER_ID, report)
                    last_log_id[gid] = log.id
            except: pass
        await asyncio.sleep(30)
        
# --- [5.5] مهمة التصفير الملكي (كل 24 ساعة عند منتصف الليل) ---
async def daily_reset_task():
    while True:
        try:
            now = datetime.now()
            # حساب الوقت المتبقي لمنتصف الليل بدقة
            tomorrow = now + timedelta(days=1)
            reset_time = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
            wait_seconds = (reset_time - now).total_seconds()
            
            await asyncio.sleep(wait_seconds)
            
            # تنفيذ التصفير في قاعدة البيانات
            db.reset_admin_activity()
            
            # إرسال إشعار للمالك بنجاح التصفير
            reset_msg = (f"♻️ **| إشـعـار الإدارة الـمـلـكـي**\n"
                        f"━━━━━━━━━━━━━━\n"
                        f"✅ تم تصفير عدادات نشاط المشرفين بنجاح.\n"
                        f"📅 يبدأ الآن سجل يوم جديد: `{datetime.now().strftime('%Y-%m-%d')}`\n"
                        f"━━━━━━━━━━━━━━")
            await client.send_message(OWNER_ID, reset_msg)
        except Exception as e:
            print(f"Error in reset task: {e}")
            await asyncio.sleep(60)
            
async def apply_penalty(event, target_id, action, target_name, duration_mins=None):
    if target_id == OWNER_ID: return "❌ لا يمكن تنفيذ عقوبات على المالك الأساسي."
    try:
        rights = None
        act_text = ""
        if action == "ban":
            rights = types.ChatBannedRights(until_date=None, view_messages=True)
            act_text = "الطرد النهائي 🚷"
        elif action == "mute":
            until = datetime.now() + timedelta(minutes=duration_mins) if duration_mins else None
            rights = types.ChatBannedRights(until_date=until, send_messages=True)
            act_text = f"الكتم {'لمدة ' + str(duration_mins) + ' دقيقة' if duration_mins else 'للأبد'} 🤐"
        elif action == "unblock":
            rights = types.ChatBannedRights(until_date=None, view_messages=False, send_messages=False)
            act_text = "العفو الملكي وفك القيود ✅"

        await client(functions.channels.EditBannedRequest(event.chat_id, target_id, rights))
        return f"⚖️ **| مـحـكـمـة مـونـوبـولي**\n━━━━━━━━━━━━━━\n👤 **المستهدف:** {target_name}\n🆔 `{target_id}`\n✅ **الإجراء:** {act_text}\n━━━━━━━━━━━━━━"
    except Exception as e: return f"❌ فشل: {str(e)}"
        
# --- [6] معالج الأوامر (النسخة الإمبراطورية المحدثة بنظام الرادار المخصص) ---
@client.on(events.NewMessage(chats=ALLOWED_GROUPS))
async def main_handler(event):
    if not event.sender_id or event.sender.bot: return
    text = event.raw_text
    parts = text.split()
    if not parts: return
    cmd = parts[0]

    # [1] تحديث الرادار اللحظي للمرسل (كاشف الأسماء) - يعمل في كل المجموعات
    fn = f"{event.sender.first_name} {event.sender.last_name or ''}".strip()
    un = f"@{event.sender.username}" if event.sender.username else "لا يوجد"
    await check_user_radar(event.sender_id, fn, un)

    # [2] نظام تتبع نشاط المشرفين (الرادار الجديد)
    rank_text = await get_user_rank(event.chat_id, event.sender_id)
    is_admin = any(r in rank_text for r in ["المالك", "منشئ", "مشرف", "مدير"])
    
    # 🎯 تخصيص الجرد: يتم احتساب المشاركات فقط في هذه المجموعة
        
    MONITOR_GROUP = -1002052564369
    
    if is_admin and event.chat_id == MONITOR_GROUP:
        # 1. جلب الرسالة التي يتم الرد عليها (للتأكد من أنها ليست رداً على بوت ألعاب)
        reply_msg = await event.get_reply_message()
        is_reply_to_bot = reply_msg and reply_msg.sender and reply_msg.sender.bot
        
        # 2. قائمة كلمات الألعاب لتجاهلها (تم إضافة الفواصل المفقودة)
        game_keywords = [
            "روليت", "تخمين", "رياضيات", "صور", "اسلاميات", 
            "انا", "صيد", "حظ", "لعبة", "الصور", "توب", "نقاطي"
        ]
        is_game_cmd = any(word in text for word in game_keywords) 

        # تسجيل النشاط فقط إذا كانت رسالة حقيقية
        if not is_reply_to_bot and not is_game_cmd:
            track_admin_activity(event.sender_id)


    # إذا لم يكن مشرفاً، لا يكمل معالجة الأوامر الإدارية
    if not is_admin: return

    # [3] استخراج الهدف (رد، آيدي، أو يوزر) - شامل لجميع الأنماط مع await
    target_id = None
    if event.is_reply:
        reply_msg = await event.get_reply_message()
        if reply_msg:
            target_id = reply_msg.sender_id
    elif len(parts) > 1:
        if parts[1].isdigit(): 
            target_id = int(parts[1])
        else:
            try:
                u_ent = await client.get_entity(parts[1]) # جلب الآيدي من اليوزر @ مع await
                target_id = u_ent.id
            except: pass

    # [4] أوامر عامة لا تحتاج لهدف (عرض التقارير)
    if not target_id:
        if cmd == "المغادرين":
            exits = db.get_recent_exits(limit=10)
            if not exits: return await event.reply("📭 الأرشيف الأسود فارغ.")
            msg = "📂 **| أرشـيـف الـمـغـادرين الـمـلـكـي**\n━━━━━━━━━━━━━━\n"
            for e in exits: msg += f"👤 {e['name']}\n🆔 `{e['id']}`\n🗓️ {e['date']}\n\n"
            await event.reply(msg + "━━━━━━━━━━━━━━")
        
        elif cmd == "الرادار" and event.sender_id == OWNER_ID:
            # عرض تقرير نشاط المشرفين للمالك فقط مع await
            report = get_admin_report()
            await event.reply(report)
        return

    # [5] جلب بيانات الهدف (تليجرام أولاً ثم الرادار) لضمان الدقة مع await
    target_name = "غير معروف"
    target_un = "لا يوجد"
    try:
        u = await client.get_entity(target_id)
        target_name = f"{u.first_name} {u.last_name or ''}".strip()
        target_un = f"@{u.username}" if u.username else "لا يوجد"
    except:
        db_data = db.get_user_from_radar(str(target_id))
        if db_data:
            target_name, target_un = db_data[0], db_data[1]

    # [6] تنفيذ الأوامر الإدارية (تعمل في كافة المجموعات ALLOWED_GROUPS)
    if cmd == "كشف":
        data = db.get_user_from_radar(str(target_id))
        history = data[2] if data and len(data) > 2 else "لا يوجد سجل سابق"
        res = (f"📋 **| كـشـف الـهـويـة الإمـبـراطـوري**\n━━━━━━━━━━━━━━\n"
               f"👤 **الاسم:** {target_name}\n🆔 **الآيدي:** `{target_id}`\n"
               f"🔗 **اليوزر:** {target_un}\n🎖️ **الرتبة:** {await get_user_rank(event.chat_id, target_id)}\n\n"
               f"📜 **السجل التاريخي:**\n{history}\n━━━━━━━━━━━━━━")
        await event.reply(res)

    elif cmd == "حظر":
        # تطبيق العقوبة مع await كامل
        response = await apply_penalty(event, target_id, "ban", target_name)
        await event.reply(response)

    elif cmd == "كتم":
        response = await apply_penalty(event, target_id, "mute", target_name, 60)
        await event.reply(response)

    elif cmd in ["فك_الحظر", "الغاء_الحظر", "الغاء_الكتم", "فك"]:
        response = await apply_penalty(event, target_id, "unblock", target_name)
        await event.reply(response)

    elif cmd == "رفع_مشرف":
        db.set_rank(str(event.chat_id), target_id, "مشرف الإدارة 🛡️")
        await event.reply(f"✅ تم رفع {target_name} إلى رتبة مشرف.")

    elif cmd == "تنزيل_مشرف":
        db.set_rank(str(event.chat_id), target_id, "عضو 👤")
        await event.reply(f"📉 تم تنزيل {target_name} إلى رتبة عضو.")
            

# --- بدء التشغيل النهائي ---
print("--- [Monopoly Royal Radar V5.1 FINAL Online] ---", flush=True)
client.loop.create_task(names_patrol_task()) 
client.loop.create_task(exits_scheduler_task()) 
client.loop.create_task(monitor_admin_log()) 
client.loop.create_task(daily_reset_task()) 

client.run_until_disconnected()
