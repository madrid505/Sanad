import asyncio
from telethon import Button, events

# بيانات الأسئلة مضمنة مباشرة داخل الكود
GAMES_LIST = [
    {
        "id": 1,
        "spoiler_file_id": (
            "AgACAgQAAxkBAAIUQmqfoP0Xb8qLlwUdGn0raK6LrQs8AAIHEGsbgkP5UK29a4Waq8DfAQADAgADeQADPQQ"
        ),
        "answer_file_id": (
            "AgACAgQAAxkBAAIURGqfoSfWfwVmGB2eRfDRxCLPmWVFAAIJEGsbgkP5UG8UAvgM_fTcAQADAgADeQADPQQ"
        ),
        "correct_answer": "فاتن",
    },
    {
        "id": 2,
        "spoiler_file_id": (
            "AgACAgQAAxkBAAIUSGqfoUTQreR--gljeB-JFLrHKhsiAAILEGsbgkP5UE0QBvs9f88IAQADAgADeQADPQQ"
        ),
        "answer_file_id": (
            "AgACAgQAAxkBAAIURmqfoTp-Yv_YApj_AAHwR27YIVgcUQACChBrG4JD-VBL3aSbmqzK3wEAAwIAA3kAAz0E"
        ),
        "correct_answer": "فرح",
    },
    {
        "id": 3,
        "spoiler_file_id": (
            "AgACAgQAAxkBAAIUSmqfoX0w4hqjBA17m3ik0M-CD5D4AAIMEGsbgkP5UJrrvdcW5dQEAQADAgADeQADPQQ"
        ),
        "answer_file_id": (
            "AgACAgQAAxkBAAIUTGqfoZ6CzaN5SCcSoSmT6A2LpfOoAAINEGsbgkP5UAQ80OkgxiuoAQADAgADeQADPQQ"
        ),
        "correct_answer": "ميران",
    },
    {
        "id": 4,
        "spoiler_file_id": (
            "AgACAgQAAxkBAAIUUGqfob5APS-ac34IpMCd9jbo4RfVAAIPEGsbgkP5UOvSH73YxGJjAQADAgADeQADPQQ"
        ),
        "answer_file_id": (
            "AgACAgQAAxkBAAIUTmqfobRtStnvGGsEkadTJ2HkJfdoAAIOEGsbgkP5UF9yZ_ETBmgdAQADAgADeQADPQQ"
        ),
        "correct_answer": "دانيا",
    },
    {
        "id": 5,
        "spoiler_file_id": (
            "AgACAgQAAxkBAAIUUmqfofEGMbYILcxCN5m8X9mkwTWrAAIQEGsbgkP5UOM7w42EYEK8AQADAgADeQADPQQ"
        ),
        "answer_file_id": (
            "AgACAgQAAxkBAAIUVGqfog7XVgSribMf22mhuh9T8Aw6AAIREGsbgkP5UMZMhNSu9bHvAQADAgADeQADPQQ"
        ),
        "correct_answer": "بغداد",
    },
    {
        "id": 6,
        "spoiler_file_id": (
            "AgACAgQAAxkBAAIUVmqfojsXHwdFFK_XgWS74MuabBTyAAISEGsbgkP5UEa-BQABZYkR_QEAAwIAA3kAAz0E"
        ),
        "answer_file_id": (
            "AgACAgQAAxkBAAIUWGqfol-5UBxmTeiJwKSj4hWTA-7bAAITEGsbgkP5UHgSEuKdAVQdAQADAgADeQADPQQ"
        ),
        "correct_answer": "فلسطين",
    },
    {
        "id": 7,
        "spoiler_file_id": (
            "AgACAgQAAxkBAAIUWmqfonQY5mjUiNYoQqpF8agFkGB8AAIUEGsbgkP5UCn9hldBBelFAQADAgADeQADPQQ"
        ),
        "answer_file_id": (
            "AgACAgQAAxkBAAIUXGqfopLIas7jI2jVaqgDgLUPfR-dAAIVEGsbgkP5UI6MfqAwSueaAQADAgADeQADPQQ"
        ),
        "correct_answer": "غزة",
    },
    {
        "id": 8,
        "spoiler_file_id": (
            "AgACAgQAAxkBAAIUXmqfoqmdWY-ucZ3n0QFv-MtTA4KYAAIXEGsbgkP5UDBYQBTgLY8fAQADAgADeQADPQQ"
        ),
        "answer_file_id": (
            "AgACAgQAAxkBAAIUYGqfosOZyzRCeFJPrjoQCMfX6gG3AAIYEGsbgkP5UMO3OaYnFtUCAQADAgADeQADPQQ"
        ),
        "correct_answer": "نهر",
    },
    {
        "id": 9,
        "spoiler_file_id": (
            "AgACAgQAAxkBAAIUYmqfot6EBVntCkUyh5qMZkuYHA3UAAIZEGsbgkP5UNjH2OS79-iFAQADAgADeQADPQQ"
        ),
        "answer_file_id": (
            "AgACAgQAAxkBAAIUZGqfovpG8AVYmOuWUffy7plruk-ZAAIaEGsbgkP5UH5ltXCDMUCRAQADAgADeQADPQQ"
        ),
        "correct_answer": "انس",
    },
    {
        "id": 10,
        "spoiler_file_id": (
            "AgACAgQAAxkBAAIUZmqfoxzK5vaHQBNrfrlvi_DlLKV7AAIbEGsbgkP5UGrHg4J3Q5NsAQADAgADeQADPQQ"
        ),
        "answer_file_id": (
            "AgACAgQAAxkBAAIUaGqfozgKpATWY5xUnDAbNA6aJHp_AAIcEGsbgkP5UEl8SXeLZoPMAQADAgADeQADPQQ"
        ),
        "correct_answer": "حصان",
    },
    {
        "id": 11,
        "spoiler_file_id": (
            "AgACAgQAAxkBAAIUamqfo2KItMxNuejQM6zVPZtbgp91AAIdEGsbgkP5UPrgmuPE5jHFAQADAgADeQADPQQ"
        ),
        "answer_file_id": (
            "AgACAgQAAxkBAAIUbGqfo3xBJuR7pg1PI6H9Jg7XbotxAAIeEGsbgkP5UAVbqyEJrL7bAQADAgADeQADPQQ"
        ),
        "correct_answer": "كوكب",
    },
    {
        "id": 12,
        "spoiler_file_id": (
            "AgACAgQAAxkBAAIUbmqfo5fy6CKzEdXduB2jeUSNy70BAAIfEGsbgkP5UE-cUcGh1KlEAQADAgADeQADPQQ"
        ),
        "answer_file_id": (
            "AgACAgQAAxkBAAIUcGqfo7Jk4ftk049GRYeYDvHn0iYQAAIgEGsbgkP5UBxbs3cj8vYXAQADAgADeQADPQQ"
        ),
        "correct_answer": "الرياض",
    },
    {
        "id": 13,
        "spoiler_file_id": (
            "AgACAgQAAxkBAAIUdGqfo-XlT3Hy8yoZBZoHA6wc3l5HAAIiEGsbgkP5UIi2C7oioWj2AQADAgADeQADPQQ"
        ),
        "answer_file_id": (
            "AgACAgQAAxkBAAIUcmqfo97uS4lPwV6Xm42oKLlLJwF5AAIhEGsbgkP5UBCeh8i8W7sgAQADAgADeQADPQQ"
        ),
        "correct_answer": "الاردن",
    },
    {
        "id": 14,
        "spoiler_file_id": (
            "AgACAgQAAxkBAAIUdmqfpBcwfeEhEbefRrdosbMKnhNKAAIjEGsbgkP5UFPbWfOuP2ZCAQADAgADeQADPQQ"
        ),
        "answer_file_id": (
            "AgACAgQAAxkBAAIUeGqfpD8SPtBByrEdCJ4yWlG3uEhZAAIkEGsbgkP5UBVlkIKF6l-pAQADAgADeQADPQQ"
        ),
        "correct_answer": "دمشق",
    },
    {
        "id": 15,
        "spoiler_file_id": (
            "AgACAgQAAxkBAAIUemqfpFb7rvfCL4pe7DwQLwVu4IPkAAIlEGsbgkP5UPD0IUHvsMoZAQADAgADeQADPQQ"
        ),
        "answer_file_id": (
            "AgACAgQAAxkBAAIUfGqfpHCb2-ZZrVECc9jk1JUqNAABSgACJhBrG4JD-VAwN2KT3CrfjgEAAwIAA3kAAz0E"
        ),
        "correct_answer": "لبنان",
    },
    {
        "id": 16,
        "spoiler_file_id": (
            "AgACAgQAAxkBAAIUfmqfpIGEJBrXyZE_jkdR4F7i1QplAAInEGsbgkP5UI_7sbggqUW1AQADAgADeQADPQQ"
        ),
        "answer_file_id": (
            "AgACAgQAAxkBAAIUgGqfpJfl-MKBBENaXTilioJ_os-AAAIoEGsbgkP5ULaCN5A0d83GAQADAgADeQADPQQ"
        ),
        "correct_answer": "أسد",
    },
    {
        "id": 17,
        "spoiler_file_id": (
            "AgACAgQAAxkBAAIUgmqfpK62EPEGiJAFwLuB9Q4NMzquAAIpEGsbgkP5UC55XyryQ3qgAQADAgADeQADPQQ"
        ),
        "answer_file_id": (
            "AgACAgQAAxkBAAIUhGqfpMlG-4uQ4qY7JgPqysruEj9oAAIqEGsbgkP5UJvU6aoD6iFuAQADAgADeQADPQQ"
        ),
        "correct_answer": "وتين",
    },
    {
        "id": 18,
        "spoiler_file_id": (
            "AgACAgQAAxkBAAIUhmqfpNmacvcfhz1-XBuDHNdCDnGoAAIrEGsbgkP5UOGTOJQdB5PwAQADAgADeQADPQQ"
        ),
        "answer_file_id": (
            "AgACAgQAAxkBAAIUiGqfpPAsjapjyoH7eQSdMVBnCOHLAAIsEGsbgkP5UE0aM5yiB72RAQADAgADeQADPQQ"
        ),
        "correct_answer": "لؤي",
    },
    {
        "id": 19,
        "spoiler_file_id": (
            "AgACAgQAAxkBAAIUimqfpYuOSj3N66858k1v8qVBDjSoAAItEGsbgkP5UHxzTpl3YB1RAQADAgADeQADPQQ"
        ),
        "answer_file_id": (
            "AgACAgQAAxkBAAIUjGqfpY-tjELqTdqwdC9l-CocevnAAAIuEGsbgkP5UDk9SUPMqxl9AQADAgADeQADPQQ"
        ),
        "correct_answer": "هلا",
    },
]

