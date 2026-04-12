from MPU import MPU6050
from machine import ADC, Pin
import uasyncio as asyncio

def adc_to_temperature_f(adc_value): 
    """Convert a 16-bit ADC reading to approximate Fahrenheit.""" 
    voltage = adc_value * (3.3 / 65535) 
    temp_celsius = (voltage + 0.075) * 100.0 
    temp_fahrenheit = (temp_celsius * 9.0 / 5.0) + 32.0 
    return temp_fahrenheit

thermistor = ADC(Pin(26))  # ADC0
obj = MPU6050(0,12,13)
obj.calibrate_gyro()  #calibrate gyro
obj.calibrate_accel() #calibrate accel - this assumes sensor is facing positive z facing local gravity

async def read_imu():
    while True:
        gyro_meas = obj.read_gyro()
        accel_meas = obj.read_acc()
        print("GyroX: ", gyro_meas[0], " GyroY: ", gyro_meas[1], " GyroZ: ", gyro_meas[2])
        print("AccX: ", accel_meas[0], " AccY: ", accel_meas[1], " AccZ: ", accel_meas[2])
        
        await asyncio.sleep(0.05)

async def read_temp():
    while True:    
        raw = thermistor.read_u16()
        temp_F = adc_to_temperature_f(raw)
        print("Temp: ", temp_F)

        await asyncio.sleep(0.1)

async def main():
    asyncio.create_task(read_imu())
    asyncio.create_task(read_temp())

    while True:
        print("\n1 sec tick...\n")
        await asyncio.sleep(1)
  
asyncio.run(main())
