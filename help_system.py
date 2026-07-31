import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, CommandHandler, CallbackQueryHandler, filters

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

# --- 2. معالجة رسائل التسجيل (تمت مساعدته) ---
async def track_help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.reply_to_message:
        return

    text = message.text or message.caption or ""
    if not text.startswith("تمت مساعدته"):
        return

    # استخراج التفاصيل المكتوبة بعد الكلمة
    help_details = text.replace("تمت مساعدته", "").strip()
    if not help_details:
        help_details = "مساعدة عامة"

    # المستفيد (صاحب الرسالة الأصلية التي تم الرد عليها)
    target_user = message.reply_to_message.from_user
    beneficiary_id = str(target_user.id)
    beneficiary_name = target_user.first_name or "مستخدم"

    # المُقدِّم (الشخص الذي كتب الرد)
    provider_user = message.from_user
    provider_id = str(provider_user.id)
    provider_name = provider_user.first_name or "مشرف/عضو"

    # الوقت والتاريخ الحالي
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # حفظ البيانات في قاعدة البيانات
    conn = sqlite3.connect("help_system.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO helps (beneficiary_id, beneficiary_name, provider_id, provider_name, help_details, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (beneficiary_id, beneficiary_name, provider_id, provider_name, help_details, current_time))
    conn.commit()
    conn.close()

    # الرد بتأكيد التسجيل
    await message.reply_text(
        f"✅ تم تسجيل المساعدة بنجاح.\n"
        f"👤 المستفيد: {beneficiary_name}\n"
        f"🤝 المُقدِّم: {provider_name}\n"
        f"📝 التفاصيل: {help_details}\n"
        f"⏱️ الوقت: {current_time}"
    )

# --- 3. نظام البحث بالرد بكلمة "بحث" ---
async def search_help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.reply_to_message:
        return

    text = (message.text or "").strip()
    if text != "بحث":
        return

    target_user = message.reply_to_message.from_user
    beneficiary_id = str(target_user.id)
    beneficiary_name = target_user.first_name or "مستخدم"

    conn = sqlite3.connect("help_system.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT help_details, provider_name, timestamp 
        FROM helps 
        WHERE beneficiary_id = ?
        ORDER BY id DESC
    """, (beneficiary_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await message.reply_text(f"❌ العضو {beneficiary_name} لم يتلق أي مساعدات مسجلة حتى الآن.")
        return

    total_helps = len(rows)
    response_text = f"🔍 **تقرير المساعدات للعضو: {beneficiary_name}**\n"
    response_text += f"📊 إجمالي عدد مرات المساعدة: **{total_helps}** مرات\n\n"
    response_text += "**التفاصيل:**\n"

    for idx, (details, provider, tstamp) in enumerate(rows[:10], 1): # عرض آخر 10 كبداية
        response_text += f"{idx}️⃣ {details} | المُقدِّم: {provider} | ⏱️ {tstamp}\n"

    await message.reply_text(response_text, parse_mode="Markdown")

# --- 4. أمر كشف المساعدات العام مع تقسيم صفحات (Pagination) ---
async def kashf_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    page = 1
    
    if query:
        await query.answer()
        page = int(query.data.split("_")[1])
        message = query.message
    else:
        message = update.message

    conn = sqlite3.connect("help_system.db")
    cursor = conn.cursor()
    cursor.execute("SELECT beneficiary_name, provider_name, help_details, timestamp FROM helps ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        msg = "📭 لا توجد أي مساعدات مسجلة في النظام حتى الآن."
        if query:
            await message.edit_text(msg)
        else:
            await message.reply_text(msg)
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

    # أزرار التنقل بين الصفحات
    keyboard = []
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"kashf_{page - 1}"))
    nav_buttons.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="none"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data=f"kashf_{page + 1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# --- 5. دالة التسجيل الأساسية لتصديرها للملف الرئيسي ---
def setup_help_system(application):
    # مراقبة رسائل الرد لتسجيل المساعدة أو البحث
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, track_help_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_help_handler))
    
    # أمر كشف المساعدات العام
    application.add_handler(CommandHandler("kashf", kashf_command))
    application.add_handler(CallbackQueryHandler(kashf_command, pattern="^kashf_"))
