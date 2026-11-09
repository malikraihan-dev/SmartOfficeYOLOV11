// Contoh ESP32 + SCD40 (I2C) mengirim pembacaan ke server Flask.
// Pasang library Sensirion I2C SCD4x dari Arduino Library Manager.
#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <SensirionI2CScd4x.h>

const char* WIFI_SSID = "NAMA_WIFI";
const char* WIFI_PASSWORD = "PASSWORD_WIFI";
// Ganti dengan alamat IP komputer yang menjalankan Flask, port 5000.
const char* API_URL = "http://192.168.1.10:5000/api/scd40";
SensirionI2CScd4x scd4x;
uint32_t lastSend = 0;

void setup() {
  Serial.begin(115200);
  Wire.begin(); // Umumnya SDA=21, SCL=22 pada ESP32; sesuaikan board.
  scd4x.begin(Wire);
  uint16_t error = scd4x.startPeriodicMeasurement();
  if (error) Serial.println("Gagal memulai pengukuran SCD40");

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) delay(500);
  Serial.print("ESP32 IP: "); Serial.println(WiFi.localIP());
}

void loop() {
  bool ready = false;
  uint16_t error = scd4x.getDataReadyStatus(ready);
  if (error || !ready || millis() - lastSend < 5000) {
    delay(250);
    return;
  }

  uint16_t co2 = 0;
  float temperature = 0.0f, humidity = 0.0f;
  error = scd4x.readMeasurement(co2, temperature, humidity);
  if (error || co2 == 0) return;
  lastSend = millis();

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(API_URL);
    http.addHeader("Content-Type", "application/json");
    String payload = "{\"co2_ppm\":" + String(co2) +
      ",\"temperature_c\":" + String(temperature, 1) +
      ",\"humidity_percent\":" + String(humidity, 1) + "}";
    int status = http.POST(payload);
    Serial.printf("POST SCD40 status: %d, payload: %s\n", status, payload.c_str());
    http.end();
  }
}
