# STM32 Battery Management System (Kalman Filter + Live Dashboard)

A lightweight embedded BMS built on an **STM32 Nucleo-L433RC-P**, estimating
State of Charge (SOC), State of Health (SOH), and Remaining Useful Life (RUL)
from voltage/current sensing, with results streamed over UART to both a PC
and an ESP32, and visualized live on a host-side Python dashboard.

## Repository Structure

```
├── firmware/
│   └── stm32_bms_kalman.ino   # STM32 firmware: sensing, Kalman filters, UART streaming
├── host/
│   ├── live_plot_simple.py    # Minimal 3-panel live plot (V / I / SOC)
│   └── dashboard_logger.py    # Fuller dashboard: V/I plot + SOC/SOH/RUL/status panel + CSV logging
├── logs/                      # CSV logs written by dashboard_logger.py (gitignored)
├── requirements.txt
└── .gitignore
```

## How it works

**Firmware (`firmware/stm32_bms_kalman.ino`)**
- Reads battery voltage (`A0`, via divider) and current (`A1`, current-sense scaling calibrated for the INA219 setup) each loop.
- Filters both with a 1D Kalman filter (`SimpleKalman`) to reduce ADC/sensor noise.
- Runs a second Kalman-style fusion between a Coulomb-counted SOC prediction and a voltage-based SOC measurement (`voltageToSoc`) to produce a stabilized SOC estimate.
- Derives SOH from cumulative SOC excursions and RUL as a fraction of a nominal cycle count.
- Streams a CSV line once per loop (~800 ms) over both USB `Serial` (to a PC) and `Serial1` (UART, to an ESP32) in the form:
  ```
  time_ms,battV_filtered,battV_raw,current_filtered,current_raw,SOC_kalman,SOC_voltage,SOH,RUL,status
  ```

**Host scripts (`host/`)**
- `live_plot_simple.py`: connects over serial and plots Voltage, Current, and SOC in three stacked live subplots. Good for a quick sanity check.
- `dashboard_logger.py`: same serial feed, but adds an SOH/RUL/status text panel and logs every sample to a timestamped CSV in `logs/`.

## Setup

1. Flash `firmware/stm32_bms_kalman.ino` to the Nucleo-L433RC-P (Arduino IDE / STM32duino core). Confirm `VOLT_SCALE`, `I_ZERO`, and `COUNTS_PER_A` against your own sensor calibration before trusting the numbers.
2. On the host PC:
   ```bash
   pip install -r requirements.txt
   ```
3. Edit `PORT` at the top of whichever host script you're using to match your STM32's serial port (e.g. `COM16` on Windows, `/dev/ttyACM0` on Linux).
4. Run:
   ```bash
   python host/dashboard_logger.py
   # or, for the simpler view:
   python host/live_plot_simple.py
   ```

## Notes / known gaps

- `VOLT_SCALE`, `I_ZERO`, and `COUNTS_PER_A` are hard-coded from a specific calibration run — re-calibrate if you change hardware.
- SOH/RUL here are simplified heuristics (cumulative-SOC-excursion based), not a full capacity-fade model — call this out if presenting it as "SOH estimation" in a report so it isn't overstated.
- The ESP32 side (receiving `Serial1` and forwarding to IoT/cloud) isn't included here — only the STM32 firmware and PC-side scripts are in this repo. Add an `esp32/` folder if/when you bring that code into the repo.
