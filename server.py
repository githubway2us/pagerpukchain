import sqlite3, hashlib, time, json, re
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Form, Request
from fastapi.responses import HTMLResponse

app = FastAPI()
DB_NAME = "pager_network.db"
ADMIN_ID = "01-0001"
REWARD_PER_BLOCK = 50

# --- 1. ระบบจัดการฐานข้อมูล (Database) ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # ตารางผู้ใช้งาน
    c.execute('CREATE TABLE IF NOT EXISTS users (pager_id TEXT PRIMARY KEY, password TEXT, balance INTEGER)')
    # ตารางข้อความ (เพิ่มคอลัมน์ ID เพื่อการลบที่แม่นยำ)
    c.execute('CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, to_id TEXT, from_id TEXT, body TEXT, timestamp REAL)')
    # ตารางบล็อกเชน
    c.execute('CREATE TABLE IF NOT EXISTS blockchain (idx INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL, data TEXT, prev_hash TEXT, hash TEXT)')
    # ตารางคะแนนเกมงู
    c.execute('CREATE TABLE IF NOT EXISTS leaderboard (pager_id TEXT, score INTEGER, timestamp REAL)')
    # ตารางสมุดหมายเลข (Phonebook)
    c.execute('CREATE TABLE IF NOT EXISTS phonebook (owner_id TEXT, contact_id TEXT, alias TEXT, PRIMARY KEY(owner_id, contact_id))')
    
    # บัญชี Admin
    c.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?)", (ADMIN_ID, "admin123", 1000000))
    conn.commit()
    conn.close()

init_db()
import random

def generate_unique_id():
    conn = sqlite3.connect(DB_NAME)
    while True:
        # สุ่มเลข 4 หลัก เช่น 0001 ถึง 9999
        random_num = random.randint(1, 9999)
        new_id = f"01-{random_num:04d}" # ฟอร์แมตให้เป็น 01-XXXX
        
        # ตรวจสอบว่ามี ID นี้ในระบบหรือยัง
        exists = conn.execute("SELECT 1 FROM users WHERE pager_id = ?", (new_id,)).fetchone()
        if not exists:
            conn.close()
            return new_id
# --- 2. Blockchain Logic ---
def write_to_blockchain(data_string, custom_hash=None, prev_h=None):
    conn = sqlite3.connect(DB_NAME)
    if not prev_h:
        last = conn.execute("SELECT hash FROM blockchain ORDER BY idx DESC LIMIT 1").fetchone()
        prev_h = last[0] if last else "0" * 64
    ts = time.time()
    if not custom_hash:
        block_content = f"{data_string}{prev_h}{ts}"
        custom_hash = hashlib.sha256(block_content.encode()).hexdigest()
    conn.execute("INSERT INTO blockchain (timestamp, data, prev_hash, hash) VALUES (?,?,?,?)", (ts, data_string, prev_h, custom_hash))
    conn.commit()
    conn.close()

