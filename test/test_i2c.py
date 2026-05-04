from machine import I2C, Pin

i2c = I2C(1, scl=Pin(11), sda=Pin(10))
print("Scan:", i2c.scan())