from machine import Pin
import network
import socket
import time

data = {
    "roll": 0,
    "pitch": 0,
    "hr": 0,
    "temp": 0
}

html = """<!DOCTYPE html>
<html>
<head>
    <title>Smart Patient Monitor</title>
    <meta http-equiv="refresh" content="2">
    <style>
        body { font-family: Arial; text-align: center; background-color: #f4f6f8; }
        .container { display: flex; justify-content: center; gap: 20px; margin-top: 30px; }
        .card { background: white; padding: 20px; border-radius: 10px; width: 200px; }
        .value { font-size: 24px; font-weight: bold; color: #27ae60; }
    </style>
</head>
<body>

<h1>Smart Patient Monitor</h1>

<div class="container">
    <div class="card">
        <h2>IMU Roll</h2>
        <p>Roll: <span class="value">%s deg</span></p>
    </div>
    
    <div class="card">
        <h2>IMU Pitch</h2>
        <p>Pitch: <span class="value">%s deg</span></p>
    </div>

    <div class="card">
        <h2>Pulse</h2>
        <p><span class="value">%s bpm</span></p>
    </div>

    <div class="card">
        <h2>Temp</h2>
        <p><span class="value">%s F</span></p>
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

def run():
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)

    while True:
        cl, addr = s.accept()
        cl.recv(1024)

        response = html % (
            data["roll"],
            data["pitch"],
            data["hr"],
            data["temp"]
        )

        cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        cl.send(response)
        cl.close()