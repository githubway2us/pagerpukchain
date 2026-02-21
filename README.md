# 📟 PUK Pager Network
### much pager • very blockchain • wow

PUK Pager Network คือระบบ pager network แบบ retro-inspired ที่รวม messaging, blockchain, mining และ economy เข้าไว้ในระบบเดียว โดยใช้ FastAPI และ SQLite เป็น backend

โปรเจกต์นี้จำลอง decentralized pager ecosystem ที่ผู้ใช้สามารถ:

- สมัคร Pager ID
- ส่งข้อความแบบ real-time
- ขุดเหรียญ PUK
- โอนเหรียญ
- เล่นเกมและส่ง score
- ดู blockchain explorer

ทั้งหมดในระบบเดียว

---

# ✨ Features

## 📟 Pager System
- สมัคร Pager ID แบบสุ่ม (เช่น `01-0420`)
- Login ด้วย password ที่ hash แบบ SHA-256 + salt
- ส่งข้อความ real-time ผ่าน WebSocket
- Inbox และ message storage

## ⛓️ Blockchain System
- Blockchain แบบ custom lightweight
- เก็บ:
  - การสมัคร user
  - การ transfer
  - การ mine block
- Immutable hash chain

โครงสร้าง block:
# hash = sha256(data + prev_hash + timestamp)

---

## ⛏️ Mining System

Proof-of-Work mining:

sha256(pager_id + last_hash + nonce)

เงื่อนไข:
hash ต้องขึ้นต้นด้วย "000"

## Reward:50 PUK ต่อ block


---

## 💰 Economy System

รองรับ:

- balance
- transfer
- mining reward

ตัวอย่าง transaction:
TX:01-0001>01-0420:100PUK


---

## 💬 Real-time Messaging

ใช้ WebSocket:
/ws/{pager_id}

รองรับ:

- instant messaging
- online delivery
- offline storage

---

## 📒 Phonebook

ผู้ใช้สามารถ:

- บันทึก contact
- ตั้ง alias

ป้องกัน XSS ด้วย:
html.escape()


---

## 🏆 Leaderboard System

เก็บ score จากเกม

API:
/submit_score
/leaderboard


---

# 🧠 Tech Stack

Backend:

- FastAPI
- Uvicorn
- SQLite3
- WebSocket

Security:

- SHA-256 password hashing
- salted hash
- XSS protection

Database:

---

# 📁 Project Structure

pagerchain/
│
├── server.py
├── client.py
├── pager_network.db
├── requirements.txt
└── README.md

---

# 🚀 Installation

## 1. Clone repo
git clone https://github.com/githubway2us/pagerpukchain.git

cd pagerpukchain

---

## 2. Create venv


---

## 3. Install dependencies
pip install fastapi uvicorn
หรือ
pip install -r requirements.txt
---

## 4. Run server
python server.py
