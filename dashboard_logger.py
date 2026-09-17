"""
dashboard_logger.py
====================
Live dashboard (Voltage/Current plot + text panel of SOC/SOH/RUL/status)
with CSV logging, for the STM32 BMS firmware
(see firmware/stm32_bms_kalman.ino).

Usage:
    python dashboard_logger.py
Adjust the USER SETTINGS block below to match your setup.
Logs are written to logs/bms_log_<timestamp>.csv
"""

import serial
import time
import csv
import os
from matplotlib import pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque
from datetime import datetime

# ================= USER SETTINGS =================
PORT = "COM16"      # change to your STM32 port
BAUD = 115200
MAX_POINTS = 200    # number of points visible in the plots
SAVE_LOG = True     # enable CSV logging
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
# =================================================

# Create log file
log_filename = None
csv_writer = None
log_file = None
if SAVE_LOG:
    os.makedirs(LOG_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(LOG_DIR, f"bms_log_{timestamp}.csv")
    log_file = open(log_filename, "w", newline="")
    csv_writer = csv.writer(log_file)
    csv_writer.writerow(["time_s", "voltage", "current", "soc", "soh", "rul", "status"])

# Serial setup
print(f"Connecting to {PORT} ...")
ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)
print(f"Connected to {PORT}")

# Data buffers
times, volts, currents, socs = deque(maxlen=MAX_POINTS), deque(maxlen=MAX_POINTS), deque(maxlen=MAX_POINTS), deque(maxlen=MAX_POINTS)
sohs, ruls = deque(maxlen=MAX_POINTS), deque(maxlen=MAX_POINTS)
status_text = "IDLE"

# Matplotlib setup (two columns: plots + value display)
fig, (ax_plot, ax_text) = plt.subplots(1, 2, figsize=(10, 6), gridspec_kw={'width_ratios': [3, 1]})
plt.subplots_adjust(left=0.08, right=0.95, wspace=0.3)
ax_plot2 = ax_plot.twinx()  # overlay voltage & current

# Text panel
ax_text.axis("off")
text_display = ax_text.text(0.0, 0.9, "", fontsize=12, va='top', family="monospace")


def update(frame):
    global status_text
    line = ser.readline().decode(errors='ignore').strip()
    if not line or not line[0].isdigit():
        return

    parts = line.split(',')
    if len(parts) < 10:
        return

    try:
        t = int(parts[0]) / 1000.0
        v = float(parts[1])
        i = float(parts[3])
        soc = float(parts[5])
        soh = float(parts[7])
        rul = float(parts[8])
        status_text = parts[9]
    except Exception:
        return

    # Append data
    times.append(t)
    volts.append(v)
    currents.append(i)
    socs.append(soc)
    sohs.append(soh)
    ruls.append(rul)

    # Log to CSV
    if SAVE_LOG and csv_writer:
        csv_writer.writerow([t, v, i, soc, soh, rul, status_text])
        log_file.flush()

    # Update plots
    ax_plot.clear()
    ax_plot2.clear()

    ax_plot.plot(times, volts, color='tab:red', label='Voltage (V)')
    ax_plot2.plot(times, currents, color='tab:blue', label='Current (A)')
    ax_plot.set_xlabel("Time (s)")
    ax_plot.set_ylabel("Voltage (V)", color='tab:red')
    ax_plot2.set_ylabel("Current (A)", color='tab:blue')
    ax_plot.grid(True)

    # Right-hand text display
    summary = (
        f"Battery Dashboard\n"
        f"----------------------\n"
        f"Voltage : {v:6.3f} V\n"
        f"Current : {i:6.3f} A\n"
        f"SOC     : {soc:6.2f} %\n"
        f"SOH     : {soh:6.2f} %\n"
        f"RUL     : {rul:6.1f} cycles\n"
        f"Status  : {status_text}\n"
    )
    ax_text.clear()
    ax_text.axis("off")
    ax_text.text(0.0, 0.9, summary, fontsize=12, va='top', family="monospace")


ani = FuncAnimation(fig, update, interval=300)


def on_close(event):
    print("\nExiting...")
    ser.close()
    if SAVE_LOG and log_file:
        log_file.close()
    plt.close('all')


fig.canvas.mpl_connect("close_event", on_close)
plt.show()
