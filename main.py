from MPU import MPU6050, ARS_EKF, FallDetector
from max30102 import MAX30102, HeartRateMonitor, SpO2Monitor
from machine import Pin, ADC, I2C
import time
import _thread
import html_server
import math

#constants
VREF = 3.3
ADC_MAX = 65535.0
SERIES_RESISTOR_OHMS = 5000.0
BETA = 3950.0
T0_K = 298.15
R0_OHMS = 10000.0
TEMP_OFFSET_F = 11.0
TEMP_LOW_F          = 96.0
TEMP_HIGH_F         = 100.4
ACTIVITY_WINDOW  = 50
PATIENT_ID            = "P-001"

# temp helper function
def adc_to_temperature_f(adc_value):
    voltage = adc_value * (VREF / ADC_MAX)
    resistance = SERIES_RESISTOR_OHMS * ((VREF - voltage) / voltage)
    temp_k = 1.0 / ((1.0 / T0_K) + (1.0 / BETA) * math.log(resistance / R0_OHMS)) 
    temp_celsius = temp_k - 273.15
    return (temp_celsius * 9.0 / 5.0) + 32.0 + TEMP_OFFSET_F
    
# init web server
ssid = 'not crying on the couch'
password = 'lemontree'
ip = html_server.connect_wifi(ssid, password)
print("IP:", ip)

# init temp sensor
thermistor = ADC(Pin(26))  # ADC0
temp_flag = False

# init i2c
i2c = I2C(0, sda=Pin(12), scl=Pin(13), freq=100000)
scl = Pin(13, Pin.OUT)
sda = Pin(12, Pin.OUT)
sda.value(1)
for _ in range(9):
    scl.value(0)
    time.sleep_ms(1)
    scl.value(1)
    time.sleep_ms(1)
# Send a STOP condition
sda.value(0)
time.sleep_ms(1)
sda.value(1)
time.sleep_ms(10)
i2c = I2C(0, sda=Pin(12), scl=Pin(13), freq=100000)
print("I2CScan:", i2c.scan())

# init IMU
obj = MPU6050(i2c)
time.sleep(2)
obj.calibrate_gyro()
obj.calibrate_accel()
grav = obj.get_gravity_vector()
_act_buf = []

# init heartrate sensor
hrm_sensor = MAX30102(i2c)
hrm = HeartRateMonitor(sample_rate=100)
#spo2_mon   = SpO2Monitor(sample_rate=100)

# start web server
_thread.start_new_thread(html_server.run, ())

# init 2D attitude ref EKF
ars = ARS_EKF(dt=0.01)
gx, gy, gz = obj.get_gravity_vector()
ars.init_from_gravity(gx, gy, gz)

# init fall detection
fall = FallDetector(dt=0.01, gravity=obj.get_gravity_vector())
fall_flag = False

dt=0.01
frame_count=0
while True:
    # imu read
    gyro_meas = obj.read_gyro()
    accel_meas = obj.read_acc()
    # EKF meas update
    ars.xP_predict(gyro_meas[0], gyro_meas[1])
    ars.meas_update(accel_meas[0], accel_meas[1], accel_meas[2])
    roll, pitch = ars.get_angles()
    # check fall detector given latest detector
    if fall.update(accel_meas[0], accel_meas[1], accel_meas[2], roll, pitch):
        fall_flag = True
        print("FALL DETECTED")
    # activity = windowed average of RMS accel readings
    lx = accel_meas[0] - grav[0]
    ly = accel_meas[1] - grav[1]
    lz = accel_meas[2] - grav[2]
    _act_buf.append(lx*lx + ly*ly + lz*lz)
    if len(_act_buf) > ACTIVITY_WINDOW:
        _act_buf.pop(0)
    activity = math.sqrt(sum(_act_buf) / len(_act_buf))
        
    # temp read
    temp_F = adc_to_temperature_f(thermistor.read_u16())
    # temp check
    if temp_F < 96 and temp_flag == False:
        temp_flag = True
        print("LOW TEMP DETECTED")
    elif temp_F > 100 and temp_flag == False:
        temp_flag = True
        print("HIGH TEMP DETECTED")
        
    # pulse monitor
    for _ in range(4):
        red, ir = hrm_sensor.read_fifo()
        if ir is not None:
            hrm.update(ir)
            #spo2_mon.update(red, ir)
    heart_rate = hrm.get_bpm()
    
    # webpage update
    if frame_count >= 99:
        # check web server for any responses
        if html_server.get_clear("fall"):
            fall_flag = False
        if html_server.get_clear("temp"):
            temp_flag = False
        html_server.update({
            "patient_id": PATIENT_ID,
            "hr": heart_rate,
            #"spo2":       spo2_mon.get_spo2(),
            #"spo2_status": spo2_mon.get_status(),
            "temp": temp_F,
            "fall":  fall_flag,
            "temp_flag": temp_flag,
            "activity":  round(activity, 3)
        })
        frame_count = 0
    else:
        frame_count+=1
        
    time.sleep(dt)
