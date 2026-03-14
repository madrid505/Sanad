import re
import io
from telethon import events
from database import db

# نظام البصمة للصور (إذا كان متوفراً)
try: 
    from hasher import get_image_hash
except: 
    get_image_hash = None

# استدعاء الوظائف من الملف الرئيسي
from __main__ import client, ALLOWED_GROUPS, check_privilege 

# خريطة الميزات (عربي - إنجليزي)
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

# --- 1. معالج الحماية التلقائي (الرادار الصامت) ---
@client.on(events.NewMessage(chats=ALLOWED_GROUPS))
async def auto_protection_handler(event):
    # استثناء الإدارة والمميزين فوراً
    if await check_privilege(event, "مميز"):
        return

    gid = str(event.chat_id)
    msg = event.raw_text or "" 

    try:
        # أ. فحص الروابط والمعرفات (Regex مطور)
        if db.is_locked(gid, "links"):
            if re.search(r'(https?://\S+|t\.me/\S+|www\.\S+|\S+\.(me|xyz|info|tk|ml|ga|cf|gq|top|rocks|site|online))', msg):
                return await event.delete()

        if db.is_locked(gid, "usernames"):
            if re.search(r'@\S+', msg):
                return await event.delete()

        # ب. فحص الوسائط والملفات
        if event.photo:
            if db.is_locked(gid, "photos"):
                return await event.delete()
            
            # فحص القائمة السوداء للصور (إذا كان الهاشر مفعل)
            if get_image_hash:
                try:
                    photo_bytes = await event.download_media(file=io.BytesIO())
                    img_hash = get_image_hash(photo_bytes)
                    # فحص مباشر في قاعدة البيانات
                    db.cursor.execute("SELECT 1 FROM image_blacklist WHERE hash = ?", (img_hash,))
                    if db.cursor.fetchone():
                        return await event.delete()
                except: pass

        # ج. فحص باقي الأقفال عبر القائمة الشاملة
        checks = {
            "stickers": event.sticker,
            "gifs": event.gif,
            "forward": event.fwd_from,
            "videos": (event.video or event.video_note),
            "voice": event.voice,
            "contacts": event.contact,
            "files": event.document
        }
        
        for key, condition in checks.items():
            if condition and db.is_locked(gid, key):
                # استثناء: إذا كان الملف فيديو أو بصمة وتم فحصهم لا نحذف مرتين
                return await event.delete()

    except Exception as e:
        print(f"⚠️ خطأ في نظام الحماية: {e}")

# --- 2. أوامر التحكم اليدوي (قفل / فتح) ---
@client.on(events.NewMessage(chats=ALLOWED_GROUPS))
async def locks_control_handler(event):
    msg = event.raw_text
    gid = str(event.chat_id)

    # التحقق من أن المرسل مدير فأعلى
    if not await check_privilege(event, "مدير"):
        return

    # أوامر قفل/فتح الميزات الفردية
    for ar_name, en_key in FEATURES.items():
        if msg == f"قفل {ar_name}":
            if en_key == "welcome_status":
                db.set_setting(gid, en_key, "off")
            else:
                db.toggle_lock(gid, en_key, 1)
            return await event.respond(f"🔒 تم قفل **{ar_name}** بنجاح.")
        
        elif msg == f"فتح {ar_name}":
            if en_key == "welcome_status":
                db.set_setting(gid, en_key, "on")
            else:
                db.toggle_lock(gid, en_key, 0)
            return await event.respond(f"🔓 تم فتح **{ar_name}** بنجاح.")

    # --- 3. أوامر السيطرة الجماعية ---
    if msg == "قفل الدردشة":
        try:
            from telethon.tl.types import ChatBannedRights
            await client.edit_permissions(event.chat_id, send_messages=False)
            await event.respond("🚫 **تم إغلاق الدردشة.**\n(الآن الصمت يسود، والإدارة فقط من تتكلم).")
        except: await event.respond("❌ عذراً، تأكد من أنني أملك صلاحية (تغيير معلومات المجموعة).")
            
    elif msg == "فتح الدردشة":
        try:
            await client.edit_permissions(event.chat_id, send_messages=True, send_media=True, send_stickers=True, send_gifs=True)
            await event.respond("✅ **تم فتح الدردشة.**\nبإمكان الجميع التفاعل الآن.")
        except: await event.respond("❌ فشل فتح الدردشة.")

    elif msg == "قفل الوسائط":
        for m in ["photos", "videos", "stickers", "gifs", "voice", "files"]:
            db.toggle_lock(gid, m, 1)
        await event.respond("🔒 **تم قفل كافة الوسائط.** (المجموعة الآن للنصوص فقط).")
        
    elif msg == "فتح الوسائط":
        for m in ["photos", "videos", "stickers", "gifs", "voice", "files"]:
            db.toggle_lock(gid, m, 0)
        await event.respond("🔓 **تم فتح كافة الوسائط.**")
