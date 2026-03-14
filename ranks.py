import io
from telethon import events
from database import db

# استيراد الـ hasher لحساب بصمة الصورة
try: 
    from hasher import get_image_hash
except: 
    get_image_hash = None

# استدعاء الأساسيات من الملف الرئيسي
from __main__ import client, ALLOWED_GROUPS, check_privilege 

@client.on(events.NewMessage(chats=ALLOWED_GROUPS))
async def ranks_manager_system(event):
    msg = event.raw_text
    gid = str(event.chat_id)

    # التحقق من الصلاحية (أدمن فأعلى مسموح له حظر الصور)
    if not await check_privilege(event, "ادمن"):
        return

    # --- 🛡️ ميزة حظر بصمة الصورة (Image Fingerprinting) ---
    if msg == "حظر صورة" and event.is_reply:
        reply_msg = await event.get_reply_message()
        
        if reply_msg and reply_msg.photo:
            if not get_image_hash:
                return await event.respond("❌ نظام التشفير (hasher) غير مفعل حالياً.")
                
            status_msg = await event.respond("🔍 جارِ فحص بصمة الصورة وحظرها ملكياً...")
            
            try:
                # 1. تحميل الصورة في الذاكرة
                photo_bytes = await reply_msg.download_media(file=io.BytesIO())
                # 2. توليد البصمة (الهاش)
                img_hash = get_image_hash(photo_bytes)
                
                # 3. إضافتها لجدول القائمة السوداء
                db.cursor.execute("INSERT OR IGNORE INTO image_blacklist (hash) VALUES (?)", (img_hash,))
                db.conn.commit()
                
                # 4. تنفيذ الحذف الفوري
                await reply_msg.delete()
                await status_msg.edit("🚫 **تم حظر بصمة الصورة بنجاح!**\nلن يُسمح بتداولها في الممالك المسموحة بعد الآن.")
                
            except Exception as e:
                print(f"Error in Image Hash: {e}")
                await status_msg.edit("❌ فشل النظام في معالجة بصمة هذه الصورة.")
        else:
            await event.respond("⚠️ يا ملك، يجب أن ترد على (صورة) لكي أستطيع سحب بصمتها.")
