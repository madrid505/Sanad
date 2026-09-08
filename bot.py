import asyncio
import json
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# تحميل بيانات الأسئلة
DATA_FILE = "games_data.json"


def load_games():
  if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
      return json.load(f)
  return []


# متغيرات تتبع حالة المسابقة لكل مجموعة
active_games = {}  # chat_id: {"question_index": 0, "winner_found": False}
user_scores = {}  # chat_id: {user_id: {"name": name, "score": count}}


async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
  chat_id = update.effective_chat.id
  text = update.message.text.strip()

  # أمر بدء اللعبة
  if text == "غباش":
    games = load_games()
    if not games:
      await update.message.reply_text("❌ عذراً، لا توجد أسئلة مخزنة حالياً.")
      return

    # تهيئة أو تقدم اللعبة
    if chat_id not in active_games:
      active_games[chat_id] = {"question_index": 0, "winner_found": False}
    else:
      # الانتقال للسؤال التالي بشكل دائري أو إيقاف عند نهايتها
      current_idx = active_games[chat_id]["question_index"]
      if current_idx >= len(games):
        active_games[chat_id]["question_index"] = 0

    q_data = games[active_games[chat_id]["question_index"]]
    active_games[chat_id]["winner_found"] = False

    # 1. رسالة البدء بالخط العريض والرموز
    start_msg_text = (
        "👑 **يا اساطير شعب مونوبولي العظيم** 👑\n\n"
        "🔥 **لقد بدأ تحدي الغباش** 🔥\n\n"
        "🧩 **كل ما هو عليك ان تضغط على الصورة ذات الغباش، وتجمع الاحرف مع بعضها لتظهر لنا الكلمة الصحيحة** 🧩"
    )
    await context.bot.send_message(
        chat_id=chat_id, text=start_msg_text, parse_mode="Markdown"
    )

    # 2. إرسال صورة الغباش مع زر دفتر النتائج
    keyboard = [[InlineKeyboardMarkup([[InlineKeyboardButton("📊 دفتر النتائج", callback_data="show_scoreboard")]])]]
    # إرسال الصورة مع الـ Spoiler
    sent_msg = await context.bot.send_photo(
        chat_id=chat_id,
        photo=q_data["spoiler_file_id"],
        has_spoiler=True,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("📊 دفتر النتائج", callback_data="show_scoreboard")]]
        ),
    )

    # 3. تشغيل مهمة التذكير التشجعي كل 5 ثوانٍ
    asyncio.create_task(
        encouragement_loop(context, chat_id, sent_msg.message_id)
    )


async def encouragement_loop(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int):
  """رسالة تشجيعية كل 5 ثوانٍ إذا لم يتم حل اللغز"""
  elapsed = 0
  while elapsed < 30:  # مدة الجولة مثلاً 30 ثانية كحد أقصى
    await asyncio.sleep(5)
    elapsed += 5

    # التحقق مما إذا تم العثور على الفائز
    if chat_id in active_games and active_games[chat_id]["winner_found"]:
      break

    encouraging_text = (
        f"⏳ **مضى {elapsed} ثواني على صورة الغباش ولم يتم حل اللغز!** ⏳\n\n"
        "⚡ **اين انتم يا عشاق التحدي؟! استيقظوا واكشفوا الكلمة!** ⚡"
    )
    try:
      await context.bot.send_message(
          chat_id=chat_id, text=encouraging_text, parse_mode="Markdown"
      )
    except Exception:
      break


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
  chat_id = update.effective_chat.id
  if chat_id not in active_games:
    return

  if active_games[chat_id]["winner_found"]:
    return

  user_text = update.message.text.strip()
  games = load_games()
  current_idx = active_games[chat_id]["question_index"]
  q_data = games[current_idx]

  # التحقق من الإجابة الصحيحة
  if user_text == q_data["correct_answer"]:
    active_games[chat_id]["winner_found"] = True
    user = update.effective_user
    user_id = user.id
    user_name = user.first_name

    # تحديث النقاط التراكمية
    if chat_id not in user_scores:
      user_scores[chat_id] = {}
    if user_id not in user_scores[chat_id]:
      user_scores[chat_id][user_id] = {"name": user_name, "score": 0}

    user_scores[chat_id][user_id]["score"] += 1
    current_score = user_scores[chat_id][user_id]["score"]

    # إرسال صورة الجواب الصحيح بالرد على تعليق الفائز
    keyboard = [[InlineKeyboardButton("📊 دفتر النتائج", callback_data="show_scoreboard")]]
    await update.message.reply_photo(
        photo=q_data["answer_file_id"],
        caption=(
            f"🎉 **مبروووووك يا بطل** 🎉\n\n"
            f"✅ **جوابك صحيح ١٠٠٪** ✅\n\n"
            f"🎯 **استمر في التحدي**"
        ),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    # التحقق من تحقيق 5 انتصارات
    if current_score >= 5:
      congrats_msg = (
          f"🏆 **مبروووووك يا اسطورة الغباش [{user_name}](tg://user?id={user_id})** 🏆\n\n"
          f"🌟 **لقد حققت خمس انتصارات وتغلبت على الجميع!** 🌟"
      )
      await context.bot.send_message(
          chat_id=chat_id, text=congrats_msg, parse_mode="Markdown"
      )
      # تصفير النقاط بعد الفوز بالبطولة أو تركها حسب رغبتك (هنا نصفرها ليبدأ تحدٍ جديد)
      user_scores[chat_id][user_id]["score"] = 0

    # التقدم للسؤال التالي تلقائياً
    active_games[chat_id]["question_index"] += 1


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()

  if query.data == "show_scoreboard":
    chat_id = update.effective_chat.id
    if chat_id not in user_scores or not user_scores[chat_id]:
      await query.message.reply_text(
          "📊 **دفتر النتائج فارغ حتى الآن، كن أول الفائزين!**",
          parse_mode="Markdown",
      )
      return

    # ترتيب الأعضاء تنازلياً حسب النقاط
    sorted_users = sorted(
        user_scores[chat_id].values(), key=lambda x: x["score"], reverse=True
    )

    score_text = "📊 **--- دفتر النتائج والمراتب ---** 📊\n\n"
    for idx, data in enumerate(sorted_users[:10], start=1):
      score_text += (
          f"🏅 **{idx}. {data['name']}** ⟵ **{data['score']}** انتصارات\n"
      )

    keyboard = [
        [
            InlineKeyboardButton("◀️ السابق", callback_data="prev_score"),
            InlineKeyboardButton("التالي ▶️", callback_data="next_score"),
        ],
        [InlineKeyboardButton("❌ إغلاق", callback_data="close_score")],
    ]

    await query.message.reply_text(
        score_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

  elif query.data == "close_score":
    await query.message.delete()
  elif query.data in ["prev_score", "next_score"]:
    await query.answer("هذه الصفحة الحالية للنتائج", show_alert=True)


def main():
  # ضع توكن البوت الخاص بك هنا
  TOKEN = "YOUR_BOT_TOKEN_HERE"

  app = ApplicationBuilder().token(TOKEN).build()

  # المعالجات
  app.add_handler(
      CommandHandler("start", start_game)
  )  # أو يستجيب للكلمة كمفتاح نصي
  app.add_handler(
      MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
  )
  app.add_handler(
      MessageHandler(filters.Regex("^غباش$"), start_game)
  )
  app.add_handler(
      CallbackQueryHandler(button_handler)
  )  # ملاحظة: استيراد CallbackQueryHandler متوفر في telegram.ext

  print("Bot is running...")
  app.run_polling()


if __name__ == "__main__":
  main()
