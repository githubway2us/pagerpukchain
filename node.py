import hashlib, time, json, requests, threading
from fastapi import FastAPI, BackgroundTasks
import uvicorn

app = FastAPI()

# --- CONFIGURATION ---
MY_IP = "1.2.3.4"  # IP ของเครื่องเราเอง
SEEDS = ["YOUR_POWEREDGE_IP:8117"] # IP เครื่องหลักของคุณที่เป็นจุดเริ่ม
PEERS = set() # รายชื่อเพื่อนที่ออนไลน์
BLOCKCHAIN = [] # สำเนาบล็อกเชนที่เครื่องเรา
PENDING_TX = [] # ข้อความที่รอการขุด

# --- P2P LOGIC ---

def broadcast_block(block):
    """ส่งบล็อกใหม่ที่ขุดได้ให้เพื่อนทุกคนในเครือข่าย"""
    for peer in list(PEERS):
        try:
            requests.post(f"http://{peer}/receive_block", json=block, timeout=2)
        except:
            PEERS.remove(peer) # ถ้าเพื่อนออฟไลน์ ให้เอาออก

@app.post("/receive_block")
async def receive_block(block: dict):
    """เมื่อเพื่อนส่งบล็อกมาให้ เราต้องตรวจสอบก่อนยอมรับ"""
    last_block = BLOCKCHAIN[-1] if BLOCKCHAIN else None
    
    # 1. ตรวจสอบ Proof of Work (ขึ้นต้นด้วย 000 หรือไม่)
    # 2. ตรวจสอบ prev_hash ว่าต่อกันสนิทไหม
    if validate_block(block, last_block):
        BLOCKCHAIN.append(block)
        print(f"✅ New Block Accepted from Peer!")
        return {"status": "accepted"}
    return {"status": "rejected"}

def sync_peers():
    """ถามหาเพื่อนใหม่จาก Seeds ทุกๆ 1 นาที"""
    while True:
        for seed in SEEDS:
            try:
                res = requests.get(f"http://{seed}/get_peers").json()
                for p in res: PEERS.add(p)
            except: pass
        time.sleep(60)

# --- MINING LOGIC (P2P Style) ---

def mine_loop():
    """ขุดไปเรื่อยๆ โดยใช้บล็อกล่าสุดในเครื่องตัวเองเป็นตัวตั้งต้น"""
    while True:
        last_h = BLOCKCHAIN[-1]['hash'] if BLOCKCHAIN else "0"*64
        # ทำการขุดเหมือนเดิม...
        # ถ้าขุดเจอ -> สร้าง block -> BLOCKCHAIN.append(block) -> broadcast_block(block)
        time.sleep(1)

@app.get("/get_peers")
def get_peers():
    return list(PEERS)

# --- START NODE ---
if __name__ == "__main__":
    # รันระบบค้นหาเพื่อนใน Background
    threading.Thread(target=sync_peers, daemon=True).start()
    # รันระบบขุด
    threading.Thread(target=mine_loop, daemon=True).start()
    # เปิด API ให้เพจเจอร์มาเชื่อมต่อ
    uvicorn.run(app, host="0.0.0.0", port=8117)