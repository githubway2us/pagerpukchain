import tkinter as tk
from tkinter import messagebox
import websocket, threading, json, requests, time, random, platform, hashlib

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
        if platform.system() == "Linux": self.root.attributes('-type', 'splash')
        else: self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.geometry("520x550+500+200")
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
        self.info_text = self.canvas.create_text(250, 160, text="SYSTEM READY", font=("Courier", 11), fill="#8fb339")
        self.id_entry = tk.Entry(self.root, width=14, font=("Courier", 12), bg="#000", fg="#8fb339", bd=0, justify="center"); self.canvas.create_window(140, 240, window=self.id_entry); self.id_entry.insert(0, "01-")
        self.pw_entry = tk.Entry(self.root, width=22, font=("Courier", 12), bg="#000", fg="#8fb339", bd=0, justify="center", show="*"); self.canvas.create_window(310, 240, window=self.pw_entry)
        self.create_button(self.canvas, 445, 180, "GO", "#27ae60", self.attempt_login, w=60, h=50)
        self.create_button(self.canvas, 460, 40, "X", "#c0392b", self.root.destroy, w=30, h=30)
        self.id_entry.focus_set()

    def attempt_login(self):
        p_id, pw = self.id_entry.get().strip(), self.pw_entry.get().strip()
        try:
            res = requests.post(f"{SERVER_URL}/login", json={"pager_id": p_id, "password": pw}, timeout=5)
            print("Login response status:", res.status_code)  # debug
            print("Login response text:", res.text)           # debug
            data = res.json()
            if data.get('status') == "success":
                self.pager_id = p_id
                self.show_os()
            else:
                msg = data.get('message', 'ACCESS DENIED')
                self.canvas.itemconfig(self.info_text, text=f"ERROR: {msg}")
        except Exception as e:
            print("Login exception:", str(e))
            messagebox.showerror("Error", f"Server issue: {str(e)}")

    def show_os(self):
        self.clear_screen()
        self.canvas = tk.Canvas(self.root, width=500, height=500, bg="#2c3e50", highlightthickness=0); self.canvas.pack(pady=10)
        self.draw_round_rect(self.canvas, 10, 10, 490, 480, radius=50, fill="#1a1a1a")
        self.draw_round_rect(self.canvas, 15, 15, 485, 475, radius=48, fill="#2d2d2d")
        self.lcd_bg = self.draw_round_rect(self.canvas, 40, 40, 400, 220, radius=18, fill="#8fb339")
        self.screen_top = self.canvas.create_text(60, 60, anchor="nw", text="", font=("Courier", 10, "bold"), fill="#1a2401")
        self.screen_main = self.canvas.create_text(220, 130, text="WELCOME", font=("Courier", 16, "bold"), fill="#0c1101", width=320, justify="center")
        self.screen_bottom = self.canvas.create_text(60, 195, anchor="sw", text="SIGNAL: OK", font=("Courier", 9), fill="#1a2401")
        self.entry_1 = tk.Entry(self.root, width=12, font=("Courier", 11), bg="#000", fg="#8fb339", bd=0, justify="center"); self.canvas.create_window(125, 255, window=self.entry_1)
        self.entry_2 = tk.Entry(self.root, width=22, font=("Courier", 11), bg="#000", fg="#8fb339", bd=0, justify="center"); self.canvas.create_window(285, 255, window=self.entry_2)
        
        self.create_button(self.canvas, 445, 90, "▲", "#4caf50", self.prev_msg, w=45, h=40)
        self.create_button(self.canvas, 445, 155, "RD", "#ffeb3b", self.enter_action, tcol="black", w=45, h=50)
        self.create_button(self.canvas, 445, 220, "▼", "#f44336", self.next_msg, w=45, h=40)
        self.create_button(self.canvas, 110, 310, "MENU", "#ffa000", self.open_menu, w=100, h=50)
        self.create_button(self.canvas, 225, 310, "DEL", "#c0392b", self.delete_handler, w=80, h=50)
        self.create_button(self.canvas, 460, 40, "X", "#c0392b", self.root.destroy, w=30, h=30)
        
        self.root.bind("<Return>", lambda e: self.enter_action())
        for d in ["Up", "Down", "Left", "Right"]: self.root.bind(f"<{d}>", lambda e, dir=d: self.change_dir(dir))
        self.set_input_state(False, False); threading.Thread(target=self.connect_ws_loop, daemon=True).start(); self.refresh_inbox()

    def clear_screen(self): 
        for widget in self.root.winfo_children(): widget.destroy()

    def set_input_state(self, e1=False, e2=False):
        self.entry_1.config(state="normal" if e1 else "disabled"); self.entry_2.config(state="normal" if e2 else "disabled")
        if e1: self.entry_1.focus_force()

    def update_lcd(self, main="", top="", bottom=None):
        if self.canvas:
            self.canvas.itemconfig(self.screen_main, text=str(main).upper())
            self.canvas.itemconfig(self.screen_top, text=str(top).upper())
            if bottom is not None: self.canvas.itemconfig(self.screen_bottom, text=str(bottom).upper())

    def connect_ws_loop(self):
        while True:
            # 1. เช็คก่อนว่า Login หรือยัง ถ้ายังไม่มี ID ให้หลับรอไปก่อน
            if not self.pager_id:
                time.sleep(1)
                continue
                
            try:
                self.update_lcd(bottom="CONNECTING...")
                
                # 2. สร้าง URL ที่มี ID ที่ถูกต้อง
                current_ws_url = f"{WS_URL}?pager_id={self.pager_id}"
                
                self.ws = websocket.WebSocketApp(
                    current_ws_url, 
                    on_message=self.on_ws_msg,
                    on_open=lambda ws: self.update_lcd(bottom="SIGNAL: OK"),
                    on_error=lambda ws, e: self.update_lcd(bottom="SIGNAL: ERR"),
                    on_close=lambda ws, c, m: self.update_lcd(bottom="SIGNAL: DEAD")
                )
                
                # 3. run_forever จะ block thread นี้ไว้จนกว่าจะหลุด
                self.ws.run_forever(ping_interval=20, ping_timeout=10)
                
            except Exception as e:
                print(f"WS Thread Error: {e}")
            
            # 4. ถ้าหลุดจากข้างบน ให้รอ 5 วินาทีก่อนพยายามต่อใหม่
            self.update_lcd(bottom="RETRYING...")
            time.sleep(5)

    def on_ws_msg(self, ws, message):
        data = json.loads(message); self.history.insert(0, data); self.current_idx = 0
        self.mode = "READ"; self.update_lcd(main=data.get('body'), top=f"FROM: {data.get('from')}")

    def open_menu(self):
        self.mode = "MENU"; self.update_lcd(main="1.SEND  2.TX    3.MINE\n4.PB    5.SNAKE  6.BAL\n7.PURGE 8.TETRIS 9.RANK", top="MENU SELECT")
        self.set_input_state(True, False); self.entry_1.delete(0, tk.END); self.entry_2.delete(0, tk.END)

    def enter_action(self):
        v1, v2 = self.entry_1.get().strip(), self.entry_2.get().strip()
        
        if self.mode == "MENU":
            if v1 == "1": 
                self.mode = "SEND"; self.update_lcd("TO ID | MSG", "SEND MESSAGE"); self.set_input_state(True, True)
            elif v1 == "2": 
                self.mode = "SEND_COIN"; self.update_lcd("TO ID | AMOUNT", "TRANSFER PUK"); self.set_input_state(True, True)
            elif v1 == "3": self.start_mining()
            elif v1 == "4": self.open_pb()
            elif v1 == "5": self.start_snake()
            elif v1 == "6": self.check_bal()
            elif v1 == "8": self.start_tetris()
            elif v1 == "9": self.show_leaderboard()
            else: self.reset_ui()
            self.entry_1.delete(0, tk.END); self.entry_2.delete(0, tk.END)

        elif self.mode == "SEND":
                    if v1 and v2: 
                        # Check if ws exists and is actually connected
                        if self.ws and self.ws.sock and self.ws.sock.connected:
                            try:
                                self.ws.send(json.dumps({"to": v1, "body": v2}))
                                self.update_lcd("SENT!", "SUCCESS")
                                self.root.after(1200, self.reset_ui)
                            except Exception as e:
                                self.update_lcd("SEND FAILED", "WS ERROR")
                        else:
                            self.update_lcd("OFFLINE", "RECONNECTING...")
                            # The connect_ws_loop is already trying to reconnect,
                            # so we just notify the user.

        elif self.mode == "SEND_COIN":
            if v1 and v2.isdigit(): self.send_puk(v1, int(v2))
            else: self.update_lcd("INVALID DATA", "ERROR")

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
            res = requests.post(f"{SERVER_URL}/transfer", json={"from_id": self.pager_id, "to_id": target_id, "amount": amount}, timeout=5).json()
            if res.get("status") == "success": self.update_lcd(f"SENT {amount} PUK\nTO {target_id}", "TX COMPLETE")
            else: self.update_lcd(res.get("message", "FAILED"), "TX ERROR")
            self.root.after(2500, self.reset_ui)
        except: self.update_lcd("SERVER ERROR", "TX FAILED"); self.root.after(2000, self.reset_ui)

    def submit_score(self, score):
        try: requests.post(f"{SERVER_URL}/submit_score", json={"pager_id": self.pager_id, "score": score}, timeout=5)
        except: pass

    def show_leaderboard(self):
        try:
            res = requests.get(f"{SERVER_URL}/leaderboard", timeout=5).json()
            if res:
                board_text = "\n".join([f"{i+1}. {r['pager_id']} -> {r['score']}" for i, r in enumerate(res[:5])])
                self.update_lcd(board_text, "TOP 5 SCORES")
            else: self.update_lcd("NO DATA", "LEADERBOARD")
            self.mode = "RANK"; self.root.after(4000, self.reset_ui)
        except: self.update_lcd("CONN ERROR", "RANK")

    def delete_handler(self):
        if self.mode == "READ" and self.history:
            try:
                mid = self.history[self.current_idx].get('id')
                if mid:
                    requests.post(f"{SERVER_URL}/delete_msg", json={
                        "pager_id": self.pager_id,
                        "msg_id": mid
                    }, timeout=5)
                self.history.pop(self.current_idx)
                if self.current_idx >= len(self.history):
                    self.current_idx = max(0, len(self.history)-1)
                self.reset_ui()
            except:
                self.update_lcd("DELETE FAILED", "SERVER ERROR")

    def refresh_inbox(self):
        if self.mode != "READ":
            return
        try:
            r = requests.get(f"{SERVER_URL}/get_messages/{self.pager_id}", timeout=6)
            if r.status_code == 200:
                self.history = r.json()
                self.show_msg()
            else:
                self.update_lcd("INBOX ERROR", "SERVER")
        except:
            self.update_lcd("OFFLINE?", "CHECK NET")

    def show_msg(self):
        if not self.history:
            self.update_lcd("NO MESSAGES", "INBOX EMPTY")
            return
        m = self.history[self.current_idx]
        self.update_lcd(
            main=m.get('body', '?'),
            top=f"FROM: {m.get('from', '?')}  {self.current_idx+1}/{len(self.history)}"
        )

    def prev_msg(self):
        if self.history and self.mode == "READ":
            self.current_idx = (self.current_idx - 1) % len(self.history)
            self.show_msg()

    def next_msg(self):
        if self.history and self.mode == "READ":
            self.current_idx = (self.current_idx + 1) % len(self.history)
            self.show_msg()

    def reset_ui(self): 
        self.mining_active = False; self.mode = "READ"; self.game_running = False; self.set_input_state(False, False); self.refresh_inbox()

    # --- MINING LOGIC ---
    def start_mining(self):
        self.mode = "MINE"; self.mining_active = True; self.update_lcd("STARTING...", "MINER v1.0")
        threading.Thread(target=self.mine_worker, daemon=True).start()

    def mine_worker(self):
        try:
            lh = requests.get(f"{SERVER_URL}/get_last_hash", timeout=5).json().get("hash", "0"*64)
            n = 0
            while self.mining_active:
                h = hashlib.sha256(f"{self.pager_id}{lh}{n}".encode()).hexdigest()
                if h.startswith("000"):
                    requests.post(f"{SERVER_URL}/mine", json={"pager_id": self.pager_id, "nonce": str(n)}, timeout=5)
                    self.update_lcd("BLOCK MINED!", "SUCCESS"); time.sleep(2); break
                n += 1
                if n % 5000 == 0: 
                    self.update_lcd(f"MINING...\nNONCE: {n}", "PUK CHAIN"); time.sleep(0.01)
            self.root.after(500, self.reset_ui)
        except: self.update_lcd("CONN ERROR", "MINER"); time.sleep(2); self.reset_ui()

    def stop_mining(self): self.mining_active = False; self.reset_ui()

    # --- GAMES ---
    def start_snake(self):
        self.mode = "SNAKE"; self.game_running = True; self.snake = [(10,5),(9,5)]; self.direction = "Right"; self.spawn_food(); self.run_snake()
    def spawn_food(self): self.food = (random.randint(0,19), random.randint(0,9))
    def run_snake(self):
        if not self.game_running or self.mode != "SNAKE": return
        hx, hy = self.snake[0]
        dx, dy = {"Up":(0,-1), "Down":(0,1), "Left":(-1,0), "Right":(1,0)}[self.direction]
        nx, ny = (hx+dx)%20, (hy+dy)%10
        if (nx,ny) in self.snake: 
            sc = len(self.snake)-2; self.mode="SNAKE_OVER"; self.update_lcd(f"CRASH!\nSCORE: {sc}", "GAME OVER")
            self.submit_score(sc); return
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
            res = requests.post(f"{SERVER_URL}/login", json={"pager_id": self.pager_id, "password": ""}).json()
            self.update_lcd(f"BALANCE:\n{res.get('balance', 0)} PUK", "BANK"); self.root.after(2500, self.reset_ui)
        except: self.update_lcd("CONN ERROR", "BANK"); self.root.after(2000, self.reset_ui)

if __name__ == "__main__":
    root = tk.Tk(); app = PagerApp(root); root.mainloop()