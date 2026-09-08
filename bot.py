import asyncio
import json
import os
from telethon import Button, events

# تحديد مسار ملف البيانات بدقة بناءً على مكان وجود الملف الحالي
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "games_data.json")


def load_games():
  if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
      return json.load(f)
  return []


# متغيرات تتبع حالة المسابقة لكل مجموعة
active_games = {}  # chat_id: {"question_index": 0, "winner_found": False}
user_scores = {}  # chat_id: {user_id: {"name": name, "score": count}}


def setup_game_handlers(client):

  @client.on(events.NewMessage(pattern=r"^غباش$"))
  async def start_game(event):
    chat_id = event.chat_id

    games = load_games()
    if not games:
      await event.reply("❌ عذراً، لا توجد أسئلة مخزنة حالياً في ملف games_data.json")
      return

    if chat_id not in active_games:
      active_games[chat_id] = {"question_index": 0, "winner_found": False}
    else:
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
    await client.send_message(chat_id, start_msg_text, parse_mode="md")

    # 2. إرسال صورة الغباش مع زر النتائج
    buttons = [[Button.inline("📊 دفتر النتائج", data="show_scoreboard".encode())]]

    sent_msg = await client.send_file(
        chat_id,
        file=q_data["spoiler_file_id"],
        buttons=buttons,
        attributes=None,
    )

    # 3. تشغيل مهمة التذكير التشجعي كل 5 ثوانٍ
    asyncio.create_task(
        encouragement_loop(client, chat_id, sent_msg.id)
    )

  async def encouragement_loop(client, chat_id, message_id):
    elapsed = 0
    while elapsed < 30:
      await asyncio.sleep(5)
      elapsed += 5

      if chat_id in active_games and active_games[chat_id]["winner_found"]:
        break

      encouraging_text = (
          f"⏳ **مضى {elapsed} ثواني على صورة الغباش ولم يتم حل اللغز!** ⏳\n\n"
          "⚡ **اين انتم يا عشاق التحدي؟! استيقظوا واكشفوا الكلمة!** ⚡"
      )
      try:
        await client.send_message(chat_id, encouraging_text, parse_mode="md")
      except Exception:
        break

  @client.on(events.NewMessage(incoming=True))
  async def handle_message(event):
    if not event.is_group:
      return

    chat_id = event.chat_id
    if chat_id not in active_games:
      return

    if active_games[chat_id]["winner_found"]:
      return

    user_text = event.raw_text.strip()
    games = load_games()
    current_idx = active_games[chat_id]["question_index"]
    q_data = games[current_idx]

    if user_text == q_data["correct_answer"]:
      active_games[chat_id]["winner_found"] = True
      user = await event.get_sender()
      if not user:
        return
      user_id = user.id
      user_name = user.first_name or "المتحدي"

      if chat_id not in user_scores:
        user_scores[chat_id] = {}
      if user_id not in user_scores[chat_id]:
        user_scores[chat_id][user_id] = {"name": user_name, "score": 0}

      user_scores[chat_id][user_id]["score"] += 1
      current_score = user_scores[chat_id][user_id]["score"]

      # إرسال صورة الجواب الصحيح بالرد على رسالة الفائز
      buttons = [
          [Button.inline("📊 دفتر النتائج", data="show_scoreboard".encode())]
      ]
      await event.reply(
          file=q_data["answer_file_id"],
          message=(
              f"🎉 **مبروووووك يا بطل** 🎉\n\n"
              f"✅ **جوابك صحيح ١٠٠٪** ✅\n\n"
              f"🎯 **استمر في التحدي**"
          ),
          parse_mode="md",
          buttons=buttons,
      )

      # التحقق من 5 انتصارات
      if current_score >= 5:
        congrats_msg = (
            f"🏆 **مبروووووك يا اسطورة الغباش [{user_name}](tg://user?id={user_id})"
            f"** 🏆\n\n🌟 **لقد حققت خمس انتصارات وتغلبت على الجميع!** 🌟"
        )
        await client.send_message(chat_id, congrats_msg, parse_mode="md")
        user_scores[chat_id][user_id]["score"] = 0

      active_games[chat_id]["question_index"] += 1

  @client.on(events.CallbackQuery)
  async def callback_handler(event):
    data = event.data.decode("utf-8")
    chat_id = event.chat_id

    if data == "show_scoreboard":
      if chat_id not in user_scores or not user_scores[chat_id]:
        await event.answer(
            "دفتر النتائج فارغ حتى الآن، كن أول الفائزين!", alert=True
        )
        return

      sorted_users = sorted(
          user_scores[chat_id].values(), key=lambda x: x["score"], reverse=True
      )

      score_text = "📊 **--- دفتر النتائج والمراتب ---** 📊\n\n"
      for idx, item in enumerate(sorted_users[:10], start=1):
        score_text += (
            f"🏅 **{idx}. {item['name']}** ⟵ **{item['score']}** انتصارات\n"
        )

      buttons = [
          [
              Button.inline("◀️ السابق", data="prev_score".encode()),
              Button.inline("التالي ▶️", data="next_score".encode()),
          ],
          [Button.inline("❌ إغلاق", data="close_score".encode())],
      ]

      await event.respond(score_text, parse_mode="md", buttons=buttons)
      await event.answer()

    elif data == "close_score":
      await event.delete()
    elif data in ["prev_score", "next_score"]:
      await event.answer("هذه الصفحة الحالية للنتائج", alert=True)
