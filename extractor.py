from telethon import events

def setup_id_extractor(client):
    @client.on(events.NewMessage(incoming=True))
    async def get_private_file_id(event):
        # التأكد حصرياً من أن الرسالة مرسلة في الخاص
        if not event.is_private:
            return

        # التحقق مما إذا كانت الرسالة تحتوي على صورة
        if event.photo:
            try:
                # جلب الـ File ID الفعلي المباشر
                file_id = event.message.file.id

                # طباعة المعرف في السجلات للتأكد
                print(f"📌 [نجاح استخراج الصورة] File ID: {file_id}")

                # إرسال الرد في الخاص فوراً
                await event.reply(
                    "✅ **تم استلام الصورة في الخاص بنجاح!**\n\n"
                    "📋 **معرف الصورة (File ID):**\n"
                    f"`{file_id}`\n\n"
                    "💡 *انسخ هذا الكود وضعه في قائمة الأسئلة لديك.*",
                    parse_mode="md",
                )
            except Exception as e:
                print(f"❌ خطأ أثناء استخراج معرف الصورة في الخاص: {e}")
