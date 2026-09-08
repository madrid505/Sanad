from telethon import events


def setup_extractor_handlers(client, owner_id):

  @client.on(events.NewMessage(incoming=True))
  async def catch_photo(event):
    if event.is_private and event.sender_id == owner_id:
      if event.photo:
        try:
          photo_id = event.message.media.photo.id
          await event.reply(
              f"<b>✅ تم اصطياد المعرف بنجاح:</b>\n<code>{photo_id}</code>",
              parse_mode="html",
          )
        except Exception as e:
          await event.reply(f"❌ حدث خطأ أثناء استخراج المعرف: {e}")
