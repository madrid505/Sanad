from telethon import events


def setup_id_extractor(client):

  @client.on(events.NewMessage(incoming=True))
  async def get_private_file_id(event):
    # التأكد من أن الرسالة في الخاص فقط
    if not event.is_private:
      return

    # التحقق مما إذا كانت الرسالة تحتوي على صورة
    if event.photo:
      try:
        # استخراج معرف الملف الفعلي المباشر المتوافق مع تليثون
        file_id = event.message.file.id
        media_signature = event.message.media

        # طباعة تفاصيل الكائن في السجل احتياطياً
        print(f"📌 [استخراج المعرف] تم استقبال صورة جديدة. File ID: {file_id}")

        # الرد في الخاص بالمعرف الجاهز للاستخدام
        await event.reply(
            "✅ **تم استلام الصورة بنجاح في الخاص!**\n\n"
            "📋 **معرف الصورة (File ID):**\n"
            f"`{file_id}`\n\n"
            "💡 *انسخ هذا المعرف وضعه مباشرة في قائمة الأسئلة لديك.*",
            parse_mode="md",
        )
      except Exception as e:
        print(f"❌ خطأ أثناء استخراج معرف الصورة: {e}")
