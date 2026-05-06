from machine import I2C, Pin
import time
import math

class MPU6050:
    def __init__(self, i2c):
        self.PWR_MGMT_1 = 0x6B
        self.SMPLRT_DIV = 0x19
        self.CONFIG = 0x1A
        self.GYRO_CONFIG = 0x1B
        self.ACCEL_XOUT_H = 0x3B
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
        
        self.grav_x = 0.0
        self.grav_y = 0.0
        self.grav_z = 1.0  # default: Z-up
        
        self.mpu6050_addr = 0x68
        self.LED = Pin("LED", Pin.OUT)
        self.i2c = i2c
        time.sleep_ms(1000)
        self.i2c.writeto(self.mpu6050_addr, bytearray([self.PWR_MGMT_1, 0x00]))
        time.sleep_ms(100)
        self.i2c.writeto(self.mpu6050_addr, bytearray([self.PWR_MGMT_1, 0x01]))
        self.start = None

    def _bytes_to_signed_16bit_(self, hi, lo):
        return (((hi << 8) | lo) ^ 0x8000) - 0x8000

    def _read_raw_data_(self, addr):
        self.i2c.writeto(self.mpu6050_addr, bytearray([addr]))
        data = self.i2c.readfrom(self.mpu6050_addr, 2)
        return self._bytes_to_signed_16bit_(data[0], data[1])

    def read_acc_unbiased(self):
        return (self._read_raw_data_(self.ACCEL_XOUT_H)/16384, self._read_raw_data_(self.ACCEL_YOUT_H)/16384, self._read_raw_data_(self.ACCEL_ZOUT_H)/16384)
    
    def read_gyro_unbiased(self):
        return (self._read_raw_data_(self.GYRO_XOUT_H)/131, self._read_raw_data_(self.GYRO_YOUT_H)/131, self._read_raw_data_(self.GYRO_ZOUT_H)/131)    
    
    def read_accel_gyro(self):
        self.i2c.writeto(self.mpu6050_addr, bytearray([self.ACCEL_XOUT_H]))
        d = self.i2c.readfrom(self.mpu6050_addr, 14)
        def s16(hi, lo):
            return (((hi << 8) | lo) ^ 0x8000) - 0x8000
        ax = s16(d[0],  d[1])  / 16384 - self.x_accel_bias
        ay = s16(d[2],  d[3])  / 16384 - self.y_accel_bias
        az = s16(d[4],  d[5])  / 16384 - self.z_accel_bias
        gx = s16(d[8],  d[9])  / 131   - self.x_gyro_bias
        gy = s16(d[10], d[11]) / 131   - self.y_gyro_bias
        gz = s16(d[12], d[13]) / 131   - self.z_gyro_bias
        return (ax, ay, az), (gx, gy, gz)

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
        print("Calibrating gyroscope....\nXGB:",self.x_gyro_bias, "YGB:", self.y_gyro_bias, "ZGB:", self.z_gyro_bias, "deg\n")
        self.blink(0.1)
        time.sleep(2)
        
    def calibrate_accel(self):
        AX_sum, AY_sum, AZ_sum = 0, 0, 0
        num_samples = 500
        for i in range(num_samples):
            a_x, a_y, a_z = self.read_acc_unbiased()
            AX_sum += a_x
            AY_sum += a_y
            AZ_sum += a_z
        # measured gravity vector in sensor frame
        gx = AX_sum / num_samples
        gy = AY_sum / num_samples
        gz = AZ_sum / num_samples
        mag = math.sqrt(gx*gx + gy*gy + gz*gz)
        # normalise to unit vector
        self.grav_x = gx / mag
        self.grav_y = gy / mag
        self.grav_z = gz / mag
        # biases: difference between measured and expected gravity in each axis
        # project expected 1g onto sensor frame from the measured gravity direction
        self.x_accel_bias = gx - self.grav_x * mag
        self.y_accel_bias = gy - self.grav_y * mag
        self.z_accel_bias = gz - self.grav_z * mag
        print("Calibrating accelerometer....\nXAB:",self.x_accel_bias, "YAB:", self.y_accel_bias, "ZAB:", self.z_accel_bias, "g")
        print("\nGravity vector:", self.grav_x, self.grav_y, self.grav_z)
        print("Measured mag:  ", mag, "g\n")
        self.blink(0.1)
        time.sleep(2)
        
    def get_gravity_vector(self):
        return (self.grav_x, self.grav_y, self.grav_z)
        
    # ---------------------------------------------------------------------------
# Minimal 4x4 matrix helpers (row-major list-of-lists, no numpy)
# ---------------------------------------------------------------------------
 
def _mat_add(A, B, n):
    return [[A[i][j] + B[i][j] for j in range(n)] for i in range(n)]
 
def _mat_mul(A, B, n):
    return [[sum(A[i][k]*B[k][j] for k in range(n)) for j in range(n)] for i in range(n)]
 
