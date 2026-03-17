# 1. استخدام نسخة بايثون مستقرة وخفيفة
FROM python:3.10-slim

# 2. إعداد مجلد العمل داخل الحاوية
WORKDIR /app

# 3. تثبيت المكتبات اللازمة للنظام لضمان استقرار التشفير
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 4. بناء ملف المتطلبات برمجياً لضمان تثبيت Telethon فقط وتجنب أخطاء sqlite3
RUN echo "telethon" > requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 5. إنشاء مجلد التخزين الدائم لقاعدة البيانات (الأرشيف المتراكم)
RUN mkdir -p /app/data

# 6. نسخ جميع ملفات الكود (main.py و database.py)
COPY . .

# 7. أمر تشغيل البوت الإمبراطوري
CMD ["python", "main.py"]
