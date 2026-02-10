import time
from machine import Pin, Timer
#
# this script uses the button & led as a indicator of patient wellbeing
# by giving the user an "OK" button by blinking an led every after 5 
# minutes of inactivity to prompt patient action to press the button. if button is pressed, 
# the led stops blinking and the timer restarts.
#
# this acknowledgement can be used with the heart rate monitor to
# determine if the patient falls asleep and turn off the light 
# until they wake up so it's not so annoying
#
button = Pin(14, Pin.IN, Pin.PULL_UP)
led = Pin(15, Pin.OUT)

last_ack = time.time()
ALERT_INTERVAL = 300  # 5 minutes

def button_pressed(pin):
    global last_ack
    last_ack = time.time()
    led.off()

button.irq(trigger=Pin.IRQ_FALLING, handler=button_pressed)

while True:
    elapsed = time.time() - last_ack

    if elapsed > ALERT_INTERVAL:
        led.toggle()
        time.sleep(0.5)   
    else:
        led.off()
        time.sleep(1)