def _mat_scale(A, s, n):
    return [[A[i][j]*s for j in range(n)] for i in range(n)]
 
def _eye(n):
    return [[1.0 if i==j else 0.0 for j in range(n)] for i in range(n)]
 
def _inv4(M):
    """Gauss-Jordan inverse of a 4x4 matrix."""
    A = [row[:] + [1.0 if i==j else 0.0 for j in range(4)] for i, row in enumerate(M)]
    for col in range(4):
        pivot = A[col][col]
        A[col] = [v/pivot for v in A[col]]
        for row in range(4):
            if row != col:
                f = A[row][col]
                A[row] = [A[row][k] - f*A[col][k] for k in range(8)]
    return [row[4:] for row in A]
 
def _inv2(M):
    """Analytic inverse of a 2x2 matrix."""
    a, b, c, d = M[0][0], M[0][1], M[1][0], M[1][1]
    det = a*d - b*c
    return [[d/det, -b/det], [-c/det, a/det]]
 
# ---------------------------------------------------------------------------
# EKF 2D Attitude Reference System
# ---------------------------------------------------------------------------
# State:  x = [phi, theta, b_gx, b_gy]  (roll, pitch, gyro biases) [deg, deg/s]
# Input:  u = (gx, gy, gz) corrected gyro readings [deg/s]
# Measurement: z = [phi_acc, theta_acc] from accelerometer [deg]
#
# Process model (Euler angles, small-angle approx for bias coupling):
#   phi_k+1   = phi_k   + dt*(gx - b_gx)
#   theta_k+1 = theta_k + dt*(gy - b_gy)
#   b_gx_k+1  = b_gx_k
#   b_gy_k+1  = b_gy_k
#
# Measurement model:
#   phi_acc   = atan2(ay, az)
#   theta_acc = atan2(-ax, sqrt(ay^2+az^2))
# ---------------------------------------------------------------------------
 
class ARS_EKF:
    def __init__(self, dt,
                 q_angle=0.01, q_bias=0.003,
                 r_angle=2.0):
        self.dt = dt
        # state initialization
        self.x = [0.0, 0.0, 0.0, 0.0]
        # covariance initialization
        self.P = _eye(4)
        # Process noise Q
        self.Q = [[0.0]*4 for _ in range(4)]
        self.Q[0][0] = q_angle
        self.Q[1][1] = q_angle
        self.Q[2][2] = q_bias
        self.Q[3][3] = q_bias
        print("Process Noise Q (diagonal):")
        print(self.Q[0][0],"deg")
        print(self.Q[1][1],"deg")
        print(self.Q[2][2],"deg/s")
        print(self.Q[3][3],"deg/s")
        # meas noise
        self.R = [[r_angle, 0.0], [0.0, r_angle]]
        print("Measurement Noise R (diagonal):")
        print(self.R[0][0])
        print(self.R[1][1])
 
    def init_from_gravity(self, grav_x, grav_y, grav_z):
        if grav_z >= 0:
            self.gz_sign = 1.0
        else:
            self.gz_sign = -1.0
        # seed roll/pitch from measured gravity direction to help EKF converge
        print("Initial EKF State Est from measured gravity direction...")
        self.x[0] = math.degrees(math.atan2(grav_y, grav_z))
        self.x[1] = math.degrees(math.atan2(-grav_x,
                    math.sqrt(grav_y*grav_y + grav_z*grav_z)))
        print("Phi_0",self.x[0],"deg")
        print("Theta_0",self.x[1],"deg")
        print("GyroX_Bias_0",self.x[2],"deg/s")
        print("GyroY_Bias_0",self.x[3],"deg/s")
        print("( Gyro Biases are Gaussian - Zero Mean )")
 
    def xP_predict(self, gx, gy):
        dt = self.dt
        phi, theta, b_gx, b_gy = self.x
 
        # dynamics model state propagation
        self.x[0] = phi   + dt * (gx - b_gx)
        self.x[1] = theta + dt * (gy - b_gy)
        print("State estimate at meas time using dynamics...")
        print("Phi",self.x[0],"Theta",self.x[1],"Gyro X Bias",self.x[2],"Gyro Y Bias",self.x[3])
 
        # dynamics calculation based on Jacobian
        F = _eye(4)
        F[0][2] = -dt   # d(phi)/d(b_gx)
        F[1][3] = -dt   # d(theta)/d(b_gy)
        print("Dynamics Jacobian:")
        print(F[0][0], F[0][1], F[0][2], F[0][3])
        print(F[1][0], F[1][1], F[1][2], F[1][3])
        print(F[2][0], F[2][1], F[2][2], F[2][3])
        print(F[3][0], F[3][1], F[3][2], F[3][3])
 
        # covariance propagation
        FP  = _mat_mul(F, self.P, 4)
        FPFt = _mat_mul(FP, [[F[j][i] for j in range(4)] for i in range(4)], 4)
        self.P = _mat_add(FPFt, self.Q, 4)
        print("Covariance propagation to meas time...")
 
    def meas_update(self, ax, ay, az):
        # roll and pitch measurements given ax ay az
        s = self.gz_sign
        phi_acc   = math.degrees(math.atan2(s*ay, s*az))
        theta_acc = math.degrees(math.atan2(-s*ax, math.sqrt(ay*ay + az*az)))
        z = [phi_acc, theta_acc]
 
        # meas prediction from state estimate
        h = [self.x[0], self.x[1]]
 
        # residual
        y = [z[0] - h[0], z[1] - h[1]]
        print("Measurement Residuals...")
        print("y(0)",y[0],"y(1)",y[1])
 
        # meas->state map matrix
        H = [[1.0, 0.0, 0.0, 0.0],
             [0.0, 1.0, 0.0, 0.0]]
 
        # S = H*P*Hᵀ + R  (2x2)
        # H*P rows: just rows 0 and 1 of P
       
        # meas space to state space covariance
        # H*P extracts rows 0,1 of P; (H*P)*Hᵀ then takes cols 0,1
        HP = [self.P[0][:], self.P[1][:]]
        HPHt = [[HP[i][j] for j in range(2)] for i in range(2)]
        S = [[HPHt[i][j] + self.R[i][j] for j in range(2)] for i in range(2)]
 
        # Kalman gain K = P*Hᵀ*S⁻¹  (4x2)
        # P*Hᵀ selects cols 0,1 of P (Hᵀ is [I|0]ᵀ)
        PHt   = [[self.P[i][0], self.P[i][1]] for i in range(4)]
        S_inv = _inv2(S)
        K     = [[sum(PHt[i][k]*S_inv[k][j] for k in range(2)) for j in range(2)] for i in range(4)]
 
        # state update
        print("Updating states with Kalman gain-weighted residuals...")
        for i in range(4):
            self.x[i] += K[i][0]*y[0] + K[i][1]*y[1]
            print(self.x[i])
 
        # covariance update
        KH    = [[sum(K[i][k]*H[k][j] for k in range(2)) for j in range(4)] for i in range(4)]
        I_KH  = [[(_eye(4)[i][j] - KH[i][j]) for j in range(4)] for i in range(4)]
        self.P = _mat_mul(I_KH, self.P, 4)
 
    def get_angles(self):
        return self.x[0], self.x[1]

