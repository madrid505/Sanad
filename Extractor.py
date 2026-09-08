from telethon import events


def setup_extractor_handlers(client, owner_id):
  @client.on(events.NewMessage(incoming=True))
  async def catch_photo(event):
    # التحقق من أن الرسالة في المحادثة الخاصة وأن المرسل هو المالك
    if event.is_private and event.sender_id == owner_id:
      if event.photo:
        p_id = event.photo.id
        await event.reply(
            f"<b>✅ تم الاصطياد:</b>\n<code>{p_id}=الجواب_هنا</code>",
            parse_mode="html",
        )
