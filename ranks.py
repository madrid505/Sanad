import io
from telethon import events
from database import db
# استيراد الـ hasher (تأكد من وجود ملف hasher.py في المجلد)
try: from hasher import get_image_hash
except: get_image_hash = None

from __main__ import client, ALLOWED_GROUPS, check_privilege 

@client.on(events.NewMessage(chats=ALLOWED_GROUPS))
async def ranks_manager_system(event):
    msg = event.raw_text
    gid = str(event.chat_id)

    # التحقق من الصلاحية (ادمن فأعلى)
    if not await check_privilege(event, "ادمن"):
        return

    # --- ميزة حظر بصمة الصورة ---
    if msg == "حظر صورة" and event.is_reply:
        reply_msg = await event.get_reply_message()
        if reply_msg and reply_msg.photo:
            if not get_image_hash:
                await event.respond("❌ ملف التشفير (hasher) غير موجود.")
                return
                
            try:
                # تحميل الصورة وحساب بصمتها الفريدة
                photo_bytes = await reply_msg.download_media(file=io.BytesIO())
                img_hash = get_image_hash(photo_bytes)
                
                # إضافة البصمة للقائمة السوداء في قاعدة البيانات
                # ملاحظة: تأكد أن دالة add_image_hash موجودة في database.py
                db.cursor.execute("INSERT OR IGNORE INTO image_blacklist (hash) VALUES (?)", (img_hash,))
                db.conn.commit()
                
                await reply_msg.delete()
                await event.respond("🚫 **تم حظر بصمة هذه الصورة بنجاح.**\nلن يستطيع أي عضو (غير مستثنى) إرسالها مجدداً.")
            except Exception as e:
                print(f"Error in Image Hash: {e}")
                await event.respond("❌ حدث خطأ أثناء محاولة حظر الصورة.")
        else:
            await event.respond("⚠️ يرجى الرد على الصورة التي تريد حظر بصمتها.")

# ملاحظة إمبراطورية: تم نقل بقية الأوامر الإدارية لـ main.py لضمان السرعة ومنع التكرار.
