from telethon import events, utils


def setup_extractor_handlers(client, owner_id):

  @client.on(events.NewMessage(incoming=True))
  async def catch_photo(event):
    if event.is_private and event.sender_id == owner_id:
      if event.photo:
        try:
          # استخراج الـ file_id النصي تماماً بالشكل التقليدي المطلوب
          file_id_str = utils.pack_bot_file_id(event.media)

          await event.reply(
              f"<b>✅ تم استخراج المعرف بنجاح:</b>\n\n"
              f"<code>{file_id_str}=الجواب_هنا</code>",
              parse_mode="html",
          )
        except Exception as e:
          await event.reply(f"❌ حدث خطأ أثناء التوليد: {e}")