class FallDetector:
    FREE_FALL_G  = 0.8   # g  — below this = free-fall phase
    IMPACT_G     = 1.5   # g  — above this = impact phase
    SERIOUS_IMPACT = 3.0 # g
    WINDOW_S   = 0.4   # seconds between free-fall and impact
    ANGLE_DEG   = 12.0  # min attitude change (deg) to confirm fall
 
    def __init__(self, dt, gravity=(0.0, 0.0, 1.0)):
        self._grav_x, self._grav_y, self._grav_z = gravity
        self.dt = dt
        self._ff_timer   = 0.0   # counts up during free-fall phase
        self._ff_roll    = None  # roll at free-fall onset
        self._ff_pitch   = None
        self._in_ff      = False
        self.fall_detected = False
 
    def update(self, ax, ay, az, roll, pitch):
        g = math.sqrt(self._grav_x**2 + self._grav_y**2 + self._grav_z**2)
        # rotate gravity into current body frame
        r = math.radians(roll)
        p = math.radians(pitch)
        grav_x = -math.sin(p) * g
        grav_y =  math.sin(r) * math.cos(p) * g
        grav_z =  math.cos(r) * math.cos(p) * g
        
        mag = math.sqrt(
            (ax - grav_x)**2 +
            (ay - grav_y)**2 +
            (az - grav_z)**2
        )
        self.fall_detected = False
        # print(f"[FALL] mag={mag:.3f}, in_ff={self._in_ff}, timer={self._ff_timer:.3f}")
 
        if mag > self.SERIOUS_IMPACT:
            print("IMPACT")
            self.fall_detected = True
            self._in_ff = False
        elif not self._in_ff:
            if mag < self.FREE_FALL_G:
                #print("magnitude below free fall gs")
                # free-fall onset
                self._in_ff   = True
                self._ff_timer = 0.0
                self._ff_roll  = roll
                self._ff_pitch = pitch
        else:
            self._ff_timer += self.dt
            if self._ff_timer > self.WINDOW_S:
                # timeout — no impact, reset
                self._in_ff = False
            elif mag > self.IMPACT_G:
                print("IMPACT")
                # impact detected — validate with attitude change
                d_roll  = abs(roll  - self._ff_roll)
                d_pitch = abs(pitch - self._ff_pitch)
                if d_roll > self.ANGLE_DEG or d_pitch > self.ANGLE_DEG:
                    #print("fall detected")
                    self.fall_detected = True
                self._in_ff = False
        return self.fall_detected