# --- 3. WEB UI (Explorer) ---
@app.get("/", response_class=HTMLResponse)
async def web_interface():
    conn = sqlite3.connect(DB_NAME)
    
    # ดึงข้อมูลเหมือนเดิม
    blocks = conn.execute(
        "SELECT idx, timestamp, data, hash FROM blockchain ORDER BY idx DESC LIMIT 15"
    ).fetchall()
    
    mining_blocks = conn.execute(
        "SELECT COUNT(*) FROM blockchain WHERE data LIKE 'MINED:%'"
    ).fetchone()[0]
    
    total_mined_coins = mining_blocks * 50
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    
    rich_list = conn.execute(
        "SELECT pager_id, balance FROM users ORDER BY balance DESC LIMIT 5"
    ).fetchall()
    
    conn.close()

    block_rows = ""
    for b in blocks:
        is_mine = "color: #c2a633; font-weight: bold; background: rgba(194,166,51,0.15);" if "MINED:" in b[2] else ""
        block_rows += f"""
        <tr style="{is_mine}">
            <td>{b[0]}</td>
            <td>{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(b[1]))}</td>
            <td>{b[2][:80]}{'...' if len(b[2]) > 80 else ''}</td>
            <td><code>{b[3][:16]}...</code></td>
        </tr>
        """

    rich_rows = "".join([
        f"<li><strong>{r[0]}</strong> — <span style='color:#c2a633;'>{r[1]:,} PUK</span></li>"
        for r in rich_list
    ]) or "<li>very empty... wow</li>"

    return f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PUK Pager Network - much explore wow</title>
        <link href="https://fonts.googleapis.com/css2?family=Comic+Neue:wght@400;700&family=Roboto:wght@400;700&display=swap" rel="stylesheet">
        <style>
            body {{
                margin: 0;
                font-family: 'Comic Neue', 'Comic Sans MS', cursive, sans-serif;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                color: #ffffff;
                min-height: 100vh;
                position: relative;
                overflow-x: hidden;
            }}

            body::before {{
                content: "";
                position: fixed;
                inset: 0;
                background: url('https://dogecoin.com/imgs/doge.png') center/cover no-repeat;
                opacity: 0.08;
                z-index: -2;
                pointer-events: none;
            }}

            .container {{
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }}

            header {{
                text-align: center;
                padding: 60px 20px 40px;
                background: rgba(0,0,0,0.5);
                border-bottom: 4px solid #c2a633;
            }}

            .logo {{
                width: 180px;
                height: auto;
                margin-bottom: 20px;
                filter: drop-shadow(0 0 20px #c2a633);
                animation: bounce 3s infinite;
            }}

            @keyframes bounce {{
                0%, 100% {{ transform: translateY(0); }}
                50% {{ transform: translateY(-15px); }}
            }}

            h1 {{
                font-size: 4rem;
                margin: 0;
                color: #c2a633;
                text-shadow: 0 0 30px #c2a63388;
                letter-spacing: 4px;
            }}

            h1 span {{
                color: #ffffff;
            }}

            .subtitle {{
                font-size: 1.8rem;
                margin: 10px 0 30px;
                color: #e0e0e0;
            }}

            .stats {{
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
                gap: 30px;
                margin: 40px 0;
            }}

            .stat-card {{
                background: rgba(194,166,51,0.15);
                border: 2px solid #c2a633;
                border-radius: 16px;
                padding: 25px 35px;
                min-width: 220px;
                text-align: center;
                box-shadow: 0 8px 25px rgba(194,166,51,0.3);
                transition: transform 0.3s;
            }}

            .stat-card:hover {{
                transform: translateY(-10px);
            }}

            .stat-value {{
                font-size: 2.8rem;
                font-weight: bold;
                color: #c2a633;
            }}

            .stat-label {{
                font-size: 1.1rem;
                color: #ddd;
            }}

            .tabs {{
                display: flex;
                justify-content: center;
                flex-wrap: wrap;
                gap: 12px;
                margin: 40px 0 20px;
            }}

            .tab {{
                padding: 14px 28px;
                background: rgba(255,255,255,0.08);
                border: 2px solid #c2a633;
                border-radius: 50px;
                color: #c2a633;
                font-weight: bold;
                cursor: pointer;
                transition: all 0.3s;
            }}

            .tab:hover, .tab.active {{
                background: #c2a633;
                color: #1a1a2e;
                transform: scale(1.08);
            }}

            .tab-content {{
                display: none;
                background: rgba(0,0,0,0.6);
                border-radius: 16px;
                padding: 30px;
                border: 1px solid #c2a63344;
            }}

            .tab-content.show {{
                display: block;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}

            th, td {{
                padding: 14px;
                text-align: left;
                border-bottom: 1px solid #444;
            }}

            th {{
                background: #c2a63322;
                color: #c2a633;
            }}

            tr:hover {{
                background: rgba(194,166,51,0.1);
            }}

            .register-form {{
                max-width: 500px;
                margin: 0 auto;
                background: rgba(194,166,51,0.1);
                padding: 30px;
                border-radius: 16px;
                border: 2px solid #c2a633;
            }}

            input, button {{
                width: 100%;
                padding: 14px;
                margin: 10px 0;
                border-radius: 8px;
                font-size: 1.1rem;
                border: 2px solid #c2a633;
                background: #1a1a2e;
                color: white;
            }}

            button {{
                background: #c2a633;
                color: #1a1a2e;
                font-weight: bold;
                cursor: pointer;
                border: none;
            }}

            button:hover {{
                background: #d4b760;
            }}

            .wow-text {{
                text-align: center;
                font-size: 1.6rem;
                color: #c2a633;
                margin: 40px 0;
                font-style: italic;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <img src="https://pngimg.com/d/pager_PNG23.png" alt="puk" class="logo">
                <h1>PUK <span>PAGER</span> NETWORK</h1>
                <div class="subtitle">much pager • very blockchain • wow</div>
            </header>

            <div class="stats">
                <div class="stat-card">
                    <div class="stat-value">{total_mined_coins:,}</div>
                    <div class="stat-label">TOTAL PUK SUPPLY</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{mining_blocks:,}</div>
                    <div class="stat-label">MINED BLOCKS</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{total_users:,}</div>
                    <div class="stat-label">REGISTERED PAGERS</div>
                </div>
            </div>

            <div class="tabs">
                <div class="tab active" onclick="openTab('explorer')">EXPLORER</div>
                <div class="tab" onclick="openTab('register')">REGISTER</div>
                <div class="tab" onclick="openTab('howtouse')">HOW TO USE</div>
                <div class="tab" onclick="openTab('blockchain')">WHAT IS THIS?</div>
            </div>

            <div id="explorer" class="tab-content show">
                <h2>Recent Blocks – very recent wow</h2>
                <table>
                    <tr>
                        <th>BLOCK</th>
                        <th>TIME</th>
                        <th>DATA</th>
                        <th>HASH</th>
                    </tr>
                    {block_rows}
                </table>

                <h2 style="margin-top:40px;">Rich Shibes</h2>
                <ul style="list-style:none; padding:0; font-size:1.2rem;">
                    {rich_rows}
                </ul>
            </div>

            <div id="register" class="tab-content">
                <h2>much register • join now wow</h2>
                <form action="/register" method="post" class="register-form">
                    <p style="text-align:center; color:#c2a633;">System will generate a unique Pager ID for you!</p>
                    <input type="password" name="password" placeholder="set password (min 6 chars)" minlength="6" required>
                    <button type="submit">GENERATE MY PAGER →</button>
                </form>
                <p style="text-align:center; margin-top:20px; color:#aaa;">100 PUK starting balance • very generous</p>
            </div>

            <div id="howtouse" class="tab-content">
                <h2>How to Use – very easy</h2>
                <div style="background:rgba(194,166,51,0.1); padding:25px; border-radius:12px; border:1px solid #c2a633;">
                    <p><strong>1. Login</strong> → open client • enter ID + pass</p>
                    <p><strong>2. Send message</strong> → menu 1 • to ID + text</p>
                    <p><strong>3. Mine PUK</strong> → menu 3 • much compute wow</p>
                    <p><strong>4. Play game</strong> → snake / tetris • fun & score</p>
                </div>
            </div>

            <div id="blockchain" class="tab-content">
                <h2>What is this? – very blockchain</h2>
                <div style="background:rgba(194,166,51,0.1); padding:25px; border-radius:12px; border:1px solid #c2a633;">
                    <p>Decentralized • immutable • proof-of-work mining</p>
                    <p>much secure • very pager • wow crypto</p>
                </div>
            </div>

            <div class="wow-text">such pager • very network • wow</div>
        </div>

        <script>
            function openTab(tabId) {{
                document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('show'));
                document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
                document.getElementById(tabId).classList.add('show');
                event.currentTarget.classList.add('active');
            }}
        </script>
    </body>
    </html>
    """
# --- 4. API ENDPOINTS ---

# สมัครสมาชิก
from fastapi.responses import HTMLResponse

@app.post("/register")
async def register(password: str = Form(...)): # รับแค่ password
    try:
        # 1. เจนเบอร์อัตโนมัติ
        pager_id = generate_unique_id()
        
        conn = sqlite3.connect(DB_NAME)
        conn.execute("INSERT INTO users VALUES (?, ?, ?)", (pager_id, password, 100))
        conn.commit()
        conn.close()
        
        write_to_blockchain(f"NEW_USER:{pager_id}")
        
        # HTML หน้าสำเร็จ + alert + redirect อัตโนมัติ
        success_page = f"""
        <!DOCTYPE html>
        <html lang="th">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>สมัครสำเร็จ - PUK Pager Network</title>
            <style>
                body {{
                    font-family: 'Courier New', Courier, monospace;
                    background: #0a0a0a;
                    color: #00ff9d;
                    margin: 0;
                    padding: 0;
                    height: 100vh;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    text-align: center;
                }}
                .success-container {{
                    background: rgba(0, 255, 157, 0.12);
                    border: 2px solid #00ff9d;
                    border-radius: 12px;
                    padding: 40px 30px;
                    max-width: 500px;
                    box-shadow: 0 0 40px rgba(0, 255, 157, 0.3);
                }}
                h1 {{
                    color: #8fb339;
                    text-shadow: 0 0 12px #8fb339;
                    margin-bottom: 20px;
                }}
                p {{
                    font-size: 1.2em;
                    margin: 10px 0;
                }}
                .countdown {{
                    font-size: 1.1em;
                    color: #aaa;
                }}
            </style>
        </head>
        <body>
            <div class="success-container">
                <h1>🎉 สมัครสมาชิกสำเร็จ!</h1>
                <p>ยินดีต้อนรับ <strong>{pager_id}</strong> สู่ PUK Pager Network</p>
                <p>คุณได้รับเครดิตเริ่มต้น 100 PUK</p>
                <p class="countdown">กำลังกลับไปหน้าแรกใน <span id="timer">3</span> วินาที...</p>
            </div>

            <script>
                alert('สมัครสมาชิกสำเร็จ! ยินดีต้อนรับสู่ PUK Pager Network 📟');

                let seconds = 3;
                const timerElement = document.getElementById('timer');
                
                const countdown = setInterval(() => {{
                    seconds--;
                    timerElement.textContent = seconds;
                    if (seconds <= 0) {{
                        clearInterval(countdown);
                        window.location.href = '/';
                    }}
                }}, 1000);
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=success_page)

    except sqlite3.IntegrityError:
        # จับกรณี ID ซ้ำ (PRIMARY KEY violation)
        error_page = """
        <!DOCTYPE html>
        <html lang="th">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>เกิดข้อผิดพลาด - PUK Pager Network</title>
            <style>
                body {
                    font-family: 'Courier New', Courier, monospace;
                    background: #0a0a0a;
                    color: #ff4d4d;
                    margin: 0;
                    height: 100vh;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    text-align: center;
                }
                .error-container {
                    background: rgba(255, 77, 77, 0.12);
                    border: 2px solid #ff4d4d;
                    border-radius: 12px;
                    padding: 40px 30px;
                    max-width: 500px;
                    box-shadow: 0 0 30px rgba(255, 77, 77, 0.3);
                }
                h1 { color: #ff4d4d; text-shadow: 0 0 10px #ff4d4d; }
                a { color: #00ff9d; text-decoration: underline; font-weight: bold; }
            </style>
        </head>
        <body>
            <div class="error-container">
                <h1>❌ ID นี้มีอยู่แล้ว</h1>
                <p>กรุณาเลือก ID อื่น แล้วลองสมัครใหม่</p>
                <p><a href="/">กลับไปหน้าแรก</a></p>
            </div>
            <script>
                alert('ID นี้ถูกใช้ไปแล้ว กรุณาเลือก ID ใหม่');
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=error_page, status_code=400)

    except Exception as e:
        return HTMLResponse(f"เกิดข้อผิดพลาด: {str(e)}", status_code=500)

# ระบบ Login
@app.post("/login")
async def login(data: dict):
    conn = sqlite3.connect(DB_NAME)
    user = conn.execute("SELECT password, balance FROM users WHERE pager_id = ?", (data['pager_id'],)).fetchone()
    conn.close()
    if user and (data.get('password') == "" or user[0] == data['password']):
        return {"status": "success", "balance": user[1]}
    return {"status": "error"}

# --- ระบบสมุดหมายเลข (Phonebook) ---
@app.post("/save_contact")
async def save_contact(data: dict):
    owner, contact, alias = data['owner_id'], data['contact_id'], data['alias']
    conn = sqlite3.connect(DB_NAME)
    conn.execute("INSERT OR REPLACE INTO phonebook VALUES (?, ?, ?)", (owner, contact, alias))
    conn.commit(); conn.close()
    return {"status": "success"}

@app.get("/get_contacts/{owner_id}")
async def get_contacts(owner_id: str):
    conn = sqlite3.connect(DB_NAME)
    contacts = conn.execute("SELECT contact_id, alias FROM phonebook WHERE owner_id = ?", (owner_id,)).fetchall()
    conn.close()
    return [{"id": c[0], "alias": c[1]} for c in contacts]

# --- การขุด (Mining) ---
# --- แก้ไขฟังก์ชันดึงข้อมูล Last Hash (แยกออกมาให้เรียกง่าย) ---
@app.get("/get_last_hash")
async def get_last_hash():
    conn = sqlite3.connect(DB_NAME)
    last = conn.execute("SELECT hash FROM blockchain ORDER BY idx DESC LIMIT 1").fetchone()
    conn.close()
    return {"hash": last[0] if last else "0" * 64}

# --- ปรับปรุงระบบ Mining ให้เสถียรขึ้น ---
@app.post("/mine")
async def mine(data: dict):
    p_id = data.get('pager_id')
    nonce = data.get('nonce')
    
    if not p_id or not nonce:
        return {"status": "error", "message": "Missing data"}

    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    try:
        # 1. ตรวจสอบ Hash ล่าสุดอีกครั้ง
        last = conn.execute("SELECT hash FROM blockchain ORDER BY idx DESC LIMIT 1").fetchone()
        last_h = last[0] if last else "0" * 64
        
        # 2. ตรวจสอบความถูกต้องของ Nonce ที่ Client ส่งมา
        chk_hash = hashlib.sha256(f"{p_id}{last_h}{nonce}".encode()).hexdigest()
        
        if chk_hash.startswith("000"):
            # 3. ให้รางวัล (Transaction)
            conn.execute("UPDATE users SET balance = balance + ? WHERE pager_id = ?", (REWARD_PER_BLOCK, p_id))
            conn.commit()
            
            # 4. บันทึกลง Blockchain
            write_to_blockchain(f"MINED:{p_id}", chk_hash, last_h)
            return {"status": "success", "reward": REWARD_PER_BLOCK}
        
        return {"status": "error", "message": "Invalid Proof-of-Work"}
    finally:
        conn.close()

# --- ระบบบันทึก Blockchain (เพิ่มความเสถียรของ Database) ---
def write_to_blockchain(data_string, custom_hash=None, prev_h=None):
    # ใช้ check_same_thread=False เพื่อรองรับการเรียกจาก WebSocket และ API พร้อมกัน
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    try:
        if not prev_h:
            last = conn.execute("SELECT hash FROM blockchain ORDER BY idx DESC LIMIT 1").fetchone()
            prev_h = last[0] if last else "0" * 64
        
        ts = time.time()
        if not custom_hash:
            block_content = f"{data_string}{prev_h}{ts}"
            custom_hash = hashlib.sha256(block_content.encode()).hexdigest()
            
        conn.execute("INSERT INTO blockchain (timestamp, data, prev_hash, hash) VALUES (?,?,?,?)", 
                     (ts, data_string, prev_h, custom_hash))
        conn.commit()
    finally:
        conn.close()

# --- คะแนนเกม (Snake Game) ---
# --- แก้ไขการดึง Leaderboard ให้เหลือ 5 อันดับ ---
@app.get("/leaderboard")
async def get_leaderboard():
    conn = sqlite3.connect(DB_NAME)
    # ดึงค่าสูงสุดของแต่ละคน และเรียงจากมากไปน้อย 5 อันดับแรก
    res = conn.execute("""
        SELECT pager_id, MAX(score) as top_score 
        FROM leaderboard 
        GROUP BY pager_id 
        ORDER BY top_score DESC 
        LIMIT 5
    """).fetchall()
    conn.close()
    return [{"pager_id": r[0], "score": r[1]} for r in res]

# --- ตรวจสอบฟังก์ชันบันทึกคะแนน ---
@app.post("/submit_score")
async def submit_score(data: dict):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("INSERT INTO leaderboard VALUES (?, ?, ?)", 
                 (data['pager_id'], data['score'], time.time()))
    conn.commit()
    conn.close()
    return {"status": "success"}



# --- การจัดการข้อความ (Messaging) ---
@app.get("/get_messages/{pager_id}")
async def get_messages(pager_id: str):
    conn = sqlite3.connect(DB_NAME)
    msgs = conn.execute("SELECT id, from_id, body, timestamp FROM messages WHERE to_id = ? ORDER BY timestamp DESC", (pager_id,)).fetchall()
    conn.close()
    return [{"id": m[0], "from": m[1], "body": m[2], "ts": m[3]} for m in msgs]

@app.post("/delete_msg")
async def delete_msg(data: dict):
    conn = sqlite3.connect(DB_NAME)
    if data.get('all'):
        conn.execute("DELETE FROM messages WHERE to_id = ?", (data['pager_id'],))
    else:
        # ลบโดยใช้ ID (Primary Key) จะแม่นยำที่สุด
        conn.execute("DELETE FROM messages WHERE id = ? AND to_id = ?", (data['msg_id'], data['pager_id']))
    conn.commit(); conn.close()
    return {"status": "success"}

@app.post("/transfer")
async def transfer_puk(data: dict):
    f_id, t_id, amount = data['from_id'], data['to_id'], int(data['amount'])
    if amount <= 0: return {"status": "error", "message": "Invalid amount"}
    
    conn = sqlite3.connect(DB_NAME)
    try:
        # เช็คยอดเงินคนส่ง
        sender = conn.execute("SELECT balance FROM users WHERE pager_id = ?", (f_id,)).fetchone()
        receiver = conn.execute("SELECT pager_id FROM users WHERE pager_id = ?", (t_id,)).fetchone()
        
        if not sender or sender[0] < amount:
            return {"status": "error", "message": "Insufficient funds"}
        if not receiver:
            return {"status": "error", "message": "Recipient not found"}
            
        # ทำการโอน
        conn.execute("UPDATE users SET balance = balance - ? WHERE pager_id = ?", (amount, f_id))
        conn.execute("UPDATE users SET balance = balance + ? WHERE pager_id = ?", (amount, t_id))
        conn.commit()
        
        # บันทึกลง Blockchain
        write_to_blockchain(f"TX:{f_id}>{t_id}:{amount}PUK")
        
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()

# --- Real-time Messaging (WebSocket) ---
# เก็บ connection
active_pagers: dict[str, WebSocket] = {}


@app.websocket("/ws/{pager_id}")
async def websocket_endpoint(websocket: WebSocket, pager_id: str):

    await websocket.accept()

    print(f"[CONNECTED] {pager_id}")

    # ถ้ามี connection เก่า ให้ปิดก่อน
    if pager_id in active_pagers:
        try:
            await active_pagers[pager_id].close()
        except:
            pass

    active_pagers[pager_id] = websocket

    try:
        while True:

            data = await websocket.receive_json()

            to_id = data.get("to")
            body = data.get("body")

            if not to_id or not body:
                await websocket.send_json({
                    "error": "invalid message"
                })
                continue

            ts = time.time()

            # save db
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()

            c.execute(
                "INSERT INTO messages (to_id, from_id, body, timestamp) VALUES (?,?,?,?)",
                (to_id, pager_id, body, ts)
            )

            msg_id = c.lastrowid

            conn.commit()
            conn.close()

            msg = {
                "id": msg_id,
                "from": pager_id,
                "to": to_id,
                "body": body,
                "ts": ts
            }

            print(f"[MSG] {pager_id} -> {to_id}: {body}")

            # send realtime ถ้า online
            if to_id in active_pagers:

                try:
                    await active_pagers[to_id].send_json(msg)
                    print(f"[DELIVERED] to {to_id}")

                except Exception as e:

                    print(f"[FAILED DELIVERY] {to_id}: {e}")

                    # remove dead connection
                    active_pagers.pop(to_id, None)

    except WebSocketDisconnect:

        print(f"[DISCONNECTED] {pager_id}")

    except Exception as e:

        print(f"[ERROR] {pager_id}: {e}")

    finally:

        # cleanup
        active_pagers.pop(pager_id, None)

        try:
            await websocket.close()
        except:
            pass

        print(f"[CLEANUP] {pager_id}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8139)