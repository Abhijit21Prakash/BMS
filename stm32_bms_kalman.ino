// ===============================================================
// STM32 NUCLEO-L433RC-P
// Full BMS with Kalman Filters + UART Streaming to ESP32
// Sensors: onboard ADC (voltage divider) + current sense (INA219-derived scale)
// ===============================================================

#define VOLT_PIN A0
#define CURR_PIN A1

// === IMPORTANT: declare Serial1 for NUCLEO-L433RC-P ===
// USART1 TX = PB6, RX = PB7
HardwareSerial Serial1(PB7, PB6); // (RX, TX)

// --- Calibrated constants ---
const float VOLT_SCALE    = 0.0152988f;   // V per ADC count
const long  I_ZERO        = 792L;         // zero-current ADC count
const float COUNTS_PER_A  = 145.8f;       // counts per amp (adjust if needed)

// --- Battery parameters ---
const float FULL_VOLT        = 4.20f;
const float EMPTY_VOLT       = 3.00f;
const float NOMINAL_CAP_mAh  = 2600.0f;
const float NOMINAL_RUL      = 500.0f;

// --- 1D Kalman Filter Class ---
class SimpleKalman {
  public:
    SimpleKalman(float q, float r, float p, float init_val) {
      Q = q; R = r; P = p; X = init_val;
    }
    float update(float measurement) {
      P += Q;
      float K = P / (P + R);
      X += K * (measurement - X);
      P *= (1.0f - K);
      return X;
    }
  private:
    float Q, R, P, X;
};

// --- Filters ---
SimpleKalman kalmanV(0.001f, 0.01f, 1.0f, 3.8f);
SimpleKalman kalmanI(0.01f, 0.1f, 1.0f, 0.0f);

// --- SOC Kalman ---
float soc_x = 50.0f, soc_P = 1.0f;
float soc_Q = 0.005f, soc_R = 1.0f;

// --- Helper Functions ---
inline float voltageToSoc(float v) {
  float soc = ((v - EMPTY_VOLT) / (FULL_VOLT - EMPTY_VOLT)) * 100.0f;
  if (soc < 0.0f) soc = 0.0f;
  if (soc > 100.0f) soc = 100.0f;
  return soc;
}

unsigned long lastMillis = 0;
float dt_seconds() {
  unsigned long now = millis();
  float dt = (now - lastMillis) / 1000.0f;
  lastMillis = now;
  if (dt <= 0.0f) dt = 0.001f;
  return dt;
}

void socKalmanUpdate(float soc_meas, float &x, float &P) {
  float K = P / (P + soc_R);
  x = x + K * (soc_meas - x);
  P = (1.0f - K) * P;
}

// ===============================================================
// SETUP
// ===============================================================
void setup() {
  Serial.begin(115200);     // USB serial to PC
  Serial1.begin(115200);    // UART serial to ESP32 (TX=PB6, RX=PB7 on Nucleo-L433RC-P)
  while (!Serial) {}

  lastMillis = millis();
  Serial.println("time_ms,battV_filtered,battV_raw,current_filtered,current_raw,SOC_kalman,SOC_voltage,SOH,RUL,status");

  long rawV0 = analogRead(VOLT_PIN);
  float battV0 = rawV0 * VOLT_SCALE;
  soc_x = voltageToSoc(battV0);
  soc_P = 1.0f;

  Serial.println("----- BMS initialized -----");
  Serial1.println("----- STM32 BMS streaming via UART -----");
}

// ===============================================================
// MAIN LOOP
// ===============================================================
void loop() {
  float dt = dt_seconds();
  long rawV = analogRead(VOLT_PIN);
  long rawI = analogRead(CURR_PIN);

  float battV_raw = rawV * VOLT_SCALE;
  float i_raw = (rawI - (float)I_ZERO) / COUNTS_PER_A;

  float battV_f = kalmanV.update(battV_raw);
  float i_f = kalmanI.update(i_raw);

  float capacity_Ah = NOMINAL_CAP_mAh / 1000.0f;
  float dt_hours = dt / 3600.0f;
  float deltaSOC = -(i_f * dt_hours) / capacity_Ah * 100.0f;
  float soc_pred = constrain(soc_x + deltaSOC, 0.0f, 100.0f);
  soc_P += fabs(deltaSOC) * 0.01f + soc_Q;

  float soc_meas = voltageToSoc(battV_f);
  socKalmanUpdate(soc_meas, soc_pred, soc_P);
  soc_x = soc_pred;

  static float soh = 100.0f;
  soh -= 0.00005f * (100.0f - soc_x);
  soh = constrain(soh, 50.0f, 100.0f);
  float rul = (soh / 100.0f) * NOMINAL_RUL;

  const char *status = "IDLE";
  if (i_f > 0.02f) status = "CHARGING";
  else if (i_f < -0.02f) status = "DISCHARGING";

  unsigned long tms = millis();

  // --- CSV String ---
  String csv = String(tms) + "," + String(battV_f, 4) + "," + String(battV_raw, 4) + "," +
               String(i_f, 4) + "," + String(i_raw, 4) + "," + String(soc_x, 4) + "," +
               String(soc_meas, 4) + "," + String(soh, 3) + "," + String(rul, 1) + "," + String(status);

  // Send to both PC and ESP32
  Serial.println(csv);
  Serial1.println(csv);     // <--- UART output to ESP32

  delay(800);
}
