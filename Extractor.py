from telethon import events


def setup_extractor_handlers(client, owner_id):

  @client.on(events.NewMessage(incoming=True))
  async def catch_photo(event):
    if event.is_private and event.sender_id == owner_id:
      if event.photo:
        try:
          # تنزيل الملف مؤقتاً للحصول على الكائن الحقيقي
          path = await event.download_media()

          # طباعة النجاح في سجل السيرفر
          print(f"--- [Extractor] Successfully caught & downloaded: {path}")

          await event.reply(
              f"<b>✅ تم حفظ الصورة بنجاح!</b>\n"
              f"📁 مسارها على السيرفر:\n<code>{path}</code>\n\n"
              f"يمكنك إرسالها في اللعبة هكذا:\n"
              f"<code>await client.send_file(chat_id, '{path}')</code>",
              parse_mode="html",
          )
        except Exception as e:
          # طباعة تفاصيل المشكلة والخطأ في سجل السيرفر بدقة
          print(f"--- [Extractor Error] Failed to process photo: {str(e)}")

          await event.reply(f"❌ حدث خطأ: {e}")
