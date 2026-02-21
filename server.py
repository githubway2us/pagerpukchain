import sqlite3
import hashlib
import time
import json
import re
import random
import html
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Form, Request, HTTPException
from fastapi.responses import HTMLResponse

app = FastAPI()
DB_NAME = "pager_network.db"
ADMIN_ID = "01-0001"
REWARD_PER_BLOCK = 50
SALT = "puk_retro_secure_salt_2026"  # ใช้สำหรับ Hash รหัสผ่าน

# --- 1. ระบบจัดการฐานข้อมูล (Database Management) ---
def get_db():
    # ใช้ check_same_thread=False เพื่อให้รองรับ WebSocket และ API พร้อมกัน
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # ให้เรียกข้อมูลผ่านชื่อคอลัมน์ได้
    return conn

def hash_password(password: str):
    """ เข้ารหัสผ่านเพื่อความปลอดภัยสูงสุด """
    return hashlib.sha256((password + SALT).encode()).hexdigest()

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (pager_id TEXT PRIMARY KEY, password TEXT, balance INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, to_id TEXT, from_id TEXT, body TEXT, timestamp REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS blockchain (idx INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL, data TEXT, prev_hash TEXT, hash TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS leaderboard (pager_id TEXT, score INTEGER, timestamp REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS phonebook (owner_id TEXT, contact_id TEXT, alias TEXT, PRIMARY KEY(owner_id, contact_id))')
    
    hashed_admin_pw = hash_password("---")
    c.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?)", (ADMIN_ID, hashed_admin_pw, 1000000))
    conn.commit()
    conn.close()

init_db()

# --- 2. Logic ช่วยเหลือ (Helpers) ---
def generate_unique_id():
    conn = get_db()
    while True:
        random_num = random.randint(1, 9999)
        new_id = f"01-{random_num:04d}"
        exists = conn.execute("SELECT 1 FROM users WHERE pager_id = ?", (new_id,)).fetchone()
        if not exists:
            conn.close()
            return new_id

def write_to_blockchain(data_string, custom_hash=None, prev_h=None):
    conn = get_db()
    try:
        if not prev_h:
            last = conn.execute("SELECT hash FROM blockchain ORDER BY idx DESC LIMIT 1").fetchone()
            prev_h = last['hash'] if last else "0" * 64
        ts = time.time()
        if not custom_hash:
            block_content = f"{data_string}{prev_h}{ts}"
            custom_hash = hashlib.sha256(block_content.encode()).hexdigest()
        conn.execute("INSERT INTO blockchain (timestamp, data, prev_hash, hash) VALUES (?,?,?,?)", 
                     (ts, data_string, prev_h, custom_hash))
        conn.commit()
    finally:
        conn.close()

# --- เพิ่ม Endpoint นี้ใน server.py ---
@app.get("/get_last_hash")
async def get_last_hash():
    conn = get_db()
    last = conn.execute("SELECT hash FROM blockchain ORDER BY idx DESC LIMIT 1").fetchone()
    conn.close()
    return {"hash": last['hash'] if last else "0" * 64}

# --- แก้ไขฟังก์ชัน web_interface (จุดที่ Error เดิม) ---
# --- WEB INTERFACE (Responsive + Mobile Friendly) ---
@app.get("/", response_class=HTMLResponse)
async def web_interface():
    conn = get_db()
    total_mined_coins = conn.execute("SELECT SUM(balance) as total FROM users").fetchone()['total'] or 0
    blocks = conn.execute("SELECT idx, timestamp, data, hash FROM blockchain ORDER BY idx DESC LIMIT 15").fetchall()
    mining_blocks = conn.execute("SELECT COUNT(*) as count FROM blockchain WHERE data LIKE 'MINED:%'").fetchone()['count']
    total_users = conn.execute("SELECT COUNT(*) as count FROM users").fetchone()['count']
    rich_list = conn.execute("SELECT pager_id, balance FROM users ORDER BY balance DESC LIMIT 5").fetchall()
    conn.close()

    block_rows = ""
    for b in blocks:
        is_mine = "color: #c2a633; font-weight: bold; background: rgba(194,166,51,0.15);" if "MINED:" in b['data'] else ""
        block_rows += f"""
        <tr style="{is_mine}">
            <td>{b['idx']}</td>
            <td>{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(b['timestamp']))}</td>
            <td>{b['data'][:80]}{'...' if len(b['data']) > 80 else ''}</td>
            <td><code>{b['hash'][:16]}...</code></td>
        </tr>
        """

    rich_rows = "".join([
        f"<li><strong>{r['pager_id']}</strong> — <span style='color:#c2a633;'>{r['balance']:,} PUK</span></li>"
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
            :root {{
                --primary: #c2a633;
                --dark: #1a1a2e;
                --darker: #16213e;
            }}

            * {{ box-sizing: border-box; }}

            body {{
                margin: 0;
                font-family: 'Comic Neue', 'Comic Sans MS', cursive, sans-serif;
                background: linear-gradient(135deg, var(--dark) 0%, var(--darker) 100%);
                color: #ffffff;
                min-height: 100vh;
                position: relative;
                overflow-x: hidden;
                font-size: 16px;
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
                padding: 1rem;
            }}

            header {{
                text-align: center;
                padding: 3rem 1rem 2rem;
                background: rgba(0,0,0,0.5);
                border-bottom: 4px solid var(--primary);
            }}

            .logo {{
                width: clamp(120px, 35vw, 180px);
                height: auto;
                margin-bottom: 1rem;
                filter: drop-shadow(0 0 20px var(--primary));
                animation: bounce 3s infinite;
            }}

            @keyframes bounce {{
                0%, 100% {{ transform: translateY(0); }}
                50% {{ transform: translateY(-15px); }}
            }}

            h1 {{
                font-size: clamp(2.5rem, 8vw, 4rem);
                margin: 0;
                color: var(--primary);
                text-shadow: 0 0 30px #c2a63388;
                letter-spacing: 0.25rem;
            }}

            h1 span {{ color: #ffffff; }}

            .subtitle {{
                font-size: clamp(1.2rem, 4vw, 1.8rem);
                margin: 0.5rem 0 1.5rem;
                color: #e0e0e0;
            }}

            .stats {{
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
                gap: 1.5rem;
                margin: 2rem 0;
            }}

            .stat-card {{
                background: rgba(194,166,51,0.15);
                border: 2px solid var(--primary);
                border-radius: 16px;
                padding: 1.5rem 2rem;
                min-width: 180px;
                flex: 1 1 220px;
                max-width: 300px;
                text-align: center;
                box-shadow: 0 8px 25px rgba(194,166,51,0.3);
                transition: transform 0.3s;
            }}

            .stat-card:hover {{ transform: translateY(-8px); }}

            .stat-value {{
                font-size: clamp(1.8rem, 6vw, 2.8rem);
                font-weight: bold;
                color: var(--primary);
            }}

            .stat-label {{ font-size: 1.1rem; color: #ddd; }}

            .tabs {{
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
                gap: 0.8rem;
                margin: 2rem 0 1rem;
            }}

            .tab {{
                padding: 0.8rem 1.5rem;
                background: rgba(255,255,255,0.08);
                border: 2px solid var(--primary);
                border-radius: 50px;
                color: var(--primary);
                font-weight: bold;
                cursor: pointer;
                transition: all 0.3s;
                font-size: 1rem;
            }}

            .tab:hover, .tab.active {{
                background: var(--primary);
                color: var(--dark);
                transform: scale(1.05);
            }}

            .tab-content {{
                display: none;
                background: rgba(0,0,0,0.6);
                border-radius: 16px;
                padding: 1.5rem;
                border: 1px solid #c2a63344;
                text-align: center;
            }}

            .tab-content.show {{ display: block; }}

            .coming-soon {{
                font-size: clamp(2.5rem, 10vw, 3.5rem);
                font-weight: bold;
                color: var(--primary);
                text-shadow: 0 0 20px #c2a63388;
                margin: 3rem 0 1rem;
                animation: pulse 2s infinite;
            }}

            @keyframes pulse {{
                0% {{ transform: scale(1); }}
                50% {{ transform: scale(1.05); }}
                100% {{ transform: scale(1); }}
            }}

            .coming-text {{ font-size: 1.4rem; color: #e0e0e0; margin: 1rem 0; }}

            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 1rem;
                font-size: 0.95rem;
            }}

            th, td {{
                padding: 0.8rem;
                text-align: left;
                border-bottom: 1px solid #444;
            }}

            th {{ background: rgba(194,166,51,0.15); color: var(--primary); }}

            tr:hover {{ background: rgba(194,166,51,0.1); }}

            .register-form {{
                max-width: 100%;
                margin: 0 auto;
                background: rgba(194,166,51,0.1);
                padding: 1.5rem;
                border-radius: 16px;
                border: 2px solid var(--primary);
            }}

            input, button {{
                width: 100%;
                padding: 0.9rem;
                margin: 0.6rem 0;
                border-radius: 8px;
                font-size: 1rem;
                border: 2px solid var(--primary);
                background: var(--dark);
                color: white;
            }}

            button {{
                background: var(--primary);
                color: var(--dark);
                font-weight: bold;
                cursor: pointer;
                border: none;
                min-height: 48px;
            }}

            button:hover {{ background: #d4b760; }}

            .wow-text {{
                text-align: center;
                font-size: 1.6rem;
                color: var(--primary);
                margin: 2rem 0;
                font-style: italic;
            }}

            /* Mobile adjustments */
            @media (min-width: 640px) {{
                .container {{ padding: 1.5rem 2rem; }}
            }}

            @media (min-width: 768px) {{
                header {{ padding: 5rem 2rem 3rem; }}
                .tabs {{ gap: 1rem; }}
                .tab {{ padding: 1rem 2rem; font-size: 1.1rem; }}
                table {{ font-size: 1rem; }}
                th, td {{ padding: 1rem 1.2rem; }}
            }}

            @media (max-width: 640px) {{
                table {{ display: block; overflow-x: auto; white-space: nowrap; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <img src="https://pngimg.com/d/pager_PNG23.png" alt="puk" class="logo">
                <h1>PUK <span>PAGER</span> NETWORK</h1>
                <div class="subtitle">much pager • very blockchain • wow</div>
                <p style="margin-top: -10px; font-size: 1.2rem;">
                    <a href="https://x.com/pukcoin" style="color: #c2a633; text-decoration: none; font-weight: bold;" target="_blank">@pukcoin on X</a>
                </p>
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
                <div class="tab" onclick="openTab('download')">DOWNLOAD CLIENT</div>
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

                <h2 style="margin-top:2rem;">Rich Shibes</h2>
                <ul style="list-style:none; padding:0; font-size:1.2rem; text-align:left; max-width:400px; margin:1rem auto;">
                    {rich_rows}
                </ul>
            </div>

            <div id="register" class="tab-content">
                <h2>much register • join now wow</h2>
                <form action="/register" method="post" class="register-form">
                    <p style="text-align:center; color:#c2a633; margin-bottom:1.5rem;">System will generate a unique Pager ID for you!</p>
                    <input type="password" name="password" placeholder="set password (min 6 chars)" minlength="6" required>
                    <button type="submit">GENERATE MY PAGER →</button>
                </form>
                <p style="text-align:center; margin-top:1.5rem; color:#aaa;">100 PUK starting balance • very generous</p>
            </div>

            <div id="howtouse" class="tab-content">
                <h2>How to Use – very easy</h2>
                <div style="background:rgba(194,166,51,0.1); padding:1.5rem; border-radius:12px; border:1px solid #c2a633; text-align:left; max-width:600px; margin:1rem auto;">
                    <p><strong>1. Login</strong> → open client • enter ID + pass</p>
                    <p><strong>2. Send message</strong> → menu 1 • to ID + text</p>
                    <p><strong>3. Mine PUK</strong> → menu 3 • much compute wow</p>
                    <p><strong>4. Play game</strong> → snake / tetris • fun & score</p>
                </div>
            </div>

            <div id="download" class="tab-content">
                <h2 class="coming-soon">COMING SOON!!</h2>
                <p class="coming-text">Client สำหรับ Windows / macOS / Linux / Android กำลังพัฒนาอยู่</p>
                <p class="coming-text">เตรียมตัวให้พร้อม • จะมาแบบ very fast • wow</p>
                <p style="margin-top:3rem; color:#c2a633; font-size:1.3rem;">
                    (ตอนนี้ใช้ Web interface ไปก่อนนะ 555)
                </p>
            </div>

            <div id="blockchain" class="tab-content">
                <h2>What is this? – very blockchain</h2>
                <div style="background:rgba(194,166,51,0.1); padding:1.5rem; border-radius:12px; border:1px solid #c2a633; text-align:left; max-width:600px; margin:1rem auto;">
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
@app.post("/register")
async def register(password: str = Form(...)):
    if len(password) < 6: 
        return HTMLResponse("<script>alert('Password too short!'); window.history.back();</script>", status_code=400)
    
    pager_id = generate_unique_id()
    hashed_pw = hash_password(password)
    conn = get_db()
    try:
        conn.execute("INSERT INTO users VALUES (?, ?, ?)", (pager_id, hashed_pw, 100))
        conn.commit()
        write_to_blockchain(f"NEW_USER:{pager_id}")
        
        # คืนค่าหน้า HTML ที่ตกแต่งแล้ว
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Registration Success - PUK PAGER</title>
            <link href="https://fonts.googleapis.com/css2?family=Comic+Neue:wght@700&family=Roboto:wght@400;700&display=swap" rel="stylesheet">
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    font-family: 'Roboto', sans-serif;
                    background: #1a1a2e;
                    color: white;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    text-align: center;
                }}
                .card {{
                    background: rgba(194,166,51,0.1);
                    border: 3px solid #c2a633;
                    padding: 40px;
                    border-radius: 20px;
                    box-shadow: 0 0 30px rgba(194,166,51,0.2);
                    max-width: 400px;
                    width: 90%;
                }}
                h1 {{ font-family: 'Comic Neue', cursive; color: #c2a633; margin-bottom: 10px; }}
                .pager-id {{
                    font-size: 3rem;
                    font-weight: bold;
                    color: #ffffff;
                    background: #c2a633;
                    padding: 10px 20px;
                    border-radius: 10px;
                    margin: 20px 0;
                    display: inline-block;
                    letter-spacing: 2px;
                }}
                .warning {{
                    background: rgba(255, 0, 0, 0.2);
                    border: 1px solid #ff4d4d;
                    color: #ff4d4d;
                    padding: 15px;
                    border-radius: 8px;
                    margin: 20px 0;
                    font-size: 0.9rem;
                }}
                .btn {{
                    display: inline-block;
                    margin-top: 20px;
                    padding: 12px 25px;
                    background: #c2a633;
                    color: #1a1a2e;
                    text-decoration: none;
                    font-weight: bold;
                    border-radius: 50px;
                    transition: 0.3s;
                }}
                .btn:hover {{ transform: scale(1.1); background: #f1c40f; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1>MUCH SUCCESS!</h1>
                <p>ยินดีด้วย! คุณได้รับหมายเลขเพจเจอร์แล้ว</p>
                <div class="pager-id">{pager_id}</div>
                
                <div class="warning">
                    <strong>⚠️ ข้อควรระวัง:</strong><br>
                    กรุณาจดบันทึกหมายเลข Pager ID นี้ไว้ให้ดี <br>
                    เราไม่มีระบบกู้คืนไอดีหากคุณทำหาย!
                </div>

                <a href="/" class="btn">GO TO EXPLORER →</a>
            </div>
        </body>
        </html>
        """)
    finally: 
        conn.close()

@app.post("/login")
async def login(data: dict):
    p_id = data.get('pager_id')
    raw_pw = data.get('password', '')
    
    conn = get_db()
    user = conn.execute("SELECT password, balance FROM users WHERE pager_id = ?", (p_id,)).fetchone()
    conn.close()

    if not user:
        return {"status": "error", "message": "User not found"}

    # คำนวณ Hash จากรหัสที่ส่งมา เทียบกับที่เก็บใน DB
    incoming_hash = hash_password(raw_pw)
    if user['password'] == incoming_hash:
        return {"status": "success", "balance": user['balance']}
    else:
        # Debug: พิมพ์ออกมาดูใน Terminal ของ Server ว่าทำไมไม่ตรง
        print(f"Login Fail for {p_id}: DB_HASH={user['password']} VS INCOMING={incoming_hash}")
        return {"status": "error", "message": "Invalid password"}
    
@app.post("/save_contact")
async def save_contact(data: dict):
    conn = get_db()
    # html.escape ป้องกัน XSS ในชื่อเล่น
    conn.execute("INSERT OR REPLACE INTO phonebook VALUES (?, ?, ?)", 
                 (data['owner_id'], data['contact_id'], html.escape(data['alias'])))
    conn.commit(); conn.close()
    return {"status": "success"}

@app.get("/get_contacts/{owner_id}")
async def get_contacts(owner_id: str):
    conn = get_db()
    res = conn.execute("SELECT contact_id, alias FROM phonebook WHERE owner_id = ?", (owner_id,)).fetchall()
    conn.close()
    return [{"id": r['contact_id'], "alias": r['alias']} for r in res]

@app.post("/mine")
async def mine(data: dict):
    p_id, nonce = data.get('pager_id'), data.get('nonce')
    conn = get_db()
    try:
        last = conn.execute("SELECT hash FROM blockchain ORDER BY idx DESC LIMIT 1").fetchone()
        last_h = last['hash'] if last else "0" * 64
        chk_hash = hashlib.sha256(f"{p_id}{last_h}{nonce}".encode()).hexdigest()
        if chk_hash.startswith("000"):
            conn.execute("UPDATE users SET balance = balance + ? WHERE pager_id = ?", (REWARD_PER_BLOCK, p_id))
            conn.commit()
            write_to_blockchain(f"MINED:{p_id}", chk_hash, last_h)
            return {"status": "success", "reward": REWARD_PER_BLOCK}
        return {"status": "error"}
    finally: conn.close()

@app.post("/transfer")
async def transfer_puk(data: dict):
    f_id, t_id, amount = data['from_id'], data['to_id'], int(data['amount'])
    if amount <= 0: return {"status": "error"}
    conn = get_db()
    try:
        sender = conn.execute("SELECT balance FROM users WHERE pager_id = ?", (f_id,)).fetchone()
        if sender and sender['balance'] >= amount:
            conn.execute("UPDATE users SET balance = balance - ? WHERE pager_id = ?", (amount, f_id))
            conn.execute("UPDATE users SET balance = balance + ? WHERE pager_id = ?", (amount, t_id))
            conn.commit()
            write_to_blockchain(f"TX:{f_id}>{t_id}:{amount}PUK")
            return {"status": "success"}
        return {"status": "error", "message": "Insufficient funds"}
    finally: conn.close()

@app.get("/leaderboard")
async def get_leaderboard():
    conn = get_db()
    res = conn.execute("SELECT pager_id, MAX(score) as top FROM leaderboard GROUP BY pager_id ORDER BY top DESC LIMIT 5").fetchall()
    conn.close()
    return [{"pager_id": r['pager_id'], "score": r['top']} for r in res]

@app.post("/submit_score")
async def submit_score(data: dict):
    conn = get_db()
    conn.execute("INSERT INTO leaderboard VALUES (?, ?, ?)", (data['pager_id'], data['score'], time.time()))
    conn.commit(); conn.close()
    return {"status": "success"}

@app.get("/get_messages/{pager_id}")
async def get_messages(pager_id: str):
    conn = get_db()
    msgs = conn.execute("SELECT id, from_id, body, timestamp FROM messages WHERE to_id = ? ORDER BY timestamp DESC", (pager_id,)).fetchall()
    conn.close()
    return [{"id": m['id'], "from": m['from_id'], "body": m['body'], "ts": m['timestamp']} for m in msgs]

@app.post("/delete_msg")
async def delete_msg(data: dict):
    conn = get_db()
    if data.get('all'):
        conn.execute("DELETE FROM messages WHERE to_id = ?", (data['pager_id'],))
    else:
        conn.execute("DELETE FROM messages WHERE id = ? AND to_id = ?", (data['msg_id'], data['pager_id']))
    conn.commit(); conn.close()
    return {"status": "success"}

@app.get("/get_balance/{pager_id}")
async def get_balance(pager_id: str):
    conn = get_db()
    user = conn.execute("SELECT balance FROM users WHERE pager_id = ?", (pager_id,)).fetchone()
    conn.close()
    if user:
        return {"status": "success", "balance": user['balance']}
    return {"status": "error", "message": "User not found"}

# --- 5. Real-time Messaging (WebSocket) ---
active_pagers: dict[str, WebSocket] = {}

@app.websocket("/ws/{pager_id}")
async def websocket_endpoint(websocket: WebSocket, pager_id: str):
    await websocket.accept()
    active_pagers[pager_id] = websocket
    try:
        while True:
            data = await websocket.receive_json()
            to_id, body = data.get("to"), html.escape(data.get("body", ""))
            if not to_id or not body: continue
            
            ts = time.time()
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO messages (to_id, from_id, body, timestamp) VALUES (?,?,?,?)", (to_id, pager_id, body, ts))
            msg_id = cursor.lastrowid
            conn.commit(); conn.close()

            if to_id in active_pagers:
                await active_pagers[to_id].send_json({"id": msg_id, "from": pager_id, "body": body, "ts": ts})
    except:
        active_pagers.pop(pager_id, None)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8139)