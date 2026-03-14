import os
from telethon import events, Button
from database import db

# استدعاء الكلاينت والبيانات الأساسية
try:
    from __main__ import client, OWNER_ID
except ImportError:
    # حماية في حال فشل الاستيراد أثناء الاختبار
    OWNER_ID = 5010882230 

async def check_callback_privilege(event, required_rank):
    """التحقق السريع من الصلاحية الملكية للضغط على الأزرار"""
    if event.sender_id == OWNER_ID:
        return True
    
    current_gid = str(event.chat_id)
    user_rank = db.get_rank(current_gid, event.sender_id)
    
    ranks_order = {
        "عضو": 0, "مميز": 1, "ادمن": 2, "مدير": 3, "مالك": 4, "المنشئ": 5
    }
    return ranks_order.get(user_rank, 0) >= ranks_order.get(required_rank, 0)

@client.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode('utf-8')
    gid = str(event.chat_id)
    u_id = event.sender_id
    
    # التحقق من أن الضاغط مدير فأعلى
    if not await check_callback_privilege(event, "مدير"):
        await event.answer("⚠️ عذراً يا " + (await event.get_sender()).first_name + ".. هذه اللوحة لعلية القوم فقط! 👑", alert=True)
        return

    # --- القائمة الرئيسية ---
    if data == "show_main":
        btns = [
            [Button.inline("🛡️ نظام الحماية", "show_locks"), Button.inline("🎖️ سجل الرتب", "show_ranks")],
            [Button.inline("📜 دليل الأوامر", "show_cmds"), Button.inline("⚙️ الضبط العام", "show_settings")],
            [Button.inline("❌ إغلاق اللوحة", "close")]
        ]
        await event.edit("👑 **لوحة تحكم Monopoly الملكية** 👑\n\nمرحباً بك يا مدير، اختر القسم المراد التحكم به:", buttons=btns)

    # --- نظام الأقفال ---
    elif data == "show_locks":
        def get_s(feat): return "🔒" if db.is_locked(gid, feat) else "🔓"
        btns = [
            [Button.inline(f"{get_s('links')} الروابط", "tg_links"), Button.inline(f"{get_s('usernames')} المعرفات", "tg_usernames")],
            [Button.inline(f"{get_s('photos')} الصور", "tg_photos"), Button.inline(f"{get_s('stickers')} الملصقات", "tg_stickers")],
            [Button.inline(f"{get_s('forward')} التوجيه", "tg_forward"), Button.inline(f"{get_s('videos')} الفيديوهات", "tg_videos")],
            [Button.inline("⬅️ رجوع", "show_main")]
        ]
        await event.edit("🔐 **إعدادات الحماية الفورية للمجموعة:**\nاستخدم الأزرار لفتح أو قفل الميزات.", buttons=btns)

    # --- منطق التبديل الشامل (Toggle) ---
    elif data.startswith("tg_"):
        feature = data.replace("tg_", "")
        
        if feature == "welcome":
            curr = db.get_setting(gid, "welcome_status")
            new_status = "off" if curr == "on" else "on"
            db.set_setting(gid, "welcome_status", new_status)
            await event.answer(f"✨ نظام الترحيب: {'✅ تفعيل' if new_status == 'on' else '❌ تعطيل'}", alert=False)
            # إعادة عرض قائمة الإعدادات للتحديث
            await callback_handler(event_with_data(event, "show_settings"))
            
        else:
            current_l = db.is_locked(gid, feature)
            db.toggle_lock(gid, feature, 0 if current_l else 1)
            await event.answer("⚙️ تم تحديث أرشيف الحماية الملكي")
            # إعادة عرض قائمة الأقفال للتحديث
            await callback_handler(event_with_data(event, "show_locks"))

    # --- عرض الرتب والأوامر (نصوص فقط مع زر رجوع) ---
    elif data == "show_ranks":
        ranks_text = (
            "🎖️ **الهرم الإداري المعتمد في Monopoly:**\n"
            "━━━━━━━━━━━━━━\n"
            "👑 **المطور أنس:** صاحب السيادة المطلقة.\n"
            "👑 **المالك:** حاكم المجموعة الفعلي.\n"
            "🎖️ **المدير:** المشرف على هذه اللوحة.\n"
            "🛡️ **الأدمن:** منفذ العقوبات (حظر/كتم).\n"
            "✨ **المميز:** عضو محمي من الفلاتر.\n"
            "━━━━━━━━━━━━━━"
        )
        await event.edit(ranks_text, buttons=[[Button.inline("⬅️ رجوع", "show_main")]])

    elif data == "show_cmds":
        cmds_text = (
            "📜 **دليل الأوامر الإمبراطورية:**\n"
            "━━━━━━━━━━━━━━\n"
            "• `رتبتي` - تفاصيل رتبتك وتفاعلك.\n"
            "• `المتفاعلين` - قائمة شرف الأسبوع.\n"
            "• `كشف` - (بالرد) استجواب بيانات عضو.\n"
            "• `اضف رد` - برمجة عقل البوت الآلي.\n"
            "• `حظر / كتم` - فرض النظام بالقوة.\n"
            "━━━━━━━━━━━━━━"
        )
        await event.edit(cmds_text, buttons=[[Button.inline("⬅️ رجوع", "show_main")]])

    elif data == "show_settings":
        w_status = "✅ مفعل" if db.get_setting(gid, "welcome_status") == "on" else "❌ معطل"
        await event.edit("⚙️ **الإعدادات العامة للبوت:**\nتحكم في سلوك البوت العام هنا:", buttons=[
            [Button.inline(f"نظام الترحيب: {w_status}", "tg_welcome")],
            [Button.inline("⬅️ رجوع", "show_main")]
        ])

    elif data == "close":
        await event.delete()

# دالة مساعدة لتسهيل الانتقال بين القوائم داخلياً
def event_with_data(event, new_data):
    event.data = new_data.encode('utf-8')
    return event
