# ใช้ Python Alpine เพื่อให้ Image มีขนาดเล็กและเบา
FROM python:3.11-slim

# ตั้งค่าสิ่งแวดล้อมเพื่อไม่ให้ Python สร้างไฟล์ .pyc
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# ติดตั้ง dependencies ที่จำเป็นสำหรับระบบ
# หมายเหตุ: หากมีการใช้ไลบรารีเพิ่มเติมให้ระบุใน requirements.txt
RUN pip install --no-cache-dir fastapi uvicorn requests websocket-client

# คัดลอกโค้ดทั้งหมดเข้า Container
COPY . .

# สร้างโฟลเดอร์สำหรับเก็บฐานข้อมูล (เพื่อทำ Volume)
RUN mkdir -p /app/db

# เปิด Port ตามที่คุณตั้งไว้ใน SERVER_URL
EXPOSE 8117

# รัน Server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8117"]