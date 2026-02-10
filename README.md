# smart-patient-monitor
Nurses cannot continuously monitor every patient, leaving critical events like unwitnessed falls or fever spikes undetected. To improve safety without violating privacy via cameras, this acts as a blind sensor node that tracks only physiological data (motion, heart rate, temp) to trigger alerts.



Sensors:
● MPU6050 (Accel/Gyro): Wrist-mounted. Detects fall impacts (>3g)
and tracks activity.
[(https://invensense.tdk.com/wp-content/uploads/2015/02/MPU-6000-Datasheet1.pdf) ](https://invensense.tdk.com/wp-content/uploads/2015/02/MPU-6000-Datasheet1.pdf)
● MAX30102 (Pulse/Ox): Fingertip clip. Validates distress via heart
rate/SpO2.
[(https://www.analog.com/media/en/technical-documentation/data-sheets/max30102.pdf)](https://www.analog.com/media/en/technical-documentation/data-sheets/max30102.pdf)]
● NTC Thermistor: Wrist skin contact. Monitors continuous
temperature trends.
