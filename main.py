from MPU import MPU6050, ARS_EKF
from machine import ADC, Pin
import time
import _thread
import html_server
import math

VREF = 3.3
ADC_MAX = 65535.0
SERIES_RESISTOR_OHMS = 5000.0
BETA = 3950.0
T0_K = 298.15
R0_OHMS = 10000.0
TEMP_OFFSET_F = 0.0
THERMISTOR_TO_GND = False

def adc_to_temperature_f(adc_value):
    voltage = adc_value * (VREF / ADC_MAX)
    resistance = SERIES_RESISTOR_OHMS * ((VREF - voltage) / voltage)
    temp_k = 1.0 / ((1.0 / T0_K) + (1.0 / BETA) * math.log(resistance / R0_OHMS)) 
    temp_celsius = temp_k - 273.15
    return (temp_celsius * 9.0 / 5.0) + 32.0 + TEMP_OFFSET_F


thermistor = ADC(Pin(26))  # ADC0
pulse_sensor = ADC(Pin(27))
obj = MPU6050(0,12,13)
time.sleep(2)
obj.calibrate_gyro()  #calibrate gyro
obj.calibrate_accel() #calibrate accel - this assumes sensor is facing positive z up parallel with local gravity

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

def read_pulse():
    raw_pulse = pulse_sensor.read_u16()
    return raw_pulse

_thread.start_new_thread(html_server.run, ())

# init 2D attitude ref EKF
ars = ARS_EKF(dt=0.01)

alpha = 0.75
old_pulse = 0.0

t=0
dt=0.01
frame_count=0
while True:
    # imu read
    gyro_meas, accel_meas = read_imu()
    ars.xP_predict(gyro_meas[0], gyro_meas[1])
    ars.meas_update(accel_meas[0], accel_meas[1], accel_meas[2])
    # temp read
    temp_F = adc_to_temperature_f(read_temp())
    # pulse monitor
    raw = read_pulse()
    heart_rate = alpha * old_pulse + (1 - alpha) * raw
    old_pulse = heart_rate
    # EKF and webpage update
    if frame_count > 99:
        roll, pitch = ars.get_angles()
        html_server.update({
            "roll": roll,
            "pitch": pitch,
            "hr": heart_rate,
            "temp": temp_F})
        frame_count = 0
    else:
        frame_count+=1
    time.sleep(dt)

