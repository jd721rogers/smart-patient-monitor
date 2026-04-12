from MPU import MPU6050
from machine import ADC, Pin
import time
import _thread
import html_server

def adc_to_temperature_f(adc_value): 
    """Convert a 16-bit ADC reading to approximate Fahrenheit.""" 
    voltage = adc_value * (3.3 / 65535) 
    temp_celsius = (voltage + 0.075) * 100.0 
    temp_fahrenheit = (temp_celsius * 9.0 / 5.0) + 32.0 
    return temp_fahrenheit

thermistor = ADC(Pin(26))  # ADC0
obj = MPU6050(0,12,13)
obj.calibrate_gyro()  #calibrate gyro
obj.calibrate_accel() #calibrate accel - this assumes sensor is facing positive z up parallel with local gravity
time.sleep(1)

ssid = 'not crying on the couch'
password = 'lemontree'
ip = html_server.connect_wifi(ssid, password)
print("IP:", ip)

def read_imu():
    gyro_meas = obj.read_gyro()
    accel_meas = obj.read_acc()
    return gyro_meas, accel_meas

def read_temp():
    return thermistor.read_u16()

_thread.start_new_thread(html_server.run, ())

t=0
dt=0.005
while True:
    gyro_meas, accel_meas = read_imu()
    raw = read_temp()
    temp_F = adc_to_temperature_f(raw)
    heart_rate = 75  #temp

    html_server.update({
        "ax": accel_meas[0],
        "ay": accel_meas[1],
        "az": accel_meas[2],
        "wx": gyro_meas[0],
        "wy": gyro_meas[1],
        "wz": gyro_meas[2],
        "hr": heart_rate,
        "temp": temp_F
    })

    time.sleep(dt)

