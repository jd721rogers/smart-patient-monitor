# MAX30102 I2C pulse oximeter driver for MicroPython
# Address: 0x57  — shares bus with MPU6050 (0x68)

from machine import I2C, Pin
import time

_ADDR          = 0x57
_REG_INTR_STATUS_1 = 0x00
_REG_INTR_ENABLE_1 = 0x02
_REG_FIFO_WR_PTR   = 0x04
_REG_OVF_COUNTER   = 0x05
_REG_FIFO_RD_PTR   = 0x06
_REG_FIFO_DATA     = 0x07
_REG_FIFO_CONFIG   = 0x08
_REG_MODE_CONFIG   = 0x09
_REG_SPO2_CONFIG   = 0x0A
_REG_LED1_PA       = 0x0C   # Red LED
_REG_LED2_PA       = 0x0D   # IR  LED
_REG_PART_ID       = 0xFF
_DC_MIN = 5000

class MAX30102:
    def __init__(self, i2c):
        self.i2c = i2c
        self._buf = bytearray(6)
        self._reset()
        self._setup()

    def _wr(self, reg, val):
        self.i2c.writeto(_ADDR, bytearray([reg, val]))

    def _rd(self, reg, n=1):
        self.i2c.writeto(_ADDR, bytearray([reg]))
        return self.i2c.readfrom(_ADDR, n)

    def _reset(self):
        self._wr(_REG_MODE_CONFIG, 0x40)   # RESET bit
        time.sleep_ms(500)

    def _setup(self):
        self._wr(_REG_INTR_ENABLE_1, 0xC0) # FIFO almost full + new data ready
        self._wr(_REG_FIFO_WR_PTR,   0x00)
        self._wr(_REG_OVF_COUNTER,   0x00)
        self._wr(_REG_FIFO_RD_PTR,   0x00)
        self._wr(_REG_FIFO_CONFIG,   0x4F) # SMP_AVE=4, FIFO_ROLLOVER, FIFO_A_FULL=15
        self._wr(_REG_MODE_CONFIG,   0x03) # SpO2 mode (Red + IR)
        self._wr(_REG_SPO2_CONFIG,   0x27) # ADC 4096nA, SR 100Hz, 411us pulse
        self._wr(_REG_LED1_PA,       0x24) # Red ~7.2mA
        self._wr(_REG_LED2_PA,       0x24) # IR  ~7.2mA

    def read_fifo(self):
        """Returns (red, ir) raw 18-bit sample or (None, None) if no data."""
        wr = self._rd(_REG_FIFO_WR_PTR)[0]
        rd = self._rd(_REG_FIFO_RD_PTR)[0]
        if wr == rd:
            return None, None
        data = self._rd(_REG_FIFO_DATA, 6)
        red = ((data[0] & 0x03) << 16 | data[1] << 8 | data[2])
        ir  = ((data[3] & 0x03) << 16 | data[4] << 8 | data[5])
        return red, ir


class HeartRateMonitor:
    
    BPM_MIN = 30
    BPM_MAX = 220
    _DC_ALPHA = 0.995
    _WARMUP_SAMPLES = 500
    _REFRACTORY  = 0.3
    
    def __init__(self, sample_rate=100, history=10):
        self.fs     = sample_rate
        self._dc    = 0.0
        self._prev  = 0.0
        self._intervals = []   # samples between beats
        self._since_beat = 0
        self._max_interval = history  # max beats kept
        self._sample_count = 0

    def update(self, ir_raw):
        if ir_raw is None:
            return
        
        self._dc = self._DC_ALPHA * self._dc + (1 - self._DC_ALPHA) * ir_raw
        ac       = ir_raw - self._dc
        if self._dc < _DC_MIN:
            self._prev = 0.0  # reset so we don't get a spurious crossing on return
            self._sample_count = 0
            return
        
        self._sample_count += 1
        self._since_beat += 1
        
        if self._sample_count < self._WARMUP_SAMPLES:
            self._prev = ac
            return
        
        refractory_samples = int(self.fs * self._REFRACTORY)
        # rising zero-crossing = heartbeat
        if self._prev < 0 and ac >= 0 and self._since_beat > refractory_samples:
            bpm = 60.0 * self.fs / self._since_beat
            if self.BPM_MIN <= bpm <= self.BPM_MAX:
                self._intervals.append(self._since_beat)
                if len(self._intervals) > self._max_interval:
                    self._intervals.pop(0)
            self._since_beat = 0
            
        self._prev = ac

    def get_bpm(self):
        if not self._intervals:
            return 0
        avg_samples = sum(self._intervals) / len(self._intervals)
        return round(60.0 * self.fs / avg_samples)
    
class SpO2Monitor:
    SPO2_ALERT = 94
    SPO2_WARN  = 97
    R_MIN = 0.5
    R_MAX = 1.0
 
    def __init__(self, sample_rate=100, history=10):
        self.fs       = sample_rate
        # DC trackers (slow IIR)
        self._dc_ir   = 0.0
        self._dc_red  = 0.0
        # AC trackers (fast IIR for peak estimation)
        self._ac_ir   = 0.0
        self._ac_red  = 0.0
        self._spo2_buf = []
        self._max_buf  = history
 
    def update(self, red_raw, ir_raw):
        if red_raw is None or ir_raw is None:
            return
        dc_alpha = 0.995   # slow — tracks DC baseline
        ac_alpha = 0.90   # faster — tracks AC envelope
 
        self._dc_ir  = dc_alpha * self._dc_ir  + (1 - dc_alpha) * ir_raw
        self._dc_red = dc_alpha * self._dc_red + (1 - dc_alpha) * red_raw
 
        if self._dc_ir < _DC_MIN or self._dc_red < _DC_MIN:
            return
 
        ac_ir  = abs(ir_raw  - self._dc_ir)
        ac_red = abs(red_raw - self._dc_red)
 
        self._ac_ir  = ac_alpha * self._ac_ir  + (1 - ac_alpha) * ac_ir
        self._ac_red = ac_alpha * self._ac_red + (1 - ac_alpha) * ac_red
 
        if self._dc_ir < 1000 or self._dc_red < 1000:
            return  # no finger on sensor
 
        if self._ac_ir < 10:
            return  # no pulsatile signal
 
        R = (self._ac_red / self._dc_red) / (self._ac_ir / self._dc_ir)
        if not (self.R_MIN <= R <= self.R_MAX):
            return
        
        spo2 = max(0.0, min(100.0, 110.0 - 25.0 * R))
        self._spo2_buf.append(spo2)
        if len(self._spo2_buf) > self._max_buf:
            self._spo2_buf.pop(0)
 
    def get_spo2(self):
        if not self._spo2_buf:
            return 0
        return round(sum(self._spo2_buf) / len(self._spo2_buf), 1)
 
    def get_status(self):
        spo2 = self.get_spo2()
        if spo2 == 0:
            return "---"
        if spo2 < self.SPO2_ALERT:
            return "alert"
        if spo2 < self.SPO2_WARN:
            return "warn"
        return "ok"