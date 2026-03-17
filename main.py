import asyncio
import os
from datetime import datetime
from telethon import TelegramClient, events, types, functions, errors
from database import db

# --- إعدادات البوت الملكي ---
API_ID = 33183154
API_HASH = 'ccb195afa05973cf544600ad3c313b84'
BOT_TOKEN = '8393076766:AAG8TZ-dQ7-7ucc_AcSuNUX-QOuLuKFxFC0'
OWNER_ID = 5010882230
ALLOWED_GROUPS = [-1003791330278, -1003721123319, -1002052564369]

client = TelegramClient('Monopoly_Radar_V1', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# قفل لمنع تكرار التنبيهات في نفس اللحظة (Race Condition Fix)
radar_lock = asyncio.Lock()

# --- [1] دالة التحقق من الرتبة ---
async def get_user_rank(chat_id, user_id):
    if user_id == OWNER_ID:
        return "المالك الأساسي 👑"
    try:
        permissions = await client(functions.channels.GetParticipantRequest(channel=chat_id, participant=user_id))
        if isinstance(permissions.participant, types.ChannelParticipantCreator):
            return "منشئ المجموعة 🎖️"
        if isinstance(permissions.participant, types.ChannelParticipantAdmin):
            return "مشرف الإدارة 🛡️"
    except: pass
    return "عضو 👤"

# --- [2] محرك الرادار وكاشف الانتحال (مع سد الثغرات) ---
async def check_user_radar(user_id, current_name, current_username, chat_id=None):
    async with radar_lock: # منع التكرار
        uid_str = str(user_id)
        
        # كشف انتحال الشخصية
        owner_keywords = ["السلايطة", "Alsalayta", "༺۝༒♛ 🅰🅽🅰🆂 ♛༒۝༻", "المالك الاساسي", "المطور الأساسي"]
        if any(key in current_name for key in owner_keywords) and user_id != OWNER_ID:
            alert = f"🚨 **| تـنـبـيـه انـتـحـال خـطـيـر**\n━━━━━━━━━━━━━━\n⚠️ **المستخدم:** [{current_name}](tg://user?id={user_id})\n🆔 **الآيدي:** `{user_id}`\n\n📢 **يحاول استخدام اسم أو لقب المطور!**\n━━━━━━━━━━━━━━"
            for gid in ALLOWED_GROUPS:
                try: await client.send_message(gid, alert)
                except: continue

        # المقارنة مع الأرشيف
        old_data = db.get_user_from_radar(uid_str)
        if old_data:
            old_name, old_un, history = old_data
            if str(current_name) != str(old_name) or str(current_username) != str(old_un):
                date_now = datetime.now().strftime("%Y-%m-%d %H:%M")
                new_entry = f"• [{date_now}] اسم: {old_name} | يوزر: {old_un}\n"
                updated_history = (history + new_entry)
                
                # الجزء المعدل داخل check_user_radar
                msg = (f"🚨 **| رادار كـشـف الـهـويـة**\n"
                       f"━━━━━━━━━━━━━━\n"
                       f"👤 **المستخدم:** [{current_name}](tg://user?id={user_id})\n"
                       f"🆔 **الآيدي:** `{user_id}`\n"
                       f"🔗 **اليوزر الحالي:** {current_username}\n\n") # جعلنا اليوزر يظهر هنا دائماً
                
                if str(current_name) != str(old_name):
                    msg += f"📜 **تغيير اسم:**\n← من: {old_name}\n→ إلى: {current_name}\n\n"
                
                if str(current_username) != str(old_un):
                    msg += f"🔗 **تغيير يوزر:**\n← من: {old_un}\n→ إلى: {current_username}\n"
                
                msg += "━━━━━━━━━━━━━━"
                
                db.sync_user_to_radar(uid_str, current_name, current_username, updated_history)
                for gid in ALLOWED_GROUPS:
                    try: await client.send_message(gid, msg)
                    except: continue
                
        else:
            db.sync_user_to_radar(uid_str, current_name, current_username)

# --- [3] نظام مراقبة سجل الإدارة (صيد المغادرين) ---
async def monitor_admin_log():
    last_log_id = {}
    while True:
        for gid in ALLOWED_GROUPS:
            try:
                async for log in client.iter_admin_log(gid, limit=5, leave=True):
                    if gid not in last_log_id: last_log_id[gid] = log.id; continue
                    if log.id <= last_log_id[gid]: continue
                    
                    if not log.user or log.user.bot: continue # ثغرة البيانات المفقودة
                    
                    user = log.user
                    fn = f"{user.first_name} {user.last_name or ''}".strip()
                    un = f"@{user.username}" if user.username else "لا يوجد"
                    
                    # جلب رتبته من الداتابيز قبل تسجيل الخروج (لتحقيق الجرد الشامل)
                    old_data = db.get_user_from_radar(str(user.id))
                    saved_rank = "عضو 👤" # افتراضي
                    
                    date_exit = datetime.now().strftime("%Y-%m-%d %H:%M")
                    db.add_to_exit_logs(str(user.id), fn, un, date_exit)
                    
                    report = (
                        f"🚪 **| سـجـل الـمـغـادرة الـمـلـكـي**\n"
                        f"━━━━━━━━━━━━━━\n"
                        f"👤 **المغادر:** [{fn}](tg://user?id={user.id})\n"
                        f"🆔 **الآيدي:** `{user.id}`\n"
                        f"🔗 **اليوزر:** {un}\n"
                        f"⏰ **وقت الخروج:** `{date_exit}`\n\n"
                        f"🔍 [اضغط لعرض البروفايل](tg://user?id={user.id})\n"
                        f"━━━━━━━━━━━━━━"
                    )
                    await client.send_message(OWNER_ID, report)
                    last_log_id[gid] = log.id
            except: pass
        await asyncio.sleep(30)

# --- [4] الدورية التفتيشية (كل 5 دقائق) ---
async def patrol_system():
    while True:
        start_time = datetime.now()
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

        report_msg = (f"👑 **| تـقـريـر الـدورِيـة الـمـلـكـيـة**\n━━━━━━━━━━━━━━\n"
                      f"✅ **تم جرد المجموعات بنجاح.**\n📊 **المفحوصين:** `{total_checked}`\n"
                      f"⏰ **التوقيت:** `{datetime.now().strftime('%H:%M')}`\n━━━━━━━━━━━━━━")
        try: await client.send_message(OWNER_ID, report_msg)
        except: pass
        await asyncio.sleep(300)

# --- [5] دورية المغادرين (تحديث كل 24 ساعة) ---
async def daily_exit_patrol():
    while True:
        await asyncio.sleep(86400)
        try:
            exits = db.get_all_exits()
            for e in exits:
                try:
                    u = await client.get_entity(int(e['id']))
                    db.update_exit_user_data(str(u.id), f"{u.first_name} {u.last_name or ''}".strip(), f"@{u.username}" if u.username else "لا يوجد")
                except (errors.UserPrivacyRestrictedError, errors.UserIdInvalidError): continue
                except: continue
                await asyncio.sleep(2)
        except: pass

# --- [6] معالج الرسائل والأوامر ---
@client.on(events.NewMessage(chats=ALLOWED_GROUPS))
async def main_handler(event):
    if not event.sender_id or event.sender.bot: return
    
    # الرادار اللحظي
    fn = f"{event.sender.first_name} {event.sender.last_name or ''}".strip()
    un = f"@{event.sender.username}" if event.sender.username else "لا يوجد"
    await check_user_radar(event.sender_id, fn, un)

    if event.raw_text.startswith(("كشف", "المغادرين")):
        rank = await get_user_rank(event.chat_id, event.sender_id)
        if "عضو" in rank: return

        # الجزء المعدل داخل main_handler لتعامل صحيح مع الآيدي
        if event.raw_text.startswith("كشف"):
            target_id = None
            parts = event.raw_text.split()

            if event.is_reply:
                target_id = (await event.get_reply_message()).sender_id
            elif len(parts) > 1:
                input_data = parts[1]
                if input_data.isdigit(): # إذا كان المدخل رقماً (آيدي)
                    target_id = int(input_data)
                else: # إذا كان المدخل يوزرنيم
                    try:
                        u_entity = await client.get_entity(input_data)
                        target_id = u_entity.id
                    except: pass

            if target_id:
                try:
                    # محاولة جلب البيانات من تليجرام أو الداتابيز
                    try:
                        u = await client.get_entity(target_id)
                        curr_name = f"{u.first_name} {u.last_name or ''}".strip()
                        curr_un = f"@{u.username}" if u.username else "لا يوجد"
                    except:
                        # إذا لم يجد تليجرام العضو (غادر تماماً)، نجلب آخر اسم من الداتابيز
                        db_data = db.get_user_from_radar(str(target_id))
                        curr_name = db_data[0] if db_data else "غير معروف"
                        curr_un = db_data[1] if db_data else "غير معروف"

                    data = db.get_user_from_radar(str(target_id))
                    history = data[2] if data and data[2] else "لا يوجد سجل سابق"
                    
                    res = (f"📋 **| كـشـف الـهـويـة الإمـبـراطـوري**\n━━━━━━━━━━━━━━\n"
                           f"👤 **الاسم:** {curr_name}\n🆔 **الآيدي:** `{target_id}`\n"
                           f"🔗 **اليوزر:** {curr_un}\n"
                           f"🎖️ **الرتبة:** {await get_user_rank(event.chat_id, target_id)}\n\n"
                           f"📜 **السجل:**\n{history}\n━━━━━━━━━━━━━━")
                    await event.reply(res)
                except Exception as e:
                    await event.reply(f"❌ فشل العثور على بيانات للآيدي: `{target_id}`")
                
        elif event.raw_text == "المغادرين":
            exits = db.get_recent_exits(limit=10)
            if not exits: return await event.reply("📭 الأرشيف الأسود فارغ.")
            msg = "📂 **| أرشـيـف الـمـغـادرين الـمـلـكـي**\n━━━━━━━━━━━━━━\n"
            for e in exits: msg += f"👤 {e['name']}\n🆔 `{e['id']}`\n🗓️ {e['date']}\n\n"
            await event.reply(msg + "━━━━━━━━━━━━━━")

# --- بدء التشغيل ---
print("--- [Monopoly Royal Radar V2 Online] ---", flush=True)
client.loop.create_task(patrol_system())
client.loop.create_task(monitor_admin_log())
client.loop.create_task(daily_exit_patrol())
client.run_until_disconnected()
