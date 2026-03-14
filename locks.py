import re
import io
from telethon import events
from database import db
# نعتبر أن hasher موجود، إذا واجهت مشكلة تأكد من وجود الملف
try: from hasher import get_image_hash
except: get_image_hash = None

from __main__ import client, ALLOWED_GROUPS, check_privilege 

# خريطة الميزات المحدثة
FEATURES = {
    "الروابط": "links",
    "الصور": "photos",
    "الملصقات": "stickers",
    "المتحركة": "gifs",
    "التوجيه": "forward",
    "المعرفات": "usernames",
    "الفيديوهات": "videos",
    "البصمات": "voice",
    "الملفات": "files",
    "الجهات": "contacts",
    "الترحيب": "welcome_status"
}

# --- 1. معالج الحذف التلقائي الذكي ---
@client.on(events.NewMessage(chats=ALLOWED_GROUPS))
async def auto_protection_handler(event):
    # استثناء الإدارة والمميزين (المقام السامي مشمول برتبة أعلى من مميز)
    if await check_privilege(event, "مميز"):
        return

    gid = str(event.chat_id)
    msg = event.raw_text or "" 

    try:
        # 1. فحص الروابط والمعرفات (Regex مطور)
        if db.is_locked(gid, "links"):
            if re.search(r'(https?://\S+|t\.me/\S+|www\.\S+|\S+\.(me|xyz|info|tk|ml|ga|cf|gq|top|rocks|site|online))', msg):
                await event.delete()
                return

        if db.is_locked(gid, "usernames"):
            if re.search(r'@\S+', msg):
                await event.delete()
                return

        # 2. فحص الوسائط
        if event.photo:
            if db.is_locked(gid, "photos"):
                await event.delete()
                return
            # فحص البصمة (Blacklist) للصور
            if get_image_hash:
                photo_bytes = await event.download_media(file=io.BytesIO())
                # تأكد أن دالة is_image_blacklisted موجودة في database.py
                try:
                    if db.is_image_blacklisted(get_image_hash(photo_bytes)):
                        await event.delete()
                        return
                except: pass

        # فحص باقي الأقفال عبر القائمة الشاملة
        checks = {
            "stickers": event.sticker,
            "gifs": event.gif,
            "forward": event.fwd_from,
            "videos": (event.video or event.video_note),
            "voice": event.voice,
            "contacts": event.contact
        }
        
        for key, condition in checks.items():
            if condition and db.is_locked(gid, key):
                await event.delete()
                return

        # فحص الملفات (Documents)
        if db.is_locked(gid, "files") and event.document:
            # التأكد أنه ليس ميديا تم فحصها سابقاً
            if not any([event.voice, event.video, event.gif, event.sticker]):
                await event.delete()

    except Exception as e:
        print(f"Lock System Error: {e}")

# --- 2. أوامر التحكم الإداري ---
@client.on(events.NewMessage(chats=ALLOWED_GROUPS))
async def locks_control_handler(event):
    msg = event.raw_text
    gid = str(event.chat_id)

    if not await check_privilege(event, "مدير"):
        return

    # معالجة أوامر قفل/فتح الميزات
    for ar_name, en_key in FEATURES.items():
        if msg == f"قفل {ar_name}":
            if en_key == "welcome_status":
                db.set_setting(gid, en_key, "off")
            else:
                db.toggle_lock(gid, en_key, 1)
            await event.respond(f"🔒 تم قفل **{ar_name}** بنجاح.")
            return
        
        elif msg == f"فتح {ar_name}":
            if en_key == "welcome_status":
                db.set_setting(gid, en_key, "on")
            else:
                db.toggle_lock(gid, en_key, 0)
            await event.respond(f"🔓 تم فتح **{ar_name}** بنجاح.")
            return

    # --- 3. التحكم بالدردشة والوسائط الجماعية ---
    if msg == "قفل الدردشة":
        try:
            await client.edit_permissions(event.chat_id, send_messages=False)
            await event.respond("🚫 تم إغلاق الدردشة. (الإدارة فقط يمكنهم الكلام).")
        except: await event.respond("❌ فشل القفل، تأكد من صلاحيات البوت.")
            
    elif msg == "فتح الدردشة":
        try:
            await client.edit_permissions(event.chat_id, send_messages=True, send_media=True, send_stickers=True, send_gifs=True)
            await event.respond("✅ تم فتح الدردشة بنجاح.")
        except: await event.respond("❌ فشل الفتح.")

    elif msg == "قفل الوسائط":
        for m in ["photos", "videos", "stickers", "gifs", "voice", "files"]:
            db.toggle_lock(gid, m, 1)
        await event.respond("🔒 تم قفل **جميع الوسائط** في هذه المجموعة.")
        
    elif msg == "فتح الوسائط":
        for m in ["photos", "videos", "stickers", "gifs", "voice", "files"]:
            db.toggle_lock(gid, m, 0)
        await event.respond("🔓 تم فتح **جميع الوسائط**.")
