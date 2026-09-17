"""
live_plot_simple.py
====================
Minimal live plot of Voltage / Current / SOC streamed over UART/USB
from the STM32 BMS firmware (see firmware/stm32_bms_kalman.ino).

Usage:
    python live_plot_simple.py
Adjust PORT / BAUD below to match your setup.
"""

import serial
import time
import matplotlib.pyplot as plt
from collections import deque

PORT = "COM16"  # change to your STM32 port
BAUD = 115200

ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)
print("Connected to", PORT)

# live plot buffers
times, volts, currents, socs = deque(maxlen=100), deque(maxlen=100), deque(maxlen=100), deque(maxlen=100)
plt.ion()
fig, ax = plt.subplots(3, 1, figsize=(8, 8), sharex=True)
ax[0].set_ylabel("Voltage (V)")
ax[1].set_ylabel("Current (A)")
ax[2].set_ylabel("SOC (%)")
ax[2].set_xlabel("Time (s)")

while True:
    try:
        line = ser.readline().decode(errors='ignore').strip()
        if not line or not line[0].isdigit():  # skip summaries
            continue
        parts = line.split(',')
        if len(parts) < 10:
            continue
        t = int(parts[0]) / 1000.0
        v = float(parts[1])
        i = float(parts[3])
        soc = float(parts[5])

        times.append(t); volts.append(v); currents.append(i); socs.append(soc)

        for a in ax:
            a.clear()
        ax[0].plot(times, volts, label='Voltage')
        ax[1].plot(times, currents, label='Current')
        ax[2].plot(times, socs, label='SOC', color='g')
        for a in ax:
            a.legend()
            a.grid(True)
        plt.pause(0.1)

    except KeyboardInterrupt:
        print("Exiting...")
        ser.close()
        break
