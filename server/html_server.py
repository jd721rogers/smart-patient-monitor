from machine import Pin
import network
import socket
import time

data = {
    "patient_id": "",
    "hr":        0,
    #"spo2":        0,
    #"spo2_status": "---",
    "temp":      0,
    "fall":      False,
    "temp_flag": False,
    "activity":  0.0
}

clear_requests = {"fall": False, "temp": False}
 
def get_clear(key):
    val = clear_requests.get(key, False)
    if val:
        clear_requests[key] = False
    return val

html = """<!DOCTYPE html>
<html>
<head>
    <title>Patient Monitor</title>
    <meta http-equiv="refresh" content="3">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Courier New', Courier, monospace;
            background: #0a0f14;
            color: #e0eff8;
            padding: 28px 20px;
            min-height: 100vh;
            background-image:
                radial-gradient(ellipse at 20% 20%, rgba(0,180,255,0.05) 0%, transparent 60%),
                radial-gradient(ellipse at 80% 80%, rgba(0,255,160,0.04) 0%, transparent 60%);
        }
        header { text-align: center; margin-bottom: 32px; }
        h1 {
            font-size: 1.5rem; font-weight: 700;
            letter-spacing: 0.28em; text-transform: uppercase;
            color: #00d4ff; margin-bottom: 8px;
        }
        .patient-id { font-size: 1rem; color: #80c8e0; letter-spacing: 0.12em; }
        .section-label {
            font-size: 0.85rem; font-weight: 700;
            letter-spacing: 0.22em; text-transform: uppercase;
            color: #60a8c8; margin: 0 auto 12px auto;
            max-width: 900px;
            border-left: 3px solid #00a0c0; padding-left: 10px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px; max-width: 900px; margin: 0 auto 28px auto;
        }
        .card {
            background: #111a24; border: 1px solid #2a5a7a;
            border-radius: 8px; padding: 24px 18px 20px;
            text-align: center; position: relative; overflow: hidden;
        }
        .card::before {
            content: ''; position: absolute;
            top: 0; left: 0; right: 0; height: 3px; background: #0090c0;
        }
        .label {
            font-size: 0.8rem; font-weight: 700;
            letter-spacing: 0.16em; text-transform: uppercase;
            color: #70b8d8; margin-bottom: 14px;
        }
        .value {
            font-size: 3.4rem; font-weight: 700;
            color: #00d4ff; line-height: 1; margin-bottom: 8px;
        }
        .unit { font-size: 0.85rem; font-weight: 600; letter-spacing: 0.12em; color: #60a0c0; text-transform: uppercase; }
        .ok::before    { background: #00b050; }
        .ok .value     { color: #00ff88; }
        .ok .label     { color: #00cc66; }
        .warn::before  { background: #c08000; }
        .warn          { background: #161200; border-color: #806000; }
        .warn .value   { color: #ffd020; }
        .warn .label   { color: #d0a030; }
        .alert::before { background: #cc0000; }
        .alert         { background: #180800; border-color: #880000; }
        .alert .value  { color: #ff3030; }
        .alert .label  { color: #ff6060; }
        .bar-bg {
            background: #0a1520; border: 1px solid #2a5a7a;
            border-radius: 3px; height: 8px; margin-top: 16px; overflow: hidden;
        }
        .bar-fill {
            height: 100%; border-radius: 3px;
            background: linear-gradient(90deg, #0070a0, #00d4ff);
        }
        .btn {
            margin-top: 16px; padding: 8px 22px;
            font-family: 'Courier New', Courier, monospace;
            font-size: 0.8rem; font-weight: 700;
            letter-spacing: 0.12em; text-transform: uppercase;
            background: transparent; color: #70b8d8;
            border: 1px solid #2a7aaa; border-radius: 4px; cursor: pointer;
        }
        .btn:hover { background: #1a4a6a; color: #ffffff; }
        .timestamp {
            text-align: center; font-size: 0.75rem;
            color: #3a7a9a; margin-top: 10px; letter-spacing: 0.1em;
        }
    </style>
</head>
<body>
<header>
    <h1>Patient Monitor</h1>
    <div class="patient-id">ID: %%PATIENT_ID%%</div>
</header>
 
<div class="section-label">Vitals</div>
<div class="grid">
    <div class="card">
        <div class="label">Heart Rate</div>
        <div class="value">%%HR%%</div>
        <div class="unit">bpm</div>
    </div>
    <div class="card %%TEMPCLS%%">
        <div class="label">Temperature</div>
        <div class="value">%%TEMP%%</div>
        <div class="unit">deg F</div>
    </div>
</div>
 
<div class="section-label">Activity &amp; Alarms</div>
<div class="grid">
    <div class="card">
        <div class="label">Movement</div>
        <div class="value">%%ACTVAL%%</div>
        <div class="unit">g RMS</div>
        <div class="bar-bg"><div class="bar-fill" style="width:%%ACTPCT%%%"></div></div>
    </div>
    <div class="card %%FALLCLS%%">
        <div class="label">Fall</div>
        <div class="value">%%FALLVAL%%</div>
        <form method="POST" action="/clear_fall">
            <button class="btn" type="submit">Clear</button>
        </form>
    </div>
    <div class="card %%TFCLS%%">
        <div class="label">Temp Alarm</div>
        <div class="value">%%TFVAL%%</div>
        <form method="POST" action="/clear_temp">
            <button class="btn" type="submit">Clear</button>
        </form>
    </div>
</div>
</body>
</html>
"""

