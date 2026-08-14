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

# --- دالة مساعدة لجلب اسم المستخدم بشكل آمن ---
async def get_user_display_name(client, user_id):
    try:
        user = await client.get_entity(user_id)
        return f"{user.first_name or ''} {user.last_name or ''}".strip() or "مستخدم"
    except:
        return "مستخدم"

# --- الخلفية للتصفير اليومي والترحيل الساعة 11 صباحاً ---
async def daily_archive_scheduler(client, allowed_groups):
    while True:
        try:
            now = datetime.now(TIMEZONE)
            target = now.replace(hour=11, minute=0, second=0, microsecond=0)
            if now >= target:
                target += timedelta(days=1)
            
            wait_seconds = (target - now).total_seconds()
            await asyncio.sleep(wait_seconds)
            
            # تنفيذ الترحيل والتصفير اليومي
            conn = sqlite3.connect("help_system.db")
            cursor = conn.cursor()
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

            # إرسال إشعار للمجموعات المسموحة بعملية الترحيل والتصفير اليومي
            for chat_id in allowed_groups:
                try:
                    await client.send_message(chat_id, "🔄 **تم ترحيل السجل اليومي إلى الأرشيف وتصفير النظام بنجاح (الساعة 11:00 صباحاً).**")
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

    # 2. إحصائيات آخر 24 ساعة
    if text == "إحصائيات 24 ساعة":
        time_limit = (datetime.now(TIMEZONE) - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect("help_system.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT provider_name, COUNT(*) as count 
            FROM helps 
            WHERE timestamp >= ? 
            GROUP BY provider_id 
            ORDER BY count DESC
        """, (time_limit,))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            await event.reply("📊 لا توجد مساعدات مسجلة خلال الـ 24 ساعة الماضية.")
            return

        resp = "📊 **إحصائيات تقديم المساعدات خلال آخر 24 ساعة:**\n\n"
        for idx, (p_name, cnt) in enumerate(rows, 1):
            resp += f"{idx}️⃣ **{p_name}**: قدم **{cnt}** مساعدة\n"
        await event.reply(resp)
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

        resp = f"🗂️ **الأرشيف الشامل لـ ({query_val}):** (الإجمالي: {len(rows)} ملاحظة)\n\n"
        for idx, (ben, prov, details, tstamp) in enumerate(rows[:15], 1):
            resp += f"{idx}️⃣ المستفيد: **{ben}** | المُقدِّم: {prov}\n   📌 {details} | ⏱️ {tstamp}\n\n"
        await event.reply(resp)
        return

    # المعالجات التي تتطلب الرد (Reply)
    if not event.is_reply:
        return

    reply_msg = await event.get_reply_message()
    if not reply_msg or not reply_msg.sender_id:
        return

    target_user_id = str(reply_msg.sender_id)
    beneficiary_name = await get_user_display_name(client, target_user_id)

    # أ) حالة التسجيل (تمت مساعدته)
    if text.startswith("تمت مساعدته"):
        help_details = text.replace("تمت مساعدته", "").strip() or "مساعدة عامة"
        
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

        response_text = f"🔍 **تقرير المساعدات اليومي للعضو: {beneficiary_name}**\n"
        response_text += f"📊 إجمالي عدد مرات المساعدة: **{len(rows)}** مرات\n\n"
        response_text += "**التفاصيل:**\n"
        for idx, (details, provider, tstamp) in enumerate(rows[:10], 1):
            response_text += f"{idx}️⃣ {details} | المُقدِّم: {provider} | ⏱️ {tstamp}\n"

        await event.reply(response_text)

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

        response_text = f"🗂️ **الأرشيف الشامل للعضو: {beneficiary_name}**\n"
        response_text += f"━━━━━━━━━━━━━━━━━━━\n"
        response_text += f"📊 **إجمالي السجلات التاريخية:** {len(rows)} ملاحظة\n"
        response_text += f"━━━━━━━━━━━━━━━━━━━\n\n"
        
        for idx, (details, provider, tstamp) in enumerate(rows, 1):
            response_text += f"🔹 **الملاحظة رقم ({idx}):**\n"
            response_text += f"━━━━━━━━━━━━━━━━━━━\n"
            response_text += f"📝 **التفاصيل:** {details}\n"
            response_text += f"━━━━━━━━━━━━━━━━━━━\n"
            response_text += f"🤝 **المُقدِّم:** {provider}\n"
            response_text += f"━━━━━━━━━━━━━━━━━━━\n"
            response_text += f"📅 **التاريخ:** {tstamp.split()[0]}\n"
            response_text += f"━━━━━━━━━━━━━━━━━━━\n"
            response_text += f"⏱️ **الوقت:** {tstamp.split()[1]}\n"
            response_text += f"━━━━━━━━━━━━━━━━━━━\n\n"

        await event.reply(response_text)


    # د) حالة حذف ملاحظة معينة (للمشرفين فقط بالرد واختيار القائمة)
    elif text == "حذف":
        if not await is_admin(event):
            await event.reply("❌ هذا الأمر مخصص للمشرفين فقط.")
            return

        conn = sqlite3.connect("help_system.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, help_details, timestamp FROM helps WHERE beneficiary_id = ? ORDER BY id DESC", (target_user_id,))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            await event.reply(f"❌ لا توجد ملاحظات نشطة لهذا العضو لحذفها.")
            return

        buttons = []
        resp = f"🗑️ **قائمة ملاحظات العضو ({beneficiary_name}) للحذف:**\nاختر الملاحظة المراد حذفها:\n\n"
        for row_id, details, tstamp in rows[:8]:
            resp += f"🆔 `[رقم {row_id}]` - {details} ({tstamp})\n"
            buttons.append([Button.inline(f"حذف رقم {row_id}", data=f"del_{row_id}")])

        await event.reply(resp, buttons=buttons)

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
        for row_id, details, tstamp in rows[:8]:
            resp += f"🆔 `[رقم {row_id}]` - {details} ({tstamp})\n"
            buttons.append([Button.inline(f"تعديل رقم {row_id}", data=f"edit_{row_id}")])

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
        if (text.startswith("تمت مساعدته") or text == "بحث" or text == "أرشيف" or 
            text == "حذف" or text == "تعديل" or text == "تصفير" or text == "إحصائيات 24 ساعة" or 
            text.startswith("أرشيف ")):
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
            
            # معالجة حذف ملاحظة معينة
            elif data_str.startswith("del_"):
                row_id = int(data_str.split("_")[1])
                conn = sqlite3.connect("help_system.db")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM helps WHERE id = ?", (row_id,))
                conn.commit()
                conn.close()
                await event.edit(f"✅ تم حذف الملاحظة (رقم {row_id}) بنجاح.")
                await event.answer("تم الحذف")

            # معالجة تعديل ملاحظة معينة
            elif data_str.startswith("edit_"):
                row_id = int(data_str.split("_")[1])
                await event.edit(f"✍️ يرجى إرسال النص الجديد للملاحظة برقم `{row_id}` بالرد على رسالتي هذه أو إرساله مباشرة.")
                
                # التقاط التعديل الجديد من المشرف
                async with client.conversation(event.chat_id, timeout=60) as conv:
                    response = await conv.wait_event(events.NewMessage(chats=event.chat_id, from_users=event.sender_id))
                    new_details = response.raw_text.strip()
                    
                    conn = sqlite3.connect("help_system.db")
                    cursor = conn.cursor()
                    cursor.execute("UPDATE helps SET help_details = ? WHERE id = ?", (new_details, row_id))
                    conn.commit()
                    conn.close()
                    
                    await event.respond(f"✅ تم تحديث الملاحظة (رقم {row_id}) بنجاح إلى: {new_details}")
                await event.answer("تم التعديل")
        except Exception as e:
            print(f"Error in help callback: {e}")
