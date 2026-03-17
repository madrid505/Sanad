import asyncio
import os
from datetime import datetime
from telethon import TelegramClient, events, types, functions
from database import db

# --- إعدادات البوت الملكي ---
API_ID = 33183154
API_HASH = 'ccb195afa05973cf544600ad3c313b84'
BOT_TOKEN = '8393076766:AAG8TZ-dQ7-7ucc_AcSuNUX-QOuLuKFxFC0'
OWNER_ID = 5010882230
ALLOWED_GROUPS = [-1003791330278, -1003721123319, -1002052564369]

client = TelegramClient('Monopoly_Radar_V1', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# --- دالة التحقق من الرتبة (تلقائياً من تليجرام) ---
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

# --- محرك الرادار وكاشف الانتحال ---
async def check_user_radar(user_id, current_name, current_username):
    uid_str = str(user_id)
    
    # 1. كشف انتحال الشخصية
    owner_keywords = ["السلايطة", "Alsalayta", "༺۝༒♛ 🅰🅽🅰🆂 ♛༒۝༻", "المالك الاساسي", "المطور الأساسي"]

    if any(key in current_name for key in owner_keywords) and user_id != OWNER_ID:
        alert = f"🚨 **| تـنـبـيـه انـتـحـال خـطـيـر**\n━━━━━━━━━━━━━━\n⚠️ **المستخدم:** [{current_name}](tg://user?id={user_id})\n🆔 **الآيدي:** `{user_id}`\n\n📢 **يحاول استخدام اسم أو لقب المطور!**\n━━━━━━━━━━━━━━"
        for gid in ALLOWED_GROUPS:
            try: await client.send_message(gid, alert)
            except: continue

    # 2. المقارنة مع الأرشيف (كشف تغيير الاسم والمعرف)
    old_data = db.get_user_from_radar(uid_str)
    if old_data:
        old_name, old_un, history = old_data
        if str(current_name) != str(old_name) or str(current_username) != str(old_un):
            date_now = datetime.now().strftime("%Y-%m-%d %H:%M")
            new_entry = f"• [{date_now}] اسم: {old_name} | يوزر: {old_un}\n"
            updated_history = (history + new_entry)
            
            msg = f"🚨 **| رادار كـشـف الـهـويـة**\n━━━━━━━━━━━━━━\n👤 **المستخدم:** [{current_name}](tg://user?id={user_id})\n🆔 **الآيدي:** `{user_id}`\n\n"
            
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

# --- الدورية التفتيشية (كل 5 دقائق) ---
async def patrol_system():
    while True:
        start_time = datetime.now()
        total_checked = 0
        print(f"[{start_time.strftime('%H:%M')}] بدأت الدورية التفتيشية السريعة (5 دقائق)...", flush=True)
        
        for gid in ALLOWED_GROUPS:
            try:
                async for user in client.iter_participants(gid):
                    if user.bot: continue
                    fn = f"{user.first_name} {user.last_name or ''}".strip()
                    un = f"@{user.username}" if user.username else "لا يوجد"
                    await check_user_radar(user.id, fn, un)
                    total_checked += 1
            except Exception as e:
                print(f"خطأ في الدورية للمجموعة {gid}: {e}", flush=True)

        end_time = datetime.now()
        duration = (end_time - start_time).seconds
        
        report_msg = (
            f"👑 **| تـقـريـر الـدورِيـة الـمـلـكـيـة**\n"
            f"━━━━━━━━━━━━━━\n"
            f"✅ **تم جرد المجموعات بنجاح.**\n\n"
            f"📊 **الإحصائيات:**\n"
            f"• الأعضاء المفحوصين: `{total_checked}`\n"
            f"• وقت التنفيذ: `{duration}` ثانية\n"
            f"• الدورة القادمة بعد: `5 دقائق`\n"
            f"• التوقيت: `{end_time.strftime('%H:%M')}`\n"
            f"━━━━━━━━━━━━━━"
        )
        try:
            await client.send_message(OWNER_ID, report_msg)
        except Exception as e:
            print(f"فشل إرسال التقرير للمالك: {e}", flush=True)

        # تم التعديل إلى 300 ثانية (5 دقائق)
        await asyncio.sleep(300)

# --- معالج الرسائل وأمر كشف ---
@client.on(events.NewMessage(chats=ALLOWED_GROUPS))
async def main_handler(event):
    user = await event.get_sender()
    if not user or user.bot: return
    
    fn = f"{user.first_name} {user.last_name or ''}".strip()
    un = f"@{user.username}" if user.username else "لا يوجد"
    await check_user_radar(event.sender_id, fn, un)

    if event.raw_text.startswith("كشف"):
        target_id = None
        target_user = None
        parts = event.raw_text.split()

        if event.is_reply:
            rep = await event.get_reply_message()
            target_id = rep.sender_id
        elif len(parts) > 1:
            input_data = parts[1]
            try:
                if input_data.isdigit(): target_id = int(input_data)
                else: target_user = await client.get_entity(input_data); target_id = target_user.id
            except: pass

        if target_id:
            try:
                if not target_user: target_user = await client.get_entity(target_id)
                curr_name = f"{target_user.first_name} {target_user.last_name or ''}".strip()
                curr_un = f"@{target_user.username}" if target_user.username else "لا يوجد"
                
                radar_data = db.get_user_from_radar(str(target_id))
                history_text = radar_data[2] if radar_data and radar_data[2] else "لا يوجد سجل سابق"
                rank = await get_user_rank(event.chat_id, target_id)
                
                response = (
                    f"📋 **| كـشـف الـهـويـة الإمـبـراطـوري**\n━━━━━━━━━━━━━━\n"
                    f"👤 **الاسم الحالي:** {curr_name}\n"
                    f"🆔 **الآيدي:** `{target_id}`\n"
                    f"🔗 **اليوزر:** {curr_un}\n"
                    f"🎖️ **الرتبة:** {rank}\n\n"
                    f"📜 **سجل التغييرات المكتشفة:**\n{history_text}\n"
                    f"━━━━━━━━━━━━━━"
                )
                await event.reply(response)
            except:
                await event.reply("❌ لم أتمكن من العثور على بيانات هذا المستخدم.")

# --- بدء التشغيل ---
print("--- [Monopoly Royal Radar System Online] ---", flush=True)
client.loop.create_task(patrol_system())
client.run_until_disconnected()
