import os
from telethon import events, Button
from database import db

# ملاحظة تقنية: استدعاء الكلاينت من الملف الرئيسي
from __main__ import client

# --- دالة التحقق المحلية لضمان السرعة ومنع التعليق ---
async def check_callback_privilege(event, required_rank):
    """التحقق من صلاحية الشخص الذي ضغط على الزر"""
    from __main__ import OWNER_ID
    if event.sender_id == OWNER_ID:
        return True
    
    current_gid = str(event.chat_id)
    user_rank = db.get_rank(current_gid, event.sender_id)
    
    ranks_order = {
        "عضو": 0, 
        "مميز": 1, 
        "ادمن": 2, 
        "مدير": 3, 
        "مالك": 4, 
        "المنشئ": 5
    }
    
    return ranks_order.get(user_rank, 0) >= ranks_order.get(required_rank, 0)

@client.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode('utf-8')
    gid = str(event.chat_id)
    u_id = event.sender_id
    
    # 1. التحقق من الرتبة (للمدراء فقط)
    if not await check_callback_privilege(event, "مدير"):
        await event.answer("⚠️ عذراً.. هذه اللوحة مخصصة للمدراء فقط!", alert=True)
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
        await event.edit("🔐 **إعدادات الحماية الفورية للمجموعة:**", buttons=btns)

    # --- منطق التبديل (Toggle Logic) ---
    elif data.startswith("tg_"):
        feature = data.replace("tg_", "")
        
        if feature == "welcome":
            curr = db.get_setting(gid, "welcome_status")
            new_status = "off" if curr == "on" else "on"
            db.set_setting(gid, "welcome_status", new_status)
            await event.answer(f"✅ تم {'تفعيل' if new_status == 'on' else 'تعطيل'} الترحيب")
            
            # تحديث واجهة الإعدادات
            w_status = "✅ مفعل" if new_status == "on" else "❌ معطل"
            await event.edit("⚙️ **الإعدادات العامة للبوت:**", buttons=[
                [Button.inline(f"نظام الترحيب: {w_status}", "tg_welcome")],
                [Button.inline("⬅️ رجوع", "show_main")]
            ])
            
        else:
            # تبديل حالة القفل (روابط، صور، الخ)
            current_l = db.is_locked(gid, feature)
            db.toggle_lock(gid, feature, 0 if current_l else 1)
            await event.answer("⚙️ تم تحديث حالة الحماية")
            
            # إعادة جلب الأزرار بالحالة الجديدة
            def get_s(f): return "🔒" if db.is_locked(gid, f) else "🔓"
            btns_updated = [
                [Button.inline(f"{get_s('links')} الروابط", "tg_links"), Button.inline(f"{get_s('usernames')} المعرفات", "tg_usernames")],
                [Button.inline(f"{get_s('photos')} الصور", "tg_photos"), Button.inline(f"{get_s('stickers')} الملصقات", "tg_stickers")],
                [Button.inline(f"{get_s('forward')} التوجيه", "tg_forward"), Button.inline(f"{get_s('videos')} الفيديوهات", "tg_videos")],
                [Button.inline("⬅️ رجوع", "show_main")]
            ]
            await event.edit("🔐 **إعدادات الحماية الفورية للمجموعة:**", buttons=btns_updated)

    # --- عرض الرتب ---
    elif data == "show_ranks":
        ranks_text = (
            "🎖️ **الهرم الإداري المعتمد في Monopoly:**\n"
            "━━━━━━━━━━━━━━\n"
            "👑 **المطور (أنس):** صلاحيات مطلقة عابرة للمجموعات.\n"
            "👑 **المالك:** التحكم الكامل في إعدادات المجموعة والمدراء.\n"
            "🎖️ **المدير:** الوصول للوحة التحكم (هذه اللوحة).\n"
            "🛡️ **الأدمن:** تنفيذ العقوبات الفورية (طرد، كتم).\n"
            "✨ **المميز:** استثناء من فلاتر الحماية التلقائية.\n"
            "━━━━━━━━━━━━━━"
        )
        await event.edit(ranks_text, buttons=[[Button.inline("⬅️ رجوع", "show_main")]])

    # --- عرض الأوامر ---
    elif data == "show_cmds":
        cmds_text = (
            "📜 **دليل الأوامر الملكية:**\n"
            "━━━━━━━━━━━━━━\n"
            "• `رتبتي` - لعرض تفاصيلك.\n"
            "• `المتفاعلين` - قائمة شرف المجموعة.\n"
            "• `كشف` - (بالرد) لمعرفة بيانات عضو.\n"
            "• `اضف رد` - لبرمجة ردود ذكية.\n"
            "• `رفع / تنزيل` - لإدارة الرتب.\n"
            "• `حظر / كتم` - لتنفيذ العقوبات.\n"
            "━━━━━━━━━━━━━━"
        )
        await event.edit(cmds_text, buttons=[[Button.inline("⬅️ رجوع", "show_main")]])

    # --- الإعدادات العامة ---
    elif data == "show_settings":
        w_status = "✅ مفعل" if db.get_setting(gid, "welcome_status") == "on" else "❌ معطل"
        await event.edit("⚙️ **الإعدادات العامة للبوت:**", buttons=[
            [Button.inline(f"نظام الترحيب: {w_status}", "tg_welcome")],
            [Button.inline("⬅️ رجوع", "show_main")]
        ])

    # --- إغلاق ---
    elif data == "close":
        await event.delete()
