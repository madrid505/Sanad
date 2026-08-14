# 1. استخدام نسخة بايثون مستقرة وخفيفة
FROM python:3.10-slim

# 2. إعداد مجلد العمل داخل الحاوية
WORKDIR /app

# 3. تثبيت المكتبات اللازمة للنظام
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 4. نسخ ملف المتطلبات الحقيقي أولاً وتثبيته لضمان توفر كافة المكتبات (مثل pytz و telethon)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. إنشاء مجلد التخزين الدائم لقاعدة البيانات
RUN mkdir -p /app/data

# 6. نسخ باقي ملفات الكود
COPY . .

# 7. أمر تشغيل البوت الإمبراطوري
CMD ["python", "main.py"]
