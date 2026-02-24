from MPU import MPU6050
import time

obj = MPU6050(0,12,13)
obj.calibrate_gyro()  #calibrate gyro
obj.calibrate_accel() #calibrate accel - this assumes sensor is facing positive z facing local gravity
time.sleep(1)

# open csv
fname = "mpu6050_calibrated.csv"
f = open(fname, "w")
# write header
f.write("Time,Gyro Meas X,Gyro Meas Y,Gyro Meas Z,Acc Meas X,Acc Meas Y,Acc Meas Z\n")

t=0
dt=0.02
while True:
  gyro_meas = obj.read_gyro()
  accel_meas = obj.read_acc()
  
  #print("GyroX: ", gyro_meas[0], " GyroY: ", gyro_meas[1], " GyroZ: ", gyro_meas[2])
  print("AccX: ", accel_meas[0], " AccY: ", accel_meas[1], " AccZ: ", accel_meas[2])
  
  # write to csv
  f.write("{:.2f},{:.5f},{:.5f},{:.5f},{:.5f},{:.5f},{:.5f}\n".format(t, gyro_meas[0], gyro_meas[1], gyro_meas[2], accel_meas[0], accel_meas[1], accel_meas[2]))
  f.flush()
  
  t+=dt
  time.sleep(dt) 