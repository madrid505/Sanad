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
# --- تحديث قائمة المجموعات المسموحة ---
ALLOWED_GROUPS = [
    -1003791330278, 
    -1003721123319, 
    -1002052564369, 
    -1002695848824  # الآيدي الجديد الذي طلبته
]

client = TelegramClient('Monopoly_Radar_V5_1', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
radar_lock = asyncio.Lock()

# --- [1] دالة جلب الرتبة الملكية ---
async def get_user_rank(chat_id, user_id):
    if user_id == OWNER_ID: return "المالك الأساسي 👑"
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
            old_name, old_un, history = old_data
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
        await asyncio.sleep(300) # 5 دقائق

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

# --- [6] معالج الأوامر ---
@client.on(events.NewMessage(chats=ALLOWED_GROUPS))
async def main_handler(event):
    if not event.sender_id or event.sender.bot: return
    
    # تحديث لحظي
    fn = f"{event.sender.first_name} {event.sender.last_name or ''}".strip()
    un = f"@{event.sender.username}" if event.sender.username else "لا يوجد"
    await check_user_radar(event.sender_id, fn, un)

    if event.raw_text.startswith("كشف"):
        rank = await get_user_rank(event.chat_id, event.sender_id)
        if "عضو" in rank: return
        
        target_id = None
        parts = event.raw_text.split()
        if event.is_reply:
            target_id = (await event.get_reply_message()).sender_id
        elif len(parts) > 1:
            if parts[1].isdigit(): target_id = int(parts[1])
            else:
                try:
                    u_ent = await client.get_entity(parts[1])
                    target_id = u_ent.id
                except: pass

        if target_id:
            try:
                try:
                    u = await client.get_entity(target_id)
                    curr_name = f"{u.first_name} {u.last_name or ''}".strip()
                    curr_un = f"@{u.username}" if u.username else "لا يوجد"
                except:
                    db_data = db.get_user_from_radar(str(target_id))
                    curr_name = db_data[0] if db_data else "غير معروف"
                    curr_un = db_data[1] if db_data else "غير معروف"

                data = db.get_user_from_radar(str(target_id))
                history = data[2] if data and data[2] else "لا يوجد سجل سابق"
                
                res = (f"📋 **| كـشـف الـهـويـة الإمـبـراطـوري**\n━━━━━━━━━━━━━━\n"
                       f"👤 **الاسم:** {curr_name}\n🆔 **الآيدي:** `{target_id}`\n"
                       f"🔗 **اليوزر:** {curr_un}\n🎖️ **الرتبة:** {await get_user_rank(event.chat_id, target_id)}\n\n"
                       f"📜 **السجل التاريخي:**\n{history}\n━━━━━━━━━━━━━━")
                await event.reply(res)
            except: pass

    elif event.raw_text == "المغادرين":
        rank = await get_user_rank(event.chat_id, event.sender_id)
        if "عضو" in rank: return
        exits = db.get_recent_exits(limit=10)
        if not exits: return await event.reply("📭 الأرشيف الأسود فارغ.")
        msg = "📂 **| أرشـيـف الـمـغـادرين الـمـلـكـي**\n━━━━━━━━━━━━━━\n"
        for e in exits: msg += f"👤 {e['name']}\n🆔 `{e['id']}`\n🗓️ {e['date']}\n\n"
        await event.reply(msg + "━━━━━━━━━━━━━━")

# --- بدء التشغيل النهائي ---
print("--- [Monopoly Royal Radar V5.1 FINAL Online] ---", flush=True)
client.loop.create_task(names_patrol_task()) 
client.loop.create_task(exits_scheduler_task()) 
client.loop.create_task(monitor_admin_log()) 
client.run_until_disconnected()
