import asyncio
from telethon import events
from database import db
from __main__ import client, ALLOWED_GROUPS, check_privilege 

# --- [ نظام المسح والتطهير الملكي ] ---
@client.on(events.NewMessage(chats=ALLOWED_GROUPS))
async def cleaner_handler(event):
    msg = event.raw_text
    chat_id = event.chat_id

    # أمر مسح الرسائل (مثال: مسح 50)
    if msg.startswith("مسح ") or msg == "مسح":
        # التحقق من الصلاحية (أدمن فأعلى)
        if not await check_privilege(event, "ادمن"): 
            return

        try:
            parts = msg.split()
            # تحديد العدد المطلوبة مسحه
            num = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10
            
            # حماية البوت: حد أدنى 1 وحد أقصى 100
            num = max(1, min(num, 100)) 
            
            # حذف أمر المسح أولاً لتنظيف الشات
            await event.delete() 
            
            # جلب الرسائل وحذفها
            messages = await client.get_messages(chat_id, limit=num)
            await client.delete_messages(chat_id, messages)
            
            # رسالة تأكيد مؤقتة
            confirm = await event.respond(f"🗑️ **تم تطهير {len(messages)} رسالة من سجلات المملكة.**")
            
            # حذف رسالة التأكيد بعد 3 ثوانٍ ليبقى الشات نظيفاً تماماً
            await asyncio.sleep(3)
            await confirm.delete()
            
        except Exception as e:
            print(f"Cleaner Error: {e}")
            # في حال حدث خطأ (مثل صلاحيات ناقصة)
            err_msg = await event.respond("❌ فشل نظام التطهير. تأكد من صلاحية (حذف الرسائل).")
            await asyncio.sleep(3)
            await err_msg.delete()

    # --- ميزة إضافية: تنظيف الحسابات المحذوفة ---
    elif msg == "تنظيف المحذوفين":
        if not await check_privilege(event, "مدير"):
            return
            
        status = await event.respond("🔍 جاري البحث عن الحسابات المحذوفة...")
        count = 0
        async for user in client.iter_participants(chat_id):
            if user.deleted:
                try:
                    await client.kick_participant(chat_id, user)
                    count += 1
                except: pass
        
        await status.edit(f"✅ تم طرد {count} من الحسابات المحذوفة بنجاح.")
