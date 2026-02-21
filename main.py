from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
import asyncio
import time
import json

app = FastAPI()

# สถิติสำหรับหน้า Monitor
attack_logs = []
TARGET_IP = "1.46.136.140"

@app.middleware("http")
async def security_monitor(request: Request, call_next):
    real_ip = request.headers.get("CF-Connecting-IP") or request.client.host
    path = request.url.path
    
    # บันทึก Log การเข้าถึง
    log_entry = {
        "ip": real_ip,
        "method": request.method,
        "path": path,
        "time": time.strftime("%H:%M:%S"),
        "status": "ALLOWED"
    }

    # กลไกดัดหลัง (Counter-Attack)
    if real_ip == TARGET_IP:
        log_entry["status"] = "TRAPPED (TARPIT)"
        attack_logs.append(log_entry)
        
        # ขังไว้ 60 วินาที ให้สคริปต์คนยิงค้าง
        await asyncio.sleep(60)
        
        # ระเบิด Buffer ขยะกลับไป 5MB
        garbage = "ARE_YOU_BORED?" * 500000
        return Response(content=garbage, media_type="text/plain")

    attack_logs.append(log_entry)
    # เก็บ Log แค่ 50 รายการล่าสุด
    if len(attack_logs) > 50: attack_logs.pop(0)
    
    return await call_next(request)

# หน้า Monitor สำหรับคุณ (เข้าที่ /admin/monitor)
@app.get("/admin/monitor", response_class=HTMLResponse)
async def monitor_page():
    return """
    <html>
        <head>
            <title>Pukmupee Security Monitor</title>
            <script src="https://cdn.tailwindcss.com"></script>
            <meta http-equiv="refresh" content="3">
        </head>
        <body class="bg-slate-900 text-white p-8">
            <h1 class="text-3xl font-bold mb-6 text-red-500">🛡️ Intrusion Monitor</h1>
            <div class="bg-slate-800 rounded-lg p-6 shadow-xl">
                <table class="w-full text-left">
                    <thead>
                        <tr class="border-b border-slate-700 text-slate-400">
                            <th class="p-2">Time</th><th class="p-2">IP Address</th>
                            <th class="p-2">Path</th><th class="p-2">Status</th>
                        </tr>
                    </thead>
                    <tbody id="log-table">
                        """ + "".join([f"<tr class='border-b border-slate-700 {"bg-red-900/30" if l['ip'] == TARGET_IP else ""}'>"
                                       f"<td class='p-2'>{l['time']}</td>"
                                       f"<td class='p-2'>{l['ip']}</td>"
                                       f"<td class='p-2'>{l['path']}</td>"
                                       f"<td class='p-2 font-bold'>{l['status']}</td></tr>" for l in reversed(attack_logs)]) + """
                    </tbody>
                </table>
            </div>
        </body>
    </html>
    """