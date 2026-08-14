import sqlite3
import asyncio
from datetime import datetime, timedelta
import pytz
from telethon import events, Button
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator

# --- التوقيت المعتمد (الساعة 11 صباحاً لتغطية الدول العربية) ---
TIMEZONE = pytz.timezone("Asia/Amman")

# --- 1. إعداد قاعدة البيانات الخاصة بالمساعدات والأرشيف ---
def init_db():
    conn = sqlite3.connect("help_system.db")
    cursor = conn.cursor()
    # الجدول النشط (اليومي)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS helps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            beneficiary_id TEXT,
            beneficiary_name TEXT,
            provider_id TEXT,
            provider_name TEXT,
            help_details TEXT,
            timestamp TEXT
        )
    """)
    # جدول الأرشيف الشامل (يحفظ البيانات حتى شهر وأكثر)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            beneficiary_id TEXT,
            beneficiary_name TEXT,
            provider_id TEXT,
            provider_name TEXT,
            help_details TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- التحقق من صلاحيات المشرف أو المالك عبر تيليجرام ---
async def is_admin(event):
    if not event.is_group:
        return False
    try:
        participant = await event.client.get_permissions(event.chat_id, event.sender_id)
        return participant.is_admin or participant.is_creator
    except:
        return False

async def is_owner(event):
    if not event.is_group:
        return False
    try:
        participant = await event.client.get_permissions(event.chat_id, event.sender_id)
        return participant.is_creator
    except:
        return False

# --- دالة مساعدة لجلب اسم المستفيد الحقيقي من رسالة الرد بشكل مضمون ---
async def get_user_display_name(reply_msg):
    try:
        sender = await reply_msg.get_sender()
        if sender:
            return f"{sender.first_name or ''} {sender.last_name or ''}".strip() or "مستخدم"
    except:
        pass
    return "مستخدم"

# --- الخلفية للتصفير اليومي والترحيل الساعة 11 صباحاً وإرسال التقارير التلقائية ---
async def daily_archive_scheduler(client, allowed_groups):
    while True:
        try:
            now = datetime.now(TIMEZONE)
            target = now.replace(hour=11, minute=0, second=0, microsecond=0)
            if now >= target:
                target += timedelta(days=1)
            
            wait_seconds = (target - now).total_seconds()
            await asyncio.sleep(wait_seconds)
            
            time_limit = (datetime.now(TIMEZONE) - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
            today_date = datetime.now(TIMEZONE).strftime("%Y-%m-%d")

            conn = sqlite3.connect("help_system.db")
            cursor = conn.cursor()
            
            # جلب أكثر مقدم مساعدات
            cursor.execute("""
                SELECT provider_name, COUNT(*) as count 
                FROM helps 
                WHERE timestamp >= ? 
                GROUP BY provider_id 
                ORDER BY count DESC LIMIT 1
            """, (time_limit,))
            top_provider = cursor.fetchone()

            # جلب أكثر مستفيد تلقى مساعدات
            cursor.execute("""
                SELECT beneficiary_name, COUNT(*) as count 
                FROM helps 
                WHERE timestamp >= ? 
                GROUP BY beneficiary_id 
                ORDER BY count DESC LIMIT 1
            """, (time_limit,))
            top_beneficiary = cursor.fetchone()

            # تنفيذ الترحيل والتصفير اليومي
            cursor.execute("SELECT beneficiary_id, beneficiary_name, provider_id, provider_name, help_details, timestamp FROM helps")
            rows = cursor.fetchall()
            if rows:
                cursor.executemany("""
                    INSERT INTO archive (beneficiary_id, beneficiary_name, provider_id, provider_name, help_details, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, rows)
                cursor.execute("DELETE FROM helps")
                conn.commit()
            
            # تنظيف أرشيف أقدم من 30 يوماً تلقائياً
            month_ago = (datetime.now(TIMEZONE) - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("DELETE FROM archive WHERE timestamp < ?", (month_ago,))
            conn.commit()
            conn.close()

            # بناء رسالة أكثر مقدم مساعدات
            prov_msg = (
                f"🏆 **أكثر عضو قام بتقديم المساعدات (آخر 24 ساعة)**\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"📅 **التاريخ:** {today_date}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"👤 **اسم العضو:** {top_provider[0] if top_provider else 'لا يوجد'}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🔢 **عدد المساعدات:** {top_provider[1] if top_provider else 0}\n"
                f"━━━━━━━━━━━━━━━━━━━"
            )

            # بناء رسالة أكثر مستفيد تلقى مساعدات
            ben_msg = (
                f"🎯 **أكثر عضو تلقى مساعدات (آخر 24 ساعة)**\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"📅 **التاريخ:** {today_date}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"👤 **اسم العضو:** {top_beneficiary[0] if top_beneficiary else 'لا يوجد'}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🔢 **عدد المساعدات المتلقاة:** {top_beneficiary[1] if top_beneficiary else 0}\n"
                f"━━━━━━━━━━━━━━━━━━━"
            )

            # إرسال إشعار للمجموعات المسموحة بعملية الترحيل والتصفير والتقارير
            for chat_id in allowed_groups:
                try:
                    await client.send_message(chat_id, "🔄 **تم ترحيل السجل اليومي إلى الأرشيف وتصفير النظام بنجاح (الساعة 11:00 صباحاً).**")
                    await client.send_message(chat_id, prov_msg)
                    await client.send_message(chat_id, ben_msg)
                except:
                    pass
        except Exception as e:
            print(f"Error in scheduler: {e}")
            await asyncio.sleep(60)

# --- معالجة رسائل المساعدات والبحث والأرشيف والإدارة ---
async def handle_help_messages(event, client):
    text = (event.raw_text or "").strip()

    # 1. أمر التصفير (خاص بالمالكين فقط)
    if text == "تصفير":
        if not await is_owner(event):
            await event.reply("❌ عذراً، هذا الأمر مخصص للمالكين فقط.")
            return
        conn = sqlite3.connect("help_system.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM helps")
        cursor.execute("DELETE FROM archive")
        conn.commit()
        conn.close()
        await event.reply("⚠️ **تم تصفير النظام والأرشيف بالكامل والبدء من الصفر بناءً على طلب المالك.**")
        return

    # 2. أمر التوب (أكثر مقدم مساعدات وأكثر مستفيد خلال آخر 24 ساعة)
    if text.lower() in ["top", "توب", "توب ون"]:
        time_limit = (datetime.now(TIMEZONE) - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
        today_date = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
        
        conn = sqlite3.connect("help_system.db")
        cursor = conn.cursor()
        
        # أكثر مقدم مساعدات
        cursor.execute("""
            SELECT provider_name, COUNT(*) as count 
            FROM helps 
            WHERE timestamp >= ? 
            GROUP BY provider_id 
            ORDER BY count DESC LIMIT 1
        """, (time_limit,))
        top_provider = cursor.fetchone()

        # أكثر مستفيد تلقى مساعدات
        cursor.execute("""
            SELECT beneficiary_name, COUNT(*) as count 
            FROM helps 
            WHERE timestamp >= ? 
            GROUP BY beneficiary_id 
            ORDER BY count DESC LIMIT 1
        """, (time_limit,))
        top_beneficiary = cursor.fetchone()
        
        conn.close()

        if not top_provider and not top_beneficiary:
            await event.reply("📊 لا توجد مساعدات مسجلة خلال الـ 24 ساعة الماضية.")
            return

        prov_msg = (
            f"🏆 **أكثر عضو قام بتقديم المساعدات (آخر 24 ساعة)**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📅 **التاريخ:** {today_date}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **اسم العضو:** {top_provider[0] if top_provider else 'لا يوجد'}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🔢 **عدد المساعدات:** {top_provider[1] if top_provider else 0}\n"
            f"━━━━━━━━━━━━━━━━━━━"
        )

        ben_msg = (
            f"🎯 **أكثر عضو تلقى مساعدات (آخر 24 ساعة)**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📅 **التاريخ:** {today_date}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **اسم العضو:** {top_beneficiary[0] if top_beneficiary else 'لا يوجد'}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🔢 **عدد المساعدات المتلقاة:** {top_beneficiary[1] if top_beneficiary else 0}\n"
            f"━━━━━━━━━━━━━━━━━━━"
        )

        await event.reply(prov_msg)
        await event.reply(ben_msg)
        return

    # 3. أمر الأرشيف (بالكتابة المباشرة: أرشيف @user أو أرشيف id)
    if text.startswith("ارشيف ") and not event.is_reply:
        query_val = text.replace("ارشيف", "").strip()
        target_id = None
        target_name = query_val

        # محاولة البحث بالمعرف أو اليوزر
        conn = sqlite3.connect("help_system.db")
        cursor = conn.cursor()
        if query_val.isdigit():
            cursor.execute("SELECT beneficiary_name, provider_name, help_details, timestamp FROM helps WHERE beneficiary_id = ? UNION ALL SELECT beneficiary_name, provider_name, help_details, timestamp FROM archive WHERE beneficiary_id = ?", (query_val, query_val))
        else:
            cursor.execute("SELECT beneficiary_name, provider_name, help_details, timestamp FROM helps WHERE beneficiary_name LIKE ? UNION ALL SELECT beneficiary_name, provider_name, help_details, timestamp FROM archive WHERE beneficiary_name LIKE ?", (f"%{query_val}%", f"%{query_val}%"))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            await event.reply(f"❌ لم يتم العثور على أي سجل أرشيف مطابق لـ: {query_val}")
            return

        items_per_page = 1
        total_pages = len(rows)
        page = 1

        start_idx = (page - 1) * items_per_page
        current_rows = rows[start_idx:start_idx + items_per_page]

        resp = f"🗂️ **الأرشيف الشامل لـ:**\n"
        resp += f"👤 **{query_val}**\n"
        resp += f"━━━━━━━━━━━━━━━━━━━\n"
        resp += f"📊 **إجمالي السجلات:**\n"
        resp += f"🔢 **{len(rows)} ملاحظة**\n"
        resp += f"━━━━━━━━━━━━━━━━━━━\n"
        resp += f"📄 **الصفحة {page} من {total_pages}**\n"
        resp += f"━━━━━━━━━━━━━━━━━━━\n\n"
        
        for idx, (ben, prov, details, tstamp) in enumerate(current_rows, start_idx + 1):
            date_part, time_part = tstamp.split()
            resp += f"🔹 **الملاحظة رقم ({idx})**\n"
            resp += f"━━━━━━━━━━━━━━━━━━━\n"
            resp += f"🎯 **المستفيد:** {ben}\n"
            resp += f"━━━━━━━━━━━━━━━━━━━\n"
            resp += f"🤝 **المُقدِّم:** {prov}\n"
            resp += f"━━━━━━━━━━━━━━━━━━━\n"
            resp += f"📝 **التفاصيل:** {details}\n"
            resp += f"━━━━━━━━━━━━━━━━━━━\n"
            resp += f"📅 **التاريخ:** **{date_part}**\n"
            resp += f"━━━━━━━━━━━━━━━━━━━\n"
            resp += f"⏱️ **الوقت:** **{time_part}**\n"
            resp += f"━━━━━━━━━━━━━━━━━━━\n\n"

        buttons = []
        nav_buttons = []
        if total_pages > 1:
            nav_buttons.append(Button.inline(f"{page}/{total_pages}", data="none"))
            nav_buttons.append(Button.inline("التالي ➡️", data=f"arc_page_{query_val}_{page + 1}"))
        
        if nav_buttons:
            buttons.append(nav_buttons)

        await event.reply(resp, buttons=buttons if buttons else None)
        return

    # المعالجات التي تتطلب الرد (Reply)
    if not event.is_reply:
        return

    reply_msg = await event.get_reply_message()
    if not reply_msg or not reply_msg.sender_id:
        return

    target_user_id = str(reply_msg.sender_id)
    beneficiary_name = await get_user_display_name(reply_msg)

    # أ) حالة التسجيل (تمت مساعدته / تم مساعدته / تم المساعده)
    if text.startswith("تمت مساعدته") or text.startswith("تم مساعدته") or text.startswith("تم المساعده"):
        if text.startswith("تمت مساعدته"):
            help_details = text.replace("تمت مساعدته", "").strip() or "مساعدة عامة"
        elif text.startswith("تم مساعدته"):
            help_details = text.replace("تم مساعدته", "").strip() or "مساعدة عامة"
        else:
            help_details = text.replace("تم المساعده", "").strip() or "مساعدة عامة"
        
        provider_user = await event.get_sender()
        if not provider_user:
            return
        provider_id = str(provider_user.id)
        provider_name = f"{provider_user.first_name or ''} {provider_user.last_name or ''}".strip() or "مشرف/عضو"

        current_time = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect("help_system.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO helps (beneficiary_id, beneficiary_name, provider_id, provider_name, help_details, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (target_user_id, beneficiary_name, provider_id, provider_name, help_details, current_time))
        conn.commit()
        conn.close()

        await event.reply(
            f"✅ **تم تسجيل المساعدة بنجاح**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **المستفيد:** {beneficiary_name}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🤝 **المُقدِّم:** {provider_name}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📝 **التفاصيل:** {help_details}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📅 **التاريخ:** {current_time.split()[0]}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"⏱️ **الوقت:** {current_time.split()[1]}"
        )

    # ب) حالة البحث السريع
    elif text == "بحث":
        conn = sqlite3.connect("help_system.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT help_details, provider_name, timestamp 
            FROM helps 
            WHERE beneficiary_id = ?
            ORDER BY id DESC
        """, (target_user_id,))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            await event.reply(f"❌ العضو {beneficiary_name} لم يتلق أي مساعدات مسجلة اليوم.")
            return

        items_per_page = 1
        total_pages = len(rows)
        page = 1

        start_idx = (page - 1) * items_per_page
        current_rows = rows[start_idx:start_idx + items_per_page]

        response_text = f"🔍 **تقرير المساعدات اليومي للعضو:**\n"
        response_text += f"👤 **{beneficiary_name}**\n"
        response_text += f"━━━━━━━━━━━━━━━━━━━\n"
        response_text += f"📊 **إجمالي عدد مرات المساعدة:**\n"
        response_text += f"🔢 **{len(rows)} مرات**\n"
        response_text += f"━━━━━━━━━━━━━━━━━━━\n"
        response_text += f"📄 **الصفحة {page} من {total_pages}**\n"
        response_text += f"━━━━━━━━━━━━━━━━━━━\n\n"
        response_text += f"📌 **التفاصيل:**\n"
        response_text += f"━━━━━━━━━━━━━━━━━━━\n"
        
        for idx, (details, provider, tstamp) in enumerate(current_rows, start_idx + 1):
            date_part, time_part = tstamp.split()
            response_text += f"🔹 **الملاحظة رقم ({idx})**\n"
            response_text += f"━━━━━━━━━━━━━━━━━━━\n"
            response_text += f"📝 **المحتوى:** {details}\n"
            response_text += f"━━━━━━━━━━━━━━━━━━━\n"
            response_text += f"🤝 **المُقدِّم:** {provider}\n"
            response_text += f"━━━━━━━━━━━━━━━━━━━\n"
            response_text += f"📅 **التاريخ:** **{date_part}**\n"
            response_text += f"━━━━━━━━━━━━━━━━━━━\n"
            response_text += f"⏱️ **الوقت:** **{time_part}**\n"
            response_text += f"━━━━━━━━━━━━━━━━━━━\n\n"

        buttons = []
        nav_buttons = []
        if total_pages > 1:
            nav_buttons.append(Button.inline(f"{page}/{total_pages}", data="none"))
            nav_buttons.append(Button.inline("التالي ➡️", data=f"srch_page_{target_user_id}_{page + 1}"))
        
        if nav_buttons:
            buttons.append(nav_buttons)

        await event.reply(response_text, buttons=buttons if buttons else None)


    # ج) حالة طلب الأرشيف بالرد (أرشيف)
    elif text == "ارشيف":
        conn = sqlite3.connect("help_system.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT help_details, provider_name, timestamp FROM helps WHERE beneficiary_id = ?
            UNION ALL
            SELECT help_details, provider_name, timestamp FROM archive WHERE beneficiary_id = ?
        """, (target_user_id, target_user_id))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            await event.reply(f"📭 العضو {beneficiary_name} ليس لديه أي سجلات سابقة في الأرشيف.")
            return

        items_per_page = 1
        total_pages = len(rows)
        page = 1

        start_idx = (page - 1) * items_per_page
        current_rows = rows[start_idx:start_idx + items_per_page]

        response_text = f"🗂️ **الأرشيف الشامل للعضو:**\n"
        response_text += f"👤 **{beneficiary_name}**\n"
        response_text += f"━━━━━━━━━━━━━━━━━━━\n"
        response_text += f"📊 **إجمالي السجلات التاريخية:**\n"
        response_text += f"🔢 **{len(rows)} ملاحظة**\n"
        response_text += f"━━━━━━━━━━━━━━━━━━━\n"
        response_text += f"📄 **الصفحة {page} من {total_pages}**\n"
        response_text += f"━━━━━━━━━━━━━━━━━━━\n\n"
        
        for idx, (details, provider, tstamp) in enumerate(current_rows, start_idx + 1):
            date_part, time_part = tstamp.split()
            response_text += f"🔹 **الملاحظة رقم ({idx}):**\n"
            response_text += f"━━━━━━━━━━━━━━━━━━━\n"
            response_text += f"📝 **التفاصيل:** {details}\n"
            response_text += f"━━━━━━━━━━━━━━━━━━━\n"
            response_text += f"🤝 **المُقدِّم:** {provider}\n"
            response_text += f"━━━━━━━━━━━━━━━━━━━\n"
            response_text += f"📅 **التاريخ:** **{date_part}**\n"
            response_text += f"━━━━━━━━━━━━━━━━━━━\n"
            response_text += f"⏱️ **الوقت:** **{time_part}**\n"
            response_text += f"━━━━━━━━━━━━━━━━━━━\n\n"

        buttons = []
        nav_buttons = []
        if total_pages > 1:
            nav_buttons.append(Button.inline(f"{page}/{total_pages}", data="none"))
            nav_buttons.append(Button.inline("التالي ➡️", data=f"arch_page_{target_user_id}_{page + 1}"))
        
        if nav_buttons:
            buttons.append(nav_buttons)

        await event.reply(response_text, buttons=buttons if buttons else None)

    # د) حالة حذف ملاحظة معينة (للمشرفين فقط بالرد واختيار القائمة)
    elif text == "مسح":
        if not await is_admin(event):
            await event.reply("❌ هذا الأمر مخصص للمشرفين فقط.")
            return

        try:
            await event.delete()
        except:
            pass

        conn = sqlite3.connect("help_system.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, help_details, timestamp FROM helps WHERE beneficiary_id = ? ORDER BY id DESC", (target_user_id,))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            await event.respond(f"❌ لا توجد ملاحظات نشطة لهذا العضو لحذفها.")
            return

        buttons = []
        resp = f"🗑️ **قائمة ملاحظات العضو ({beneficiary_name}) للحذف:**\nاختر الملاحظة المراد حذفها:\n\n"
        
        for index, (row_id, details, tstamp) in enumerate(rows[:8], start=1):
            date_part, time_part = tstamp.split()
            resp += f"🆔 **[رقم {index}]**\n"
            resp += f"━━━━━━━━━━━━━━━━━━━\n"
            resp += f"📝 **التفاصيل:** {details}\n"
            resp += f"━━━━━━━━━━━━━━━━━━━\n"
            resp += f"📅 **التاريخ:** **{date_part}**\n"
            resp += f"━━━━━━━━━━━━━━━━━━━\n"
            resp += f"⏱️ **الوقت:** **{time_part}**\n"
            resp += f"━━━━━━━━━━━━━━━━━━━\n\n"
            # تمرير الـ row_id مع الرقم التسلسلي معا في الـ data (مثال: del_15_4)
            buttons.append([Button.inline(f"حذف رقم {index}", data=f"del_{row_id}_{index}")])

        await event.respond(resp, buttons=buttons)


    # هـ) حالة تعديل ملاحظة معينة (للمشرفين فقط بالرد واختيار القائمة)
    elif text == "تعديل":
        if not await is_admin(event):
            await event.reply("❌ هذا الأمر مخصص للمشرفين فقط.")
            return

        conn = sqlite3.connect("help_system.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, help_details, timestamp FROM helps WHERE beneficiary_id = ? ORDER BY id DESC", (target_user_id,))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            await event.reply(f"❌ لا توجد ملاحظات نشطة لهذا العضو لتعديلها.")
            return

        buttons = []
        resp = f"✏️ **قائمة ملاحظات العضو ({beneficiary_name}) للتعديل:**\nاختر الملاحظة المراد تعديلها:\n\n"
        
        for index, (row_id, details, tstamp) in enumerate(rows[:8], start=1):
            date_part, time_part = tstamp.split()
            resp += f"🆔 **[رقم {index}]**\n"
            resp += f"━━━━━━━━━━━━━━━━━━━\n"
            resp += f"📝 **التفاصيل:** {details}\n"
            resp += f"━━━━━━━━━━━━━━━━━━━\n"
            resp += f"📅 **التاريخ:** **{date_part}**\n"
            resp += f"━━━━━━━━━━━━━━━━━━━\n"
            resp += f"⏱️ **الوقت:** **{time_part}**\n"
            resp += f"━━━━━━━━━━━━━━━━━━━\n\n"
            # تمرير الـ row_id مع الرقم التسلسلي معا في الـ data (مثال: edit_15_4)
            buttons.append([Button.inline(f"تعديل رقم {index}", data=f"edit_{row_id}_{index}")])

        await event.reply(resp, buttons=buttons)


# --- 4. أمر كشف المساعدات العام مع تقسيم صفحات (Pagination) ---
async def kashf_help_command(event, client, page=1, is_callback=False):
    conn = sqlite3.connect("help_system.db")
    cursor = conn.cursor()
    cursor.execute("SELECT beneficiary_name, provider_name, help_details, timestamp FROM helps ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        msg = "📭 لا توجد أي مساعدات مسجلة اليوم حتى الآن."
        if is_callback:
            await event.edit(msg)
        else:
            await event.reply(msg)
        return

    items_per_page = 5
    total_pages = (len(rows) + items_per_page - 1) // items_per_page
    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    current_rows = rows[start_idx:end_idx]

    text = f"📋 **سجل المساعدات اليومي العام (الصفحة {page} من {total_pages}):**\n\n"
    for idx, (ben, prov, details, tstamp) in enumerate(current_rows, start_idx + 1):
        text += f"{idx}. المستفيد: **{ben}** | المُقدِّم: {prov}\n   📌 {details} | ⏱️ {tstamp}\n\n"

    buttons = []
    nav_buttons = []
    if page > 1:
        nav_buttons.append(Button.inline("⬅️ السابق", data=f"kashf_{page - 1}"))
    nav_buttons.append(Button.inline(f"{page}/{total_pages}", data="none"))
    if page < total_pages:
        nav_buttons.append(Button.inline("التالي ➡️", data=f"kashf_{page + 1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)

    if is_callback:
        await event.edit(text, buttons=buttons)
    else:
        await event.reply(text, buttons=buttons)

# --- 5. دالة التسجيل الأساسية وإدارة الأزرار والمهام الخلفية ---
def setup_help_system(client, allowed_groups):
    # تشغيل مهام الأرشيف والتصفير اليومي تلقائياً في الخلفية
    client.loop.create_task(daily_archive_scheduler(client, allowed_groups))

    @client.on(events.NewMessage(chats=allowed_groups))
    async def help_messages_listener(event):
        text = (event.raw_text or "").strip()
        if (text.startswith("تمت مساعدته") or text.startswith("تم مساعدته") or text.startswith("تم المساعده") or 
            text == "بحث" or text == "ارشيف" or text.startswith("ارشيف ") or 
            text == "مسح" or text == "تعديل" or text == "تصفير" or 
            text.lower() in ["top", "توب", "توب ون"]):
            await handle_help_messages(event, client)
        elif text == "كشف المساعدات" or text == "/kashf":
            await kashf_help_command(event, client, page=1, is_callback=False)

    @client.on(events.CallbackQuery())
    async def help_callback_listener(event):
        try:
            data_str = event.data.decode()
            
            # معالجة صفحات الكشف العام
            if data_str.startswith("kashf_"):
                page = int(data_str.split("_")[1])
                await kashf_help_command(event, client, page=page, is_callback=True)
                await event.answer()

            # معالجة صفحات البحث بالرد (ملاحظة واحدة لكل صفحة)
            elif data_str.startswith("srch_page_"):
                parts = data_str.split("_")
                target_user_id = parts[2]
                page = int(parts[3])

                conn = sqlite3.connect("help_system.db")
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT help_details, provider_name, timestamp 
                    FROM helps 
                    WHERE beneficiary_id = ?
                    ORDER BY id DESC
                """, (target_user_id,))
                rows = cursor.fetchall()
                conn.close()

                items_per_page = 1
                total_pages = len(rows)
                page = max(1, min(page, total_pages))

                start_idx = (page - 1) * items_per_page
                current_rows = rows[start_idx:start_idx + items_per_page]

                try:
                    user_entity = await client.get_entity(int(target_user_id))
                    beneficiary_name = f"{user_entity.first_name or ''} {user_entity.last_name or ''}".strip() or "مستخدم"
                except:
                    beneficiary_name = "مستخدم"

                response_text = f"🔍 **تقرير المساعدات اليومي للعضو:**\n"
                response_text += f"👤 **{beneficiary_name}**\n"
                response_text += f"━━━━━━━━━━━━━━━━━━━\n"
                response_text += f"📊 **إجمالي عدد مرات المساعدة:**\n"
                response_text += f"🔢 **{len(rows)} مرات**\n"
                response_text += f"━━━━━━━━━━━━━━━━━━━\n"
                response_text += f"📄 **الصفحة {page} من {total_pages}**\n"
                response_text += f"━━━━━━━━━━━━━━━━━━━\n\n"
                response_text += f"📌 **التفاصيل:**\n"
                response_text += f"━━━━━━━━━━━━━━━━━━━\n"
                
                for idx, (details, provider, tstamp) in enumerate(current_rows, start_idx + 1):
                    date_part, time_part = tstamp.split()
                    response_text += f"🔹 **الملاحظة رقم ({idx})**\n"
                    response_text += f"━━━━━━━━━━━━━━━━━━━\n"
                    response_text += f"📝 **المحتوى:** {details}\n"
                    response_text += f"━━━━━━━━━━━━━━━━━━━\n"
                    response_text += f"🤝 **المُقدِّم:** {provider}\n"
                    response_text += f"━━━━━━━━━━━━━━━━━━━\n"
                    response_text += f"📅 **التاريخ:** **{date_part}**\n"
                    response_text += f"━━━━━━━━━━━━━━━━━━━\n"
                    response_text += f"⏱️ **الوقت:** **{time_part}**\n"
                    response_text += f"━━━━━━━━━━━━━━━━━━━\n\n"

                buttons = []
                nav_buttons = []
                if page > 1:
                    nav_buttons.append(Button.inline("⬅️ السابق", data=f"srch_page_{target_user_id}_{page - 1}"))
                nav_buttons.append(Button.inline(f"{page}/{total_pages}", data="none"))
                if page < total_pages:
                    nav_buttons.append(Button.inline("التالي ➡️", data=f"srch_page_{target_user_id}_{page + 1}"))
                if nav_buttons:
                    buttons.append(nav_buttons)

                await event.edit(response_text, buttons=buttons)
                await event.answer()

            # معالجة صفحات الأرشيف بالرد (ملاحظة واحدة لكل صفحة)
            elif data_str.startswith("arch_page_"):
                parts = data_str.split("_")
                target_user_id = parts[2]
                page = int(parts[3])

                conn = sqlite3.connect("help_system.db")
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT help_details, provider_name, timestamp FROM helps WHERE beneficiary_id = ?
                    UNION ALL
                    SELECT help_details, provider_name, timestamp FROM archive WHERE beneficiary_id = ?
                """, (target_user_id, target_user_id))
                rows = cursor.fetchall()
                conn.close()

                items_per_page = 1
                total_pages = len(rows)
                page = max(1, min(page, total_pages))

                start_idx = (page - 1) * items_per_page
                current_rows = rows[start_idx:start_idx + items_per_page]

                try:
                    user_entity = await client.get_entity(int(target_user_id))
                    beneficiary_name = f"{user_entity.first_name or ''} {user_entity.last_name or ''}".strip() or "مستخدم"
                except:
                    beneficiary_name = "مستخدم"

                response_text = f"🗂️ **الأرشيف الشامل للعضو:**\n"
                response_text += f"👤 **{beneficiary_name}**\n"
                response_text += f"━━━━━━━━━━━━━━━━━━━\n"
                response_text += f"📊 **إجمالي السجلات التاريخية:**\n"
                response_text += f"🔢 **{len(rows)} ملاحظة**\n"
                response_text += f"━━━━━━━━━━━━━━━━━━━\n"
                response_text += f"📄 **الصفحة {page} من {total_pages}**\n"
                response_text += f"━━━━━━━━━━━━━━━━━━━\n\n"
                
                for idx, (details, provider, tstamp) in enumerate(current_rows, start_idx + 1):
                    date_part, time_part = tstamp.split()
                    response_text += f"🔹 **الملاحظة رقم ({idx}):**\n"
                    response_text += f"━━━━━━━━━━━━━━━━━━━\n"
                    response_text += f"📝 **التفاصيل:** {details}\n"
                    response_text += f"━━━━━━━━━━━━━━━━━━━\n"
                    response_text += f"🤝 **المُقدِّم:** {provider}\n"
                    response_text += f"━━━━━━━━━━━━━━━━━━━\n"
                    response_text += f"📅 **التاريخ:** **{date_part}**\n"
                    response_text += f"━━━━━━━━━━━━━━━━━━━\n"
                    response_text += f"⏱️ **الوقت:** **{time_part}**\n"
                    response_text += f"━━━━━━━━━━━━━━━━━━━\n\n"

                buttons = []
                nav_buttons = []
                if page > 1:
                    nav_buttons.append(Button.inline("⬅️ السابق", data=f"arch_page_{target_user_id}_{page - 1}"))
                nav_buttons.append(Button.inline(f"{page}/{total_pages}", data="none"))
                if page < total_pages:
                    nav_buttons.append(Button.inline("التالي ➡️", data=f"arch_page_{target_user_id}_{page + 1}"))
                if nav_buttons:
                    buttons.append(nav_buttons)

                await event.edit(response_text, buttons=buttons)
                await event.answer()

            # معالجة صفحات الأرشيف المباشر (ملاحظة واحدة لكل صفحة)
            elif data_str.startswith("arc_page_"):
                parts = data_str.split("_")
                query_val = parts[2]
                page = int(parts[3])

                conn = sqlite3.connect("help_system.db")
                cursor = conn.cursor()
                if query_val.isdigit():
                    cursor.execute("SELECT beneficiary_name, provider_name, help_details, timestamp FROM helps WHERE beneficiary_id = ? UNION ALL SELECT beneficiary_name, provider_name, help_details, timestamp FROM archive WHERE beneficiary_id = ?", (query_val, query_val))
                else:
                    cursor.execute("SELECT beneficiary_name, provider_name, help_details, timestamp FROM helps WHERE beneficiary_name LIKE ? UNION ALL SELECT beneficiary_name, provider_name, help_details, timestamp FROM archive WHERE beneficiary_name LIKE ?", (f"%{query_val}%", f"%{query_val}%"))
                rows = cursor.fetchall()
                conn.close()

                items_per_page = 1
                total_pages = len(rows)
                page = max(1, min(page, total_pages))

                start_idx = (page - 1) * items_per_page
                current_rows = rows[start_idx:start_idx + items_per_page]

                resp = f"🗂️ **الأرشيف الشامل لـ:**\n"
                resp += f"👤 **{query_val}**\n"
                resp += f"━━━━━━━━━━━━━━━━━━━\n"
                resp += f"📊 **إجمالي السجلات:**\n"
                resp += f"🔢 **{len(rows)} ملاحظة**\n"
                resp += f"━━━━━━━━━━━━━━━━━━━\n"
                resp += f"📄 **الصفحة {page} من {total_pages}**\n"
                resp += f"━━━━━━━━━━━━━━━━━━━\n\n"
                
                for idx, (ben, prov, details, tstamp) in enumerate(current_rows, start_idx + 1):
                    date_part, time_part = tstamp.split()
                    resp += f"🔹 **الملاحظة رقم ({idx})**\n"
                    resp += f"━━━━━━━━━━━━━━━━━━━\n"
                    resp += f"🎯 **المستفيد:** {ben}\n"
                    resp += f"━━━━━━━━━━━━━━━━━━━\n"
                    resp += f"🤝 **المُقدِّم:** {prov}\n"
                    resp += f"━━━━━━━━━━━━━━━━━━━\n"
                    resp += f"📝 **التفاصيل:** {details}\n"
                    resp += f"━━━━━━━━━━━━━━━━━━━\n"
                    resp += f"📅 **التاريخ:** **{date_part}**\n"
                    resp += f"━━━━━━━━━━━━━━━━━━━\n"
                    resp += f"⏱️ **الوقت:** **{time_part}**\n"
                    resp += f"━━━━━━━━━━━━━━━━━━━\n\n"

                buttons = []
                nav_buttons = []
                if page > 1:
                    nav_buttons.append(Button.inline("⬅️ السابق", data=f"arc_page_{query_val}_{page - 1}"))
                nav_buttons.append(Button.inline(f"{page}/{total_pages}", data="none"))
                if page < total_pages:
                    nav_buttons.append(Button.inline("التالي ➡️", data=f"arc_page_{query_val}_{page + 1}"))
                if nav_buttons:
                    buttons.append(nav_buttons)

                await event.edit(resp, buttons=buttons)
                await event.answer()
            
            # معالجة حذف ملاحظة معينة (قراءة الـ row_id والـ index التسلسلي بدقة)
            elif data_str.startswith("del_"):
                parts = data_str.split("_")
                row_id = int(parts[1])
                display_index = parts[2] if len(parts) > 2 else row_id

                conn = sqlite3.connect("help_system.db")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM helps WHERE id = ?", (row_id,))
                conn.commit()
                conn.close()
                await event.edit(f"✅ تم حذف الملاحظة (رقم {display_index}) بنجاح.")
                await event.answer("تم الحذف")

            # معالجة تعديل ملاحظة معينة (قراءة الـ row_id والـ index التسلسلي بدقة)
            elif data_str.startswith("edit_"):
                parts = data_str.split("_")
                row_id = int(parts[1])
                display_index = parts[2] if len(parts) > 2 else row_id

                await event.edit(f"✍️ يرجى إرسال النص الجديد للملاحظة برقم `{display_index}` بالرد على رسالتي هذه أو إرساله مباشرة.")
                
                # التقاط التعديل الجديد من المشرف
                async with client.conversation(event.chat_id, timeout=60) as conv:
                    response = await conv.wait_event(events.NewMessage(chats=event.chat_id, from_users=event.sender_id))
                    new_details = response.raw_text.strip()
                    
                    conn = sqlite3.connect("help_system.db")
                    cursor = conn.cursor()
                    cursor.execute("UPDATE helps SET help_details = ? WHERE id = ?", (new_details, row_id))
                    conn.commit()
                    conn.close()
                    
                    await event.respond(f"✅ تم تحديث الملاحظة (رقم {display_index}) بنجاح إلى: {new_details}")
                await event.answer("تم التعديل")
        except Exception as e:
            print(f"Error in help callback: {e}")
