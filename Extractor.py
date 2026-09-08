from telethon import events
from telethon.tl.types import InputPhoto


def setup_extractor_handlers(client, owner_id):

  @client.on(events.NewMessage(incoming=True))
  async def catch_photo(event):
    if event.is_private and event.sender_id == owner_id:
      if event.photo:
        try:
          photo = event.message.media.photo
          code_snippet = (
              f"InputPhoto(id={photo.id}, "
              f"access_hash={photo.access_hash}, "
              f"file_reference={repr(photo.file_reference)})"
          )
          await event.reply(
              f"<b>✅ انسخ هذا السطر وضعه في اللعبة:</b>\n\n<code>{code_snippet}</code>",
              parse_mode="html",
          )
        except Exception as e:
          await event.reply(f"❌ حدث خطأ: {e}")
