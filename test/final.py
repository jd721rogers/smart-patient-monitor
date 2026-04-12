import network
import uasyncio as asyncio
import json
import math
from machine import Pin, ADC

temp_sensor = ADC(Pin(26))
pulse_sensor = ADC(Pin(27))

# thermistor calibration constants
VREF = 3.3
ADC_MAX = 65535.0
SERIES_RESISTOR_OHMS = 4700.0
BETA = 3950.0
T0_K = 298.15
R0_OHMS = 10000.0
TEMP_OFFSET_F = -5.0
THERMISTOR_TO_GND = False

vital_signs = {
    "temperature_f": 98.6,
    "pulse_raw": 0,
    "trip_detected": False 
}

# --- HTML Dashboard ---
html_page = """<!DOCTYPE html>
<html>
<head>
    <title>Health Monitor Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }
        .card { border: 1px solid #ccc; border-radius: 10px; padding: 20px; width: 300px; margin: 10px auto; box-shadow: 2px 2px 12px #aaa; }
        .val { font-size: 2em; font-weight: bold; color: #007BFF; }
        .alert { color: red; font-weight: bold; }
    </style>
</head>
<body>
    <h1>Live Vitals Dashboard</h1>
    <div class="card">
        <h3>Temperature</h3>
        <p class="val" id="temp">-- &deg;F</p>
    </div>
    <div class="card">
        <h3>Pulse (Raw)</h3>
        <p class="val" id="pulse">--</p>
    </div>
    <div class="card">
        <h3>Fall/Trip Status</h3>
        <p class="val" id="trip">--</p>
    </div>

    <script>
        // Fetch data every 500ms
        setInterval(() => {
            fetch('/data')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('temp').innerText = data.temperature_f.toFixed(1) + ' °F';
                    document.getElementById('pulse').innerText = Math.round(data.pulse_raw);
                    
                    const tripEl = document.getElementById('trip');
                    if(data.trip_detected) {
                        tripEl.innerText = "TRIP DETECTED!";
                        tripEl.className = "val alert";
                    } else {
                        tripEl.innerText = "Normal";
                        tripEl.className = "val";
                    }
                });
        }, 500);
    </script>
</body>
</html>
"""

# --- Wi-Fi & Server Logic ---
def connect_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    while not wlan.isconnected():
        pass
    print('Wi-Fi Connected. IP:', wlan.ifconfig()[0])

async def serve_client(reader, writer):
    request_line = await reader.readline()
    while await reader.readline() != b'\r\n': 
        pass # Consume headers
    
    req = request_line.decode('utf-8')
    
    # Route: JSON Data Endpoint
    if 'GET /data ' in req:
        response = json.dumps(vital_signs)
        writer.write('HTTP/1.0 200 OK\r\nContent-type: application/json\r\n\r\n')
        writer.write(response)
    # Route: Main Dashboard
    else:
        writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html; charset=utf-8\r\n\r\n')
        writer.write(html_page)

    await writer.drain()
    writer.close()
    await writer.wait_closed()

# --- Sensor Logic (Your Code) ---
def adc_to_temperature_f(adc_value):
    # convert adc -> resistance (divider) -> temperature (beta equation)
    if adc_value <= 0 or adc_value >= ADC_MAX:
        return vital_signs["temperature_f"]

    voltage = adc_value * (VREF / ADC_MAX)
    if voltage <= 0.0 or voltage >= VREF:
        return vital_signs["temperature_f"]

    if THERMISTOR_TO_GND:
        resistance = SERIES_RESISTOR_OHMS * (voltage / (VREF - voltage))
    else:
        resistance = SERIES_RESISTOR_OHMS * ((VREF - voltage) / voltage)

    try:
        temp_k = 1.0 / ((1.0 / T0_K) + (1.0 / BETA) * math.log(resistance / R0_OHMS))
    except ValueError:
        return vital_signs["temperature_f"]

    temp_celsius = temp_k - 273.15
    return (temp_celsius * 9.0 / 5.0) + 32.0 + TEMP_OFFSET_F

async def monitor_imu():
    while True:
        await asyncio.sleep(0.01) 

async def monitor_pulse():
    pulse_history = []
    while True:
        raw_pulse = pulse_sensor.read_u16()
        pulse_history.append(raw_pulse)
        if len(pulse_history) > 5:
            pulse_history.pop(0)
        vital_signs["pulse_raw"] = sum(pulse_history) / len(pulse_history)
        await asyncio.sleep(0.1) 

async def monitor_temperature():
    temp_history = []
    while True:
        raw_temp = temp_sensor.read_u16()
        temp_history.append(adc_to_temperature_f(raw_temp))
        if len(temp_history) > 5:
            temp_history.pop(0)
        vital_signs["temperature_f"] = sum(temp_history) / len(temp_history)
        await asyncio.sleep(1) 

# --- Main Event Loop ---
async def main():
    connect_wifi('UniWest504', 'jjliu2004')
    
    # Start web server non-blocking
    asyncio.create_task(asyncio.start_server(serve_client, "0.0.0.0", 80))
    
    # Start sensors
    asyncio.create_task(monitor_imu())
    asyncio.create_task(monitor_pulse())
    asyncio.create_task(monitor_temperature())
    
    # Keep running
    while True:
        await asyncio.sleep(1)

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("System stopped.")