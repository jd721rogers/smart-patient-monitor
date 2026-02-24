from machine import I2C, Pin
import time

class MPU6050:
    def __init__(self, busid, SDA, SCL):
        self.PWR_MGMT_1 = 0x6B
        self.SMPLRT_DIV = 0x19
        self.CONFIG = 0x1A
        self.GYRO_CONFIG = 0x1B
        self.ACCEL_YOUT_H = 0x3B
        self.ACCEL_YOUT_H = 0x3D
        self.ACCEL_ZOUT_H = 0x3F
        self.GYRO_XOUT_H = 0x43
        self.GYRO_YOUT_H = 0x45
        self.GYRO_ZOUT_H = 0x47
        
        self.x_gyro_bias = 0
        self.y_gyro_bias = 0
        self.z_gyro_bias = 0
        self.x_accel_bias = 0
        self.y_accel_bias = 0
        self.z_accel_bias = 0
        
        self.mpu6050_addr = 0x68

        self.LED = Pin("LED", Pin.OUT)

        self.i2c = I2C(busid, sda=Pin(SDA), scl=Pin(SCL))
        self.i2c.writeto_mem(self.mpu6050_addr, self.PWR_MGMT_1, b'\x01')
        self.start = None

    def _bytes_to_signed_16bit_(self, hi, lo):
        return (((hi << 8) | lo) ^ 0x8000) - 0x8000

    def _read_raw_data_(self, addr):
        bytes = self.i2c.readfrom_mem(self.mpu6050_addr, addr, 2)
        return self._bytes_to_signed_16bit_(bytes[0], bytes[1])

    def read_acc_unbiased(self):
        return (self._read_raw_data_(0x3B)/16384, self._read_raw_data_(0x3D)/16384, self._read_raw_data_(0x3F)/16384)
    
    def read_acc(self):
        return (self._read_raw_data_(0x3B)/16384-self.x_accel_bias, self._read_raw_data_(0x3D)/16384-self.y_accel_bias, self._read_raw_data_(0x3F)/16384-self.z_accel_bias)

    def read_gyro_unbiased(self):
        return (self._read_raw_data_(0x43)/131, self._read_raw_data_(0x45)/131, self._read_raw_data_(0x47)/131)

    def read_gyro(self):
        return (self._read_raw_data_(0x43)/131-self.x_gyro_bias, self._read_raw_data_(0x45)/131-self.y_gyro_bias, self._read_raw_data_(0x47)/131-self.z_gyro_bias)

    def blink(self, t):
        for i in range(6):
            self.LED.toggle()
            time.sleep(t)
            
    def calibrate_gyro(self):
        GX_sum, GY_sum, GZ_sum = 0, 0, 0
        num_samples = 500
        for i in range(num_samples):
            g_x, g_y, g_z = self.read_gyro_unbiased()
            GX_sum += g_x
            GY_sum += g_y
            GZ_sum += g_z
        self.x_gyro_bias = GX_sum / num_samples
        self.y_gyro_bias = GY_sum / num_samples
        self.z_gyro_bias = GZ_sum / num_samples
        print("Calibrating gyroscope....\nXGB:",self.x_gyro_bias, "YGB:", self.y_gyro_bias, "ZGB:", self.z_gyro_bias, "deg\n\n")
        self.blink(0.1)
        time.sleep(2)
        
    def calibrate_accel(self):
        AX_sum, AY_sum, AZ_sum = 0, 0, 0
        num_samples = 500
        for i in range(num_samples):
            a_x, a_y, a_z = self.read_acc_unbiased()
            AX_sum += a_x
            AY_sum += a_y
            AZ_sum += (a_z - 1)
        self.x_accel_bias = AX_sum / num_samples
        self.y_accel_bias = AY_sum / num_samples
        self.z_accel_bias = AZ_sum / num_samples
        print("Calibrating accelerometer....\nXAB:",self.x_accel_bias, "YAB:", self.y_accel_bias, "ZAB:", self.z_accel_bias, "g\n\n")
        self.blink(0.1)
        time.sleep(2)
