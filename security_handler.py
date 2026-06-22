import logging
import requests
from telethon import functions, types
from datetime import datetime, timedelta

# إعدادات الخدمة (سأضع لك هيكلاً جاهزاً للربط)
SIGHTENGINE_API_USER = '780815925'
SIGHTENGINE_API_SECRET = 'GwP6ygqN3JzPve43Jsfe9HbSPRGSaFqu'

async def is_content_inappropriate(file_path):
    """فحص الصورة باستخدام Sightengine"""
    try:
        with open(file_path, 'rb') as f:
            params = {
                'models': 'nudity-2.0',
                'api_user': SIGHTENGINE_API_USER,
                'api_secret': SIGHTENGINE_API_SECRET,
            }
            files = {'media': f}
            response = requests.post('https://api.sightengine.com/1.0/check.json', files=files, data=params)
            data = response.json()
            
            # إذا كانت نسبة الإباحية تتجاوز 70%
            if data['nudity']['raw'] > 0.70:
                return True
    except Exception as e:
        logging.error(f"خطأ في الاتصال بخدمة الفحص: {e}")
    return False

async def process_security_violation(event, client, admin_group_id):
    """تنفيذ العقوبة وإبلاغ الإدارة"""
    sender = await event.get_sender()
    sender_name = f"{sender.first_name} {sender.last_name or ''}".strip()
    
    # 1. الحذف الفوري
    await event.delete()
    
    # 2. العقوبة (كتم لمدة 24 ساعة)
    try:
        await client(functions.channels.EditBannedRequest(
            channel=event.chat_id,
            participant=event.sender_id,
            banned_rights=types.ChatBannedRights(until_date=datetime.now() + timedelta(hours=24), send_messages=True)
        ))
    except: pass

    # 3. إبلاغ الإدارة
    alert_text = (
        f"🚨 **| تـم رصـد وتـحـيـيـد مـخـالـفـة**\n"
        f"━━━━━━━━━━━━━━\n"
        f"👤 **المخالف:** [{sender_name}](tg://user?id={event.sender_id})\n"
        f"🆔 `{event.sender_id}`\n"
        f"🛡️ **الإجراء:** تم الحذف + الكتم (24س).\n"
        f"⚠️ **يرجى من الإدارة مراجعة العضو واتخاذ إجراء الطرد.**\n"
        f"━━━━━━━━━━━━━━"
    )
    
    await client.send_message(admin_group_id, alert_text)
