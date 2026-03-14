import asyncio
from telethon import events
from database import db
from __main__ import client, ALLOWED_GROUPS, check_privilege 

# --- [ نظام المسح والتطهير ] ---
@client.on(events.NewMessage(chats=ALLOWED_GROUPS))
async def cleaner_handler(event):
    msg = event.raw_text
    chat_id = event.chat_id

    # أمر مسح الرسائل (هذا غير موجود في main.py لذا نبقيه هنا)
    if msg.startswith("مسح ") or msg == "مسح":
        # التحقق من أن المرسل أدمن فما فوق
        if not await check_privilege(event, "ادمن"): 
            return

        parts = msg.split()
        if len(parts) > 1 and parts[1].isdigit():
            num = int(parts[1])
            # حد أقصى للمسح 100 رسالة لضمان عدم تعليق البوت
            num = min(num, 100) 
            
            try:
                await event.delete() # حذف أمر المسح نفسه
                msgs = await client.get_messages(chat_id, limit=num)
                await client.delete_messages(chat_id, msgs)
                
                confirm = await event.respond(f"🗑️ **تم تطهير {len(msgs)} رسالة بنجاح.**")
                await asyncio.sleep(3)
                await confirm.delete()
            except Exception as e:
                print(f"Error in Delete: {e}")

    # يمكنك إضافة أوامر تنظيف أخرى هنا لاحقاً مثل (مسح الروابط، مسح الصور)
