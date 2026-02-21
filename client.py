import tkinter as tk
from tkinter import messagebox
import websocket, threading, json, requests, time, random, platform, hashlib

# --- SERVER CONFIG ---
SERVER_HOST = "puchain.pukmupee.com"
SERVER_URL = f"https://{SERVER_HOST}"
WS_URL = f"wss://{SERVER_HOST}/ws"

class PagerApp:
    def __init__(self, root):
        self.root = root
        self.pager_id = None
        self.history = []
        self.current_idx = 0
        self.mode = "READ"
        self.game_running = False
        self.mining_active = False
        self.ws = None
        self.phonebook = []

        self.setup_window()
        self.show_login()

    def setup_window(self):
        if platform.system() == "Linux":
            self.root.attributes('-type', 'dialog')
        else:
            self.root.overrideredirect(True)
            
        self.root.attributes("-topmost", True)
        self.root.geometry("520x600+500+150") # ขยายความสูงเพิ่มเพื่อวางบาร์โค้ด
        self.root.configure(bg="#2c3e50")
        self.root.bind("<Button-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)

    def start_move(self, event): self._drag_x, self._drag_y = event.x, event.y
    def do_move(self, event):
        x, y = self.root.winfo_x() + (event.x - self._drag_x), self.root.winfo_y() + (event.y - self._drag_y)
        self.root.geometry(f"+{x}+{y}")

    def draw_round_rect(self, canvas, x1, y1, x2, y2, radius=25, **kwargs):
        p = [x1+radius, y1, x2-radius, y1, x2, y1, x2, y1+radius, x2, y2-radius, x2, y2, x2-radius, y2, x1+radius, y2, x1, y2, x1, y2-radius, x1, y1+radius, x1, y1]
        return canvas.create_polygon(p, **kwargs, smooth=True)

    def draw_barcode(self, canvas, x_start, y_start, text):
        """สร้างบาร์โค้ดแบบจำลองจาก Pager ID"""
        # สร้างพื้นหลังสีขาวเล็กๆ
        canvas.create_rectangle(x_start-10, y_start-5, x_start+160, y_start+45, fill="#ecf0f1", outline="")
        
        # สร้างเส้นบาร์โค้ดสุ่มความหนาตามตัวอักษรของ ID
        seed_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        random.seed(seed_val)
        
        curr_x = x_start
        for i in range(25):
            w = random.choice([1, 2, 4])
            gap = random.choice([1, 2])
            canvas.create_line(curr_x, y_start, curr_x, y_start+30, width=w, fill="black")
            curr_x += w + gap
        
        # แสดงเบอร์ใต้บาร์โค้ด
        canvas.create_text(x_start+75, y_start+38, text=f"S/N: {text}", font=("Arial", 8, "bold"), fill="black")

    def create_button(self, canvas, x, y, label, color, cmd, w=50, h=45, tcol="white"):
        def darken(hex_color):
            hex_color = hex_color.lstrip('#')
            rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            dark = tuple(max(0, int(c * 0.65)) for c in rgb)
            return f'#{dark[0]:02x}{dark[1]:02x}{dark[2]:02x}'
        normal_fill, pressed_fill = color, darken(color)
        btn_id = self.draw_round_rect(canvas, x-w/2, y-h/2, x+w/2, y+h/2, radius=12, fill=normal_fill, outline="#111", width=2)
        text_id = canvas.create_text(x, y, text=label, fill=tcol, font=("Arial", 11, "bold"))
        def on_press(e): canvas.itemconfig(btn_id, fill=pressed_fill); canvas.move(btn_id, 2, 2); canvas.move(text_id, 2, 2)
        def on_release(e): canvas.itemconfig(btn_id, fill=normal_fill); canvas.move(btn_id, -2, -2); canvas.move(text_id, -2, -2); cmd()
        for item in (btn_id, text_id):
            canvas.tag_bind(item, "<Button-1>", on_press)
            canvas.tag_bind(item, "<ButtonRelease-1>", on_release)

    def show_login(self):
        self.clear_screen()
        self.canvas = tk.Canvas(self.root, width=500, height=500, bg="#2c3e50", highlightthickness=0); self.canvas.pack(pady=10)
        self.draw_round_rect(self.canvas, 10, 10, 490, 480, radius=50, fill="#1a1a1a")
        self.draw_round_rect(self.canvas, 15, 15, 485, 475, radius=48, fill="#2d2d2d")
        self.canvas.create_text(250, 100, text="📟 PUK OS v10.0", font=("Courier", 20, "bold"), fill="#8fb339")
        self.info_text = self.canvas.create_text(250, 160, text="ENTER PAGER ID & PASSWORD", font=("Courier", 10), fill="#8fb339")
        self.id_entry = tk.Entry(self.root, width=14, font=("Courier", 12), bg="#000", fg="#8fb339", bd=0, justify="center"); self.canvas.create_window(140, 240, window=self.id_entry); self.id_entry.insert(0, "01-")
        self.pw_entry = tk.Entry(self.root, width=22, font=("Courier", 12), bg="#000", fg="#8fb339", bd=0, justify="center", show="*"); self.canvas.create_window(310, 240, window=self.pw_entry)
        self.create_button(self.canvas, 445, 180, "GO", "#27ae60", self.attempt_login, w=60, h=50)
        self.create_button(self.canvas, 460, 40, "X", "#c0392b", self.root.destroy, w=30, h=30)
        self.id_entry.focus_set()

    def attempt_login(self):
        p_id, pw = self.id_entry.get().strip(), self.pw_entry.get().strip()
        try:
            res = requests.post(f"{SERVER_URL}/login", json={"pager_id": p_id, "password": pw}, timeout=5).json()
            if res.get('status') == "success":
                self.pager_id = p_id
                self.show_os()
            else:
                self.canvas.itemconfig(self.info_text, text="ACCESS DENIED", fill="red")
        except:
            messagebox.showerror("Error", "Cannot connect to PUK Network Server")

    def show_os(self):
        self.clear_screen()
        # ขยาย Canvas ให้รองรับส่วนล่าง
        self.canvas = tk.Canvas(self.root, width=500, height=580, bg="#2c3e50", highlightthickness=0); self.canvas.pack(pady=10)
        
        # วาดตัวเครื่อง
        self.draw_round_rect(self.canvas, 10, 10, 490, 520, radius=50, fill="#1a1a1a")
        self.draw_round_rect(self.canvas, 15, 15, 485, 515, radius=48, fill="#2d2d2d")
        
        # วาดหน้าจอ LCD
        self.lcd_bg = self.draw_round_rect(self.canvas, 40, 40, 400, 220, radius=18, fill="#8fb339")
        self.screen_top = self.canvas.create_text(60, 60, anchor="nw", text="", font=("Courier", 10, "bold"), fill="#1a2401")
        self.screen_main = self.canvas.create_text(220, 130, text="WELCOME", font=("Courier", 16, "bold"), fill="#0c1101", width=320, justify="center")
        self.screen_bottom = self.canvas.create_text(60, 195, anchor="sw", text="SIGNAL: OK", font=("Courier", 9), fill="#1a2401")
        
        # วาดบาร์โค้ดที่ด้านล่างตัวเครื่อง (ใต้ปุ่ม)
        self.draw_barcode(self.canvas, 175, 435, self.pager_id)
        
        # ช่อง Input
        self.entry_1 = tk.Entry(self.root, width=12, font=("Courier", 11), bg="#000", fg="#8fb339", bd=0, justify="center"); self.canvas.create_window(125, 255, window=self.entry_1)
        self.entry_2 = tk.Entry(self.root, width=22, font=("Courier", 11), bg="#000", fg="#8fb339", bd=0, justify="center"); self.canvas.create_window(285, 255, window=self.entry_2)
        
        # ปุ่มกด
        self.create_button(self.canvas, 445, 90, "▲", "#4caf50", self.prev_msg, w=45, h=40)
        self.create_button(self.canvas, 445, 155, "RD", "#ffeb3b", self.enter_action, tcol="black", w=45, h=50)
        self.create_button(self.canvas, 445, 220, "▼", "#f44336", self.next_msg, w=45, h=40)
        self.create_button(self.canvas, 110, 310, "MENU", "#ffa000", self.open_menu, w=100, h=50)
        self.create_button(self.canvas, 225, 310, "DEL", "#c0392b", self.delete_handler, w=80, h=50)
        self.create_button(self.canvas, 460, 40, "X", "#c0392b", self.root.destroy, w=30, h=30)
        
        self.root.bind("<Return>", lambda e: self.enter_action())
        for d in ["Up", "Down", "Left", "Right"]: self.root.bind(f"<{d}>", lambda e, dir=d: self.change_dir(dir))
        
        self.set_input_state(False, False)
        threading.Thread(target=self.connect_ws_loop, daemon=True).start()
        self.refresh_inbox()

    def clear_screen(self): 
        for widget in self.root.winfo_children(): widget.destroy()

    def set_input_state(self, e1=False, e2=False):
        self.entry_1.config(state="normal" if e1 else "disabled"); self.entry_2.config(state="normal" if e2 else "disabled")
        if e1: self.entry_1.focus_force()

    def update_lcd(self, main="", top="", bottom=None):
        self.root.after(0, self._perform_update_lcd, main, top, bottom)

    def _perform_update_lcd(self, main, top, bottom):
        if self.canvas:
            if main: self.canvas.itemconfig(self.screen_main, text=str(main).upper())
            if top: self.canvas.itemconfig(self.screen_top, text=str(top).upper())
            if bottom is not None: self.canvas.itemconfig(self.screen_bottom, text=str(bottom).upper())

    def connect_ws_loop(self):
        while True:
            if not self.pager_id: break
            try:
                self.ws = websocket.WebSocketApp(f"{WS_URL}/{self.pager_id}", 
                    on_message=self.on_ws_msg,
                    on_open=lambda ws: self.update_lcd(bottom="SIGNAL: OK"),
                    on_close=lambda ws,c,m: self.update_lcd(bottom="SIGNAL: LOST"))
                self.ws.run_forever()
            except: pass
            time.sleep(5)

    def on_ws_msg(self, ws, message):
        data = json.loads(message)
        self.root.after(0, self._handle_incoming_msg, data)

    def _handle_incoming_msg(self, data):
        self.history.insert(0, data)
        self.current_idx = 0
        self.mode = "READ"
        self.update_lcd(main=data.get('body'), top=f"FROM: {data.get('from')}")

    def open_menu(self):
        self.mode = "MENU"; self.update_lcd(main="1.SEND  2.TX    3.MINE\n4.PB    5.SNAKE  6.BAL\n7.PURGE 8.TETRIS 9.RANK", top="MENU SELECT")
        self.set_input_state(True, False); self.entry_1.delete(0, tk.END); self.entry_2.delete(0, tk.END)

    def enter_action(self):
        v1, v2 = self.entry_1.get().strip(), self.entry_2.get().strip()
        if self.mode == "MENU":
            if v1 == "1": self.mode = "SEND"; self.update_lcd("TO ID | MSG", "SEND MESSAGE"); self.set_input_state(True, True)
            elif v1 == "2": self.mode = "SEND_COIN"; self.update_lcd("TO ID | AMOUNT", "TRANSFER PUK"); self.set_input_state(True, True)
            elif v1 == "3": self.start_mining()
            elif v1 == "4": self.open_pb()
            elif v1 == "5": self.start_snake()
            elif v1 == "6": self.check_bal()
            elif v1 == "8": self.start_tetris()
            elif v1 == "9": self.show_leaderboard()
            else: self.reset_ui()
            self.entry_1.delete(0, tk.END); self.entry_2.delete(0, tk.END)
        elif self.mode == "SEND":
            if v1 and v2 and self.ws: 
                try:
                    self.ws.send(json.dumps({"to": v1, "body": v2}))
                    self.update_lcd("SENT!", "SUCCESS")
                    self.root.after(1000, self.reset_ui)
                except: self.update_lcd("SEND ERR", "WS FAIL")
        elif self.mode == "SEND_COIN":
            if v1 and v2.isdigit(): self.send_puk(v1, int(v2))
        elif self.mode == "PB":
            if v1 == "0": self.mode = "PB_ADD"; self.update_lcd("ID | NAME", "ADD CONTACT"); self.set_input_state(True, True)
            elif v1.isdigit():
                idx = int(v1)-1
                if 0 <= idx < len(self.phonebook):
                    t = self.phonebook[idx]; self.mode = "SEND"; self.update_lcd(f"TO: {t['alias']}", "COMPOSE")
                    self.entry_1.delete(0, tk.END); self.entry_1.insert(0, t['id']); self.set_input_state(True, True)
        elif self.mode == "PB_ADD":
            if v1 and v2: requests.post(f"{SERVER_URL}/save_contact", json={"owner_id": self.pager_id, "contact_id": v1, "alias": v2}); self.open_pb()
        elif self.mode == "MINE": self.stop_mining()
        elif "OVER" in self.mode or self.mode == "RANK": self.reset_ui()
        else: self.refresh_inbox()

    def send_puk(self, target_id, amount):
        try:
            res = requests.post(f"{SERVER_URL}/transfer", json={"from_id": self.pager_id, "to_id": target_id, "amount": amount}).json()
            self.update_lcd(res.get("message", "SUCCESS"), "TX STATUS"); self.root.after(2000, self.reset_ui)
        except: self.update_lcd("ERROR", "TX FAILED")

    def submit_score(self, score):
        try: requests.post(f"{SERVER_URL}/submit_score", json={"pager_id": self.pager_id, "score": score})
        except: pass

    def show_leaderboard(self):
        try:
            res = requests.get(f"{SERVER_URL}/leaderboard").json()
            board = "\n".join([f"{r['pager_id']}: {r['score']}" for r in res[:5]])
            self.update_lcd(board, "TOP 5 RANK"); self.mode = "RANK"
        except: self.update_lcd("EMPTY", "RANK")

    def delete_handler(self):
        if self.mode == "READ" and self.history:
            mid = self.history[self.current_idx].get('id')
            requests.post(f"{SERVER_URL}/delete_msg", json={"pager_id": self.pager_id, "msg_id": mid})
            self.history.pop(self.current_idx); self.reset_ui()

    def refresh_inbox(self):
        try:
            r = requests.get(f"{SERVER_URL}/get_messages/{self.pager_id}")
            if r.status_code == 200: self.history = r.json(); self.show_msg()
        except: self.update_lcd("OFFLINE", "SIGNAL")

    def show_msg(self):
        if not self.history: self.update_lcd("NO MESSAGES", "INBOX"); return
        m = self.history[self.current_idx]
        self.update_lcd(main=m.get('body'), top=f"FROM: {m.get('from')}  {self.current_idx+1}/{len(self.history)}")

    def prev_msg(self):
        if self.history: self.current_idx = (self.current_idx-1)%len(self.history); self.show_msg()
    def next_msg(self):
        if self.history: self.current_idx = (self.current_idx+1)%len(self.history); self.show_msg()
    def reset_ui(self): 
        self.mining_active = False; self.mode = "READ"; self.game_running = False; self.set_input_state(False, False); self.refresh_inbox()

    def start_mining(self):
        self.mode = "MINE"; self.mining_active = True; self.update_lcd("CONNECTING...", "PUK MINER")
        threading.Thread(target=self.mine_worker, daemon=True).start()

    def mine_worker(self):
        try:
            while self.mining_active:
                lh_res = requests.get(f"{SERVER_URL}/get_last_hash", timeout=5).json()
                lh = lh_res.get("hash", "0"*64)
                n = random.randint(0, 1000000)
                for _ in range(5000):
                    if not self.mining_active: return
                    h = hashlib.sha256(f"{self.pager_id}{lh}{n}".encode()).hexdigest()
                    if h.startswith("000"):
                        requests.post(f"{SERVER_URL}/mine", json={"pager_id": self.pager_id, "nonce": n})
                        self.update_lcd("BLOCK MINED!", "SUCCESS")
                        time.sleep(2)
                        break
                    n += 1
                self.update_lcd(f"MINING...\nNONCE: {n}", "PUK CHAIN")
                time.sleep(0.01)
        except: 
            self.update_lcd("MINER ERROR", "RETRYING...")
            time.sleep(2)
            self.root.after(0, self.reset_ui)

    def stop_mining(self): self.mining_active = False; self.reset_ui()

    def start_snake(self):
        self.mode = "SNAKE"; self.game_running = True; self.snake = [(10,5),(9,5)]; self.direction = "Right"; self.spawn_food(); self.run_snake()
    def spawn_food(self): self.food = (random.randint(0,19), random.randint(0,9))
    def run_snake(self):
        if not self.game_running or self.mode != "SNAKE": return
        hx, hy = self.snake[0]
        dx, dy = {"Up":(0,-1), "Down":(0,1), "Left":(-1,0), "Right":(1,0)}[self.direction]
        nx, ny = (hx+dx)%20, (hy+dy)%10
        if (nx,ny) in self.snake: 
            sc = len(self.snake)-2; self.mode="SNAKE_OVER"; self.update_lcd(f"SCORE: {sc}", "GAME OVER"); self.submit_score(sc); return
        self.snake.insert(0, (nx,ny))
        if (nx,ny) == self.food: self.spawn_food()
        else: self.snake.pop()
        g = [["·"]*20 for _ in range(10)]; g[self.food[1]][self.food[0]] = "X"
        for x,y in self.snake: g[y][x] = "■"
        self.update_lcd("\n".join("".join(r) for r in g), f"SNAKE SC:{len(self.snake)-2}"); self.root.after(150, self.run_snake)

    def start_tetris(self):
        self.mode = "TETRIS"; self.game_running = True; self.board = [[0]*10 for _ in range(15)]; self.score = 0; self.new_piece(); self.run_tetris()
    def new_piece(self): self.piece = random.choice([[[1,1,1,1]],[[1,1],[1,1]],[[0,1,0],[1,1,1]]]); self.px, self.py = 3, 0
    def check_collision(self, x, y, p):
        for r, row in enumerate(p):
            for c, v in enumerate(row):
                if v and (x+c<0 or x+c>=10 or y+r>=15 or (y+r>=0 and self.board[y+r][x+c])): return True
        return False
    def run_tetris(self):
        if not self.game_running or self.mode != "TETRIS": return
        if not self.check_collision(self.px, self.py+1, self.piece): self.py += 1
        else:
            for r, row in enumerate(self.piece):
                for c, v in enumerate(row):
                    if v: self.board[self.py+r][self.px+c] = 1
            self.board = [r for r in self.board if 0 in r]
            while len(self.board)<15: self.board.insert(0, [0]*10); self.score += 10
            self.new_piece()
        temp = [r[:] for r in self.board]
        for r, row in enumerate(self.piece):
            for c, v in enumerate(row):
                if v and self.py+r < 15: temp[self.py+r][self.px+c] = 1
        self.update_lcd("\n".join("".join("■" if v else "·" for v in r) for r in temp), f"TETRIS SC:{self.score}"); self.root.after(400, self.run_tetris)

    def change_dir(self, d):
        if self.mode == "SNAKE": self.direction = d
        elif self.mode == "TETRIS":
            if d == "Left" and not self.check_collision(self.px-1, self.py, self.piece): self.px -= 1
            if d == "Right" and not self.check_collision(self.px+1, self.py, self.piece): self.px += 1
            if d == "Up": 
                rot = [list(r) for r in zip(*self.piece[::-1])]
                if not self.check_collision(self.px, self.py, rot): self.piece = rot

    def open_pb(self):
        try: self.phonebook = requests.get(f"{SERVER_URL}/get_contacts/{self.pager_id}").json()
        except: self.phonebook = []
        txt = "0. ADD NEW\n" + "\n".join(f"{i+1}. {c.get('alias','?')}" for i, c in enumerate(self.phonebook[:5]))
        self.mode = "PB"; self.update_lcd(txt or "EMPTY", "PHONEBOOK"); self.set_input_state(True, False)

    def check_bal(self):
        try:
            res = requests.get(f"{SERVER_URL}/get_balance/{self.pager_id}", timeout=5).json()
            if res.get("status") == "success":
                bal = res.get('balance', 0)
                self.update_lcd(f"BALANCE:\n{bal:,} PUK", "BANK")
            else: self.update_lcd("NOT FOUND", "BANK")
        except: self.update_lcd("CONN ERROR", "BANK")
        self.root.after(2500, self.reset_ui)

if __name__ == "__main__":
    root = tk.Tk(); app = PagerApp(root); root.mainloop()