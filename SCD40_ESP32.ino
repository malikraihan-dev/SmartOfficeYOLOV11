// SCD40 + OLED 0.96" (SSD1306, 0x3C) + MQTT Mosquitto - ESP32-S3 CAM
// Library (Arduino Library Manager):
//   1. "Sensirion I2C SCD4x"  (versi 1.x, class SensirionI2cScd4x)
//   2. "U8g2" by olikraus
//   3. "PubSubClient" by Nick O'Leary
// Tools: PSRAM OPI, Flash 16MB, partition 16M

#include <Wire.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <SensirionI2cScd4x.h>
#include <U8g2lib.h>

#define SDA_PIN 47
#define SCL_PIN 21

// ==================== KONFIGURASI WIFI & MQTT ====================
const char* WIFI_SSID     = "NAMA_WIFI_ANDA";
const char* WIFI_PASSWORD = "PASSWORD_WIFI_ANDA";

// Ganti dengan IPv4 komputer yang menjalankan Mosquitto Broker (cek pakai `ipconfig` di Windows)
const char* MQTT_BROKER   = "192.168.1.10";
const uint16_t MQTT_PORT  = 1883;
const char* MQTT_TOPIC    = "smartoffice/scd40/telemetry";

// Kosongkan ("") jika Mosquitto memakai allow_anonymous true
const char* MQTT_USER     = "";
const char* MQTT_PASS     = "";

// Opsional: samakan dengan SMARTOFFICE_DEVICE_TOKEN di backend jika diaktifkan
const char* DEVICE_TOKEN  = "";
// =================================================================

SensirionI2cScd4x scd4x;
U8G2_SSD1306_128X64_NONAME_F_HW_I2C oled(U8G2_R0, U8X8_PIN_NONE);

WiFiClient espClient;
PubSubClient mqttClient(espClient);

uint16_t co2 = 0;
float suhu = 0, lembap = 0;
bool adaData = false;
unsigned long lastReconnectAttempt = 0;

void tampilkan(const char* baris1, const char* baris2 = "", const char* baris3 = "") {
  oled.clearBuffer();
  oled.setFont(u8g2_font_6x12_tf);
  oled.drawStr(0, 14, baris1);
  oled.drawStr(0, 30, baris2);
  oled.drawStr(0, 46, baris3);
  oled.sendBuffer();
}

void hubungkanWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;

  Serial.printf("Menghubungkan ke WiFi: %s\n", WIFI_SSID);
  tampilkan("Menghubungkan WiFi", WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long mulai = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - mulai < 10000) {
    delay(300);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    String ipStr = WiFi.localIP().toString();
    Serial.printf("WiFi Terhubung! IP ESP32: %s\n", ipStr.c_str());
    tampilkan("WiFi OK", ipStr.c_str());
  } else {
    Serial.println("WiFi belum terhubung (lanjut baca sensor, coba lagi nanti).");
    tampilkan("WiFi Timeout", "Lanjut mode lokal");
  }
  delay(800);
}

bool pastikanMQTTTerhubung() {
  if (WiFi.status() != WL_CONNECTED) {
    WiFi.reconnect();
    return false;
  }
  if (mqttClient.connected()) {
    return true;
  }

  unsigned long sekarang = millis();
  if (sekarang - lastReconnectAttempt < 5000) {
    return false;
  }
  lastReconnectAttempt = sekarang;

  String clientId = "esp32s3-scd40-" + String((uint32_t)ESP.getEfuseMac(), HEX);
  Serial.printf("Menghubungkan ke MQTT %s:%u sebagai %s...\n", MQTT_BROKER, MQTT_PORT, clientId.c_str());

  bool connected = false;
  if (strlen(MQTT_USER) > 0) {
    connected = mqttClient.connect(clientId.c_str(), MQTT_USER, MQTT_PASS);
  } else {
    connected = mqttClient.connect(clientId.c_str());
  }

  if (connected) {
    Serial.println("MQTT Terhubung!");
  } else {
    Serial.printf("MQTT Gagal, rc=%d (coba lagi dalam 5 detik)\n", mqttClient.state());
  }
  return connected;
}

