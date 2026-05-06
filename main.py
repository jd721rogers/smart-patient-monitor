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
TEMP_OFFSET_F = 9.0
TEMP_LOW_F          = 96.0
TEMP_HIGH_F         = 100.4
ACTIVITY_WINDOW  = 50
LOOP_MS = 40
PATIENT_ID            = "P-001"

# setup led
led = Pin("LED", Pin.OUT)

# timer helper functions
def tic():
    global _start_time
    _start_time = time.ticks_ms()

def toc():
    elapsed = time.ticks_diff(time.ticks_ms(), _start_time)
    print(f"Elapsed time: {elapsed} ms")
    return elapsed

# temp helper function
def adc_to_temperature_f(adc_value):
    if adc_value == 0:
        return 0.0
    voltage = adc_value * (VREF / ADC_MAX)
    if voltage <= 0 or voltage >= VREF:
        return 0.0
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
i2c = I2C(0, sda=Pin(12), scl=Pin(13), freq=400000)
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
print("\nI2CScan Bus IDs:", i2c.scan())

led.on()
# init IMU
obj = MPU6050(i2c)
time.sleep(2)
print("\naligning.... PLEASE KEEP STILL!!!\n")
i = 0
for i in range(3):
    led.toggle()
    time.sleep(0.2)
obj.calibrate_gyro()
obj.calibrate_accel()
_act_buf = []
for i in range(3):
    led.toggle()
    time.sleep(0.2)
led.off()

# init heartrate sensor
hrm_sensor = MAX30102(i2c)
hrm = HeartRateMonitor(sample_rate=25)

# start web server
_thread.start_new_thread(html_server.run, ())

# init 2D attitude ref EKF
ars = ARS_EKF(dt=LOOP_MS/1000.0)
g = 1.0
gx, gy, gz = obj.get_gravity_vector()
ars.init_from_gravity(gx, gy, gz)
gz_sign = ars.gz_sign

# init fall detection
fall = FallDetector(dt=LOOP_MS/1000.0, gravity=obj.get_gravity_vector())
fall_flag = False

frame_count=0
stale_count = 0
while True:
    _loop_start = time.ticks_ms()
        
    # imu read
    accel_meas, gyro_meas = obj.read_accel_gyro()
    
    # EKF meas update
    ars.xP_predict(gyro_meas[0], gyro_meas[1])
    ars.meas_update(accel_meas[0], accel_meas[1], accel_meas[2])
    roll_deg, pitch_deg = ars.get_angles()
    print(roll_deg, pitch_deg)
    roll_rad  = math.radians(roll_deg)
    pitch_rad = math.radians(pitch_deg)
    cos_phi, sin_phi = math.cos(roll_rad),  math.sin(roll_rad)
    cos_theta, sin_theta = math.cos(pitch_rad), math.sin(pitch_rad)
    
    # check fall detector given latest detector
    if fall.update(accel_meas[0], accel_meas[1], accel_meas[2], roll_deg, pitch_deg):
        fall_flag = True
        print("FALL DETECTED")
        
    print(f"{fall._ff_timer:.3f},{roll_deg:.1f},{pitch_deg:.1f},{fall.fall_detected}")
        
    # activity = windowed average of RMS accel readings
    # first, get gravity vector in IMU coordinates based on
    grav_x = -sin_theta * g
    grav_y =  sin_phi * cos_theta * g
    grav_z =  cos_phi * cos_theta * g
    lx = accel_meas[0] + grav_x
    ly = accel_meas[1] + grav_y
    lz = accel_meas[2] + grav_z
    #print("accel:", accel_meas)
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
    red, ir = hrm_sensor.read_fifo()
    #print(f"[FIFO] red={red}, ir={ir}")
    if ir is not None and ir > 5000:
        #print(ir)
        hrm.update(ir)
        
    heart_rate = hrm.get_bpm()
    #print("heart rate:",heart_rate," bpm")
    
    # webpage update
    if frame_count >= 33:
        # check web server for any responses
        if html_server.get_clear("fall"):
            fall_flag = False
        if html_server.get_clear("temp"):
            temp_flag = False
        led.toggle()
        html_server.update({
            "patient_id": PATIENT_ID,
            "hr": heart_rate,
            "temp": temp_F,
            "fall":  fall_flag,
            "temp_flag": temp_flag,
            "activity":  round(activity, 2)
        })
        frame_count = 0
    else:
        frame_count+=1
    
    elapsed = time.ticks_diff(time.ticks_ms(), _loop_start)
    remaining = LOOP_MS - elapsed
    if remaining > 0:
        time.sleep_ms(remaining)