active_games = {}
user_scores = {}


def setup_game_handlers(client):

  @client.on(events.NewMessage(pattern=r"^غباش$"))
  async def start_game(event):
    chat_id = event.chat_id

    games = GAMES_LIST
    if not games:
      await event.reply("❌ عذراً، لا توجد أسئلة مخزنة.")
      return

    if chat_id not in active_games:
      active_games[chat_id] = {"question_index": 0, "winner_found": False}
    else:
      current_idx = active_games[chat_id]["question_index"]
      if current_idx >= len(games):
        active_games[chat_id]["question_index"] = 0

    q_data = games[active_games[chat_id]["question_index"]]
    active_games[chat_id]["winner_found"] = False

    start_msg_text = (
        "👑 **يا اساطير شعب مونوبولي العظيم** 👑\n\n"
        "🔥 **لقد بدأ تحدي الغباش** 🔥\n\n"
        "🧩 **كل ما هو عليك ان تضغط على الصورة ذات الغباش، وتجمع الاحرف مع"
        " بعضها لتظهر لنا الكلمة الصحيحة** 🧩"
    )
    await client.send_message(chat_id, start_msg_text, parse_mode="md")

    buttons = [[Button.inline("📊 دفتر النتائج", data="show_scoreboard".encode())]]

    try:
      sent_msg = await client.send_file(
          chat_id,
          file=q_data["spoiler_file_id"],
          buttons=buttons,
          spoiler=True,
      )
    except Exception as e:
      # طباعة الخطأ الفعلي والكامل في السجل (Logs) لمتابعة أي مشكلة برمجية
      print(
          f"❌ [خطأ تقني في لعبة الغباش - إرسال صورة الغباش]: التفاصيل التقنية:"
          f" {e}"
      )
      await event.reply("❌ حدث خطأ أثناء إرسال الصورة.")
      return

    asyncio.create_task(encouragement_loop(client, chat_id, sent_msg.id))

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
    games = GAMES_LIST
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

      buttons = [
          [Button.inline("📊 دفتر النتائج", data="show_scoreboard".encode())]
      ]
      try:
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
      except Exception as e:
        print(
            f"❌ [خطأ تقني في لعبة الغباش - إرسال صورة الجواب]: التفاصيل التقنية:"
            f" {e}"
        )

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
