from MPU import MPU6050
from machine import Pin, I2C
import time
import math

i2c = I2C(0, sda=Pin(12), scl=Pin(13), freq=10000)
obj = MPU6050(i2c)
time.sleep(2)
obj.calibrate_gyro()
obj.calibrate_accel()
grav = obj.get_gravity_vector()

print("Recording 5 seconds of accel magnitude — perform a fall/drop during this time")
print("Format: time_ms, mag_g, ax, ay, az")
time.sleep(2)
print("GO!")

start = time.ticks_ms()
log = []

while time.ticks_diff(time.ticks_ms(), start) < 5000:
    t0 = time.ticks_ms()
    ax, ay, az = obj.read_acc()
    
    # magnitude relative to gravity vector
    mag = math.sqrt(
        (ax - grav[0])**2 +
        (ay - grav[1])**2 +
        (az - grav[2])**2
    )
    elapsed = time.ticks_diff(time.ticks_ms(), start)
    log.append((elapsed, round(mag, 3), round(ax, 3), round(ay, 3), round(az, 3)))
    time.sleep_ms(10)

print("Done. Results:")
for entry in log:
    print(entry[0], entry[1], entry[2], entry[3], entry[4])

# summary
mags = [e[1] for e in log]
print("\nPeak magnitude:", max(mags), "g")
print("Min magnitude:", min(mags), "g")
print("Samples below 0.4g (free-fall threshold):", sum(1 for m in mags if m < 0.4))
print("Samples above 3.0g (impact threshold):", sum(1 for m in mags if m > 3.0))