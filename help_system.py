import sqlite3
from datetime import datetime
from telethon import events, Button

# --- 1. إعداد قاعدة البيانات الخاصة بالمساعدات ---
def init_db():
    conn = sqlite3.connect("help_system.db")
    cursor = conn.cursor()
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
    conn.commit()
    conn.close()

init_db()

# --- دالة مساعدة لجلب اسم المستخدم بشكل آمن ---
async def get_user_display_name(client, user_id):
    try:
        user = await client.get_entity(user_id)
        return f"{user.first_name or ''} {user.last_name or ''}".strip() or "مستخدم"
    except:
        return "مستخدم"

# --- 2 & 3. معالجة رسائل التسجيل (تمت مساعدته) والبحث بالرد بكلمة "بحث" ---
async def handle_help_messages(event, client):
    if not event.is_reply:
        return

    text = (event.raw_text or "").strip()
    reply_msg = await event.get_reply_message()
    if not reply_msg or not reply_msg.sender_id:
        return

    # حالة التسجيل (تمت مساعدته)
    if text.startswith("تمت مساعدته"):
        help_details = text.replace("تمت مساعدته", "").strip()
        if not help_details:
            help_details = "مساعدة عامة"

        target_user_id = reply_msg.sender_id
        beneficiary_name = await get_user_display_name(client, target_user_id)
        
        provider_user = await event.get_sender()
        provider_id = str(provider_user.id)
        provider_name = f"{provider_user.first_name or ''} {provider_user.last_name or ''}".strip() or "مشرف/عضو"

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # حفظ في قاعدة البيانات
        conn = sqlite3.connect("help_system.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO helps (beneficiary_id, beneficiary_name, provider_id, provider_name, help_details, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (str(target_user_id), beneficiary_name, provider_id, provider_name, help_details, current_time))
        conn.commit()
        conn.close()

        await event.reply(
            f"✅ تم تسجيل المساعدة بنجاح.\n"
            f"👤 المستفيد: {beneficiary_name}\n"
            f"🤝 المُقدِّم: {provider_name}\n"
            f"📝 التفاصيل: {help_details}\n"
            f"⏱️ الوقت: {current_time}"
        )

    # حالة البحث بالرد بكلمة "بحث"
    elif text == "بحث":
        target_user_id = reply_msg.sender_id
        beneficiary_name = await get_user_display_name(client, target_user_id)

        conn = sqlite3.connect("help_system.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT help_details, provider_name, timestamp 
            FROM helps 
            WHERE beneficiary_id = ?
            ORDER BY id DESC
        """, (str(target_user_id),))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            await event.reply(f"❌ العضو {beneficiary_name} لم يتلق أي مساعدات مسجلة حتى الآن.")
            return

        total_helps = len(rows)
        response_text = f"🔍 **تقرير المساعدات للعضو: {beneficiary_name}**\n"
        response_text += f"📊 إجمالي عدد مرات المساعدة: **{total_helps}** مرات\n\n"
        response_text += "**التفاصيل:**\n"

        for idx, (details, provider, tstamp) in enumerate(rows[:10], 1):
            response_text += f"{idx}️⃣ {details} | المُقدِّم: {provider} | ⏱️ {tstamp}\n"

        await event.reply(response_text)

# --- 4. أمر كشف المساعدات العام مع تقسيم صفحات (Pagination) ---
async def kashf_help_command(event, client, page=1):
    conn = sqlite3.connect("help_system.db")
    cursor = conn.cursor()
    cursor.execute("SELECT beneficiary_name, provider_name, help_details, timestamp FROM helps ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        msg = "📭 لا توجد أي مساعدات مسجلة في النظام حتى الآن."
        if event.is_callback:
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

    text = f"📋 **سجل المساعدات العام (الصفحة {page} من {total_pages}):**\n\n"
    for idx, (ben, prov, details, tstamp) in enumerate(current_rows, start_idx + 1):
        text += f"{idx}. المستفيد: **{ben}** | المُقدِّم: {prov}\n   📌 {details} | ⏱️ {tstamp}\n\n"

    # أزرار التنقل (Telethon Buttons)
    buttons = []
    nav_buttons = []
    if page > 1:
        nav_buttons.append(Button.inline("⬅️ السابق", data=f"kashf_{page - 1}"))
    nav_buttons.append(Button.inline(f"{page}/{total_pages}", data="none"))
    if page < total_pages:
        nav_buttons.append(Button.inline("التالي ➡️", data=f"kashf_{page + 1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)

    if event.is_callback:
        await event.edit(text, buttons=buttons)
    else:
        await event.reply(text, buttons=buttons)

# --- 5. دالة التسجيل الأساسية لربطها بالعميل الرئيسي ---
def setup_help_system(client, allowed_groups):
    @client.on(events.NewMessage(chats=allowed_groups))
    async def help_messages_listener(event):
        text = event.raw_text or ""
        if text.startswith("تمت مساعدته") or text == "بحث":
            await handle_help_messages(event, client)
        elif text == "كشف المساعدات" or text == "/kashf":
            await kashf_help_command(event, client, page=1)

    @client.on(events.CallbackQuery(pattern=b"^kashf_"))
    async def help_callback_listener(event):
        try:
            page = int(event.data.decode().split("_")[1])
            await kashf_help_command(event, client, page=page)
            await event.answer()
        except:
            pass