def connect_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    while wlan.status() < 3:
        time.sleep(1)
    return wlan.ifconfig()[0]

def update(new_data):
    data.update(new_data)
    
def build_page():
    act_val  = data["activity"]
    # scaling where 0.3g RMS = full bar
    act_pct  = min(int(act_val * (100/4)), 100)
    
    #spo2_status = data["spo2_status"]
    #spo2_cls    = spo2_status if spo2_status in ("ok", "warn", "alert") else ""
    #spo2_val    = str(data["spo2"]) if data["spo2"] > 0 else "---"
 
    temp_cls = "warn" if data["temp_flag"] else "ok"
    fall_cls = "alert" if data["fall"] else "ok"
    tf_cls   = "warn"  if data["temp_flag"] else "ok"
 
    page = html
    page = page.replace("%%PATIENT_ID%%",  str(data["patient_id"]))
    page = page.replace("%%HR%%",       str(data["hr"]))
    #page = page.replace("%%SPO2CLS%%",    spo2_cls)
    #page = page.replace("%%SPO2%%",       spo2_val)
    page = page.replace("%%TEMPCLS%%",  temp_cls)
    page = page.replace("%%TEMP%%",     str(round(data["temp"], 1)))
    page = page.replace("%%ACTVAL%%",   str(act_val))
    page = page.replace("%%ACTPCT%%",   str(act_pct))
    page = page.replace("%%FALLCLS%%",  fall_cls)
    page = page.replace("%%FALLVAL%%",  "ALERT" if data["fall"] else "OK")
    page = page.replace("%%TFCLS%%",    tf_cls)
    page = page.replace("%%TFVAL%%",    "ALARM" if data["temp_flag"] else "OK")
    return page

def run():
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)

    while True:
        cl, _ = s.accept()
        resp = cl.recv(1024).decode('utf-8', 'ignore')

        if 'POST /clear_fall' in resp:
            clear_requests["fall"] = True
            cl.send('HTTP/1.0 303 See Other\r\nLocation: /\r\n\r\n')
        elif 'POST /clear_temp' in resp:
            clear_requests["temp"] = True
            cl.send('HTTP/1.0 303 See Other\r\nLocation: /\r\n\r\n')
        else:
            page = build_page()
            cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
            cl.send(page)
        cl.close()