bool kirimKeMQTT(uint16_t nilaiCo2, float nilaiSuhu, float nilaiLembap) {
  if (!pastikanMQTTTerhubung()) {
    return false;
  }

  char payload[256];
  if (strlen(DEVICE_TOKEN) > 0) {
    snprintf(
      payload,
      sizeof(payload),
      "{\"co2_ppm\":%u,\"temperature_c\":%.1f,\"humidity_percent\":%.1f,\"source\":\"scd40\",\"device_token\":\"%s\"}",
      nilaiCo2,
      nilaiSuhu,
      nilaiLembap,
      DEVICE_TOKEN
    );
  } else {
    snprintf(
      payload,
      sizeof(payload),
      "{\"co2_ppm\":%u,\"temperature_c\":%.1f,\"humidity_percent\":%.1f,\"source\":\"scd40\"}",
      nilaiCo2,
      nilaiSuhu,
      nilaiLembap
    );
  }

  bool terkirim = mqttClient.publish(MQTT_TOPIC, payload, false);
  if (terkirim) {
    Serial.printf("[MQTT OK] %s -> %s\n", MQTT_TOPIC, payload);
  } else {
    Serial.println("[MQTT ERR] Gagal publish payload");
  }
  return terkirim;
}

void setup() {
  Serial.begin(115200);
  delay(1500);

  // Set pin dulu, supaya Wire.begin() internal U8g2 tidak balik ke pin default
  Wire.setPins(SDA_PIN, SCL_PIN);
  Wire.begin();
  Wire.setClock(100000);   // 100 kHz dulu, lebih toleran ke kabel panjang/kontak jelek

  oled.setI2CAddress(0x3C * 2);
  oled.begin();
  tampilkan("Booting...");

  scd4x.begin(Wire, SCD41_I2C_ADDR_62);   // alamat sama untuk SCD40

  // Hentikan dulu kalau sebelumnya masih jalan (setelah reset soft)
  scd4x.stopPeriodicMeasurement();
  delay(500);

  int16_t err = scd4x.startPeriodicMeasurement();
  if (err) {
    Serial.printf("startPeriodicMeasurement error: %d\n", err);
    tampilkan("SCD40 ERROR", "cek power/kabel");
  } else {
    Serial.println("SCD40 mulai. Data pertama ~5 detik.");
    tampilkan("SCD40 OK", "tunggu ~5 detik...");
  }

  hubungkanWiFi();
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setBufferSize(256);
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    pastikanMQTTTerhubung();
    mqttClient.loop();
  }

  bool ready = false;
  int16_t err = scd4x.getDataReadyStatus(ready);
  if (err) {
    Serial.printf("getDataReadyStatus error: %d\n", err);
    tampilkan("SCD40 ERROR", "baca gagal");
    delay(1000);
    return;
  }

  if (ready) {
    err = scd4x.readMeasurement(co2, suhu, lembap);
    if (!err && co2 != 0) {
      adaData = true;
      Serial.printf("CO2: %u ppm | T: %.1f C | RH: %.1f %%\n", co2, suhu, lembap);

      bool mqttSukses = kirimKeMQTT(co2, suhu, lembap);

      char b1[24], b2[24], b3[24], b4[24];
      snprintf(b1, sizeof(b1), "CO2 : %u ppm", co2);
      snprintf(b2, sizeof(b2), "Suhu: %.1f C", suhu);
      snprintf(b3, sizeof(b3), "RH  : %.1f %%", lembap);
      if (WiFi.status() != WL_CONNECTED) {
        snprintf(b4, sizeof(b4), "WiFi: DISCONNECTED");
      } else if (mqttSukses) {
        snprintf(b4, sizeof(b4), "MQTT: SENT OK");
      } else {
        snprintf(b4, sizeof(b4), "MQTT: RETRY...");
      }

      oled.clearBuffer();
      oled.setFont(u8g2_font_7x13B_tf);
      oled.drawStr(0, 14, b1);
      oled.setFont(u8g2_font_6x12_tf);
      oled.drawStr(0, 30, b2);
      oled.drawStr(0, 44, b3);
      oled.drawStr(0, 58, b4);
      oled.sendBuffer();
    } else if (err) {
      Serial.printf("readMeasurement error: %d\n", err);
    }
  }
  delay(1000);
}
