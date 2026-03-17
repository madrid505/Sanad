# 1. استخدام نسخة بايثون مستقرة وخفيفة
FROM python:3.10-slim

# 2. إعداد مجلد العمل داخل الحاوية
WORKDIR /app

# 3. تثبيت المكتبات اللازمة للنظام (لتجنب مشاكل التشفير)
RUN apt-get update && apt-get install -id --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 4. نسخ ملف المتطلبات أولاً (للاستفادة من الكاش)
# ملاحظة: تأكد من وجود ملف اسمه requirements.txt بجانب هذا الملف
RUN echo "telethon\nsqlite3" > requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 5. إنشاء مجلد التخزين الدائم لبيانات الرادار (Database Folder)
# هذا المجلد هو الذي سيتم ربطه بـ Volume في Northflank
RUN mkdir -p /app/data

# 6. نسخ جميع ملفات الكود (main.py و database.py) إلى الحاوية
COPY . .

# 7. الأمر التشغيلي لتشغيل البوت
CMD ["python", "main.py"]
