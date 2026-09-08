from telethon import events


def setup_extractor_handlers(client, owner_id):

  @client.on(events.NewMessage(incoming=True))
  async def catch_photo(event):
    # التحقق من أن الرسالة في المحادثة الخاصة وأن المرسل هو المالك
    if event.is_private and event.sender_id == owner_id:
      if event.photo:
        try:
          # استخراج الـ File ID الحقيقي من رسالة الصورة
          real_file_id = event.message.file.id
          await event.reply(
              f"<b>✅ تم اصطياد الـ File ID الحقيقي:</b>\n"
              f"<code>{real_file_id}</code>",
              parse_mode="html",
          )
        except Exception as e:
          await event.reply(f"❌ حدث خطأ أثناء استخراج المعرف: {e}")
