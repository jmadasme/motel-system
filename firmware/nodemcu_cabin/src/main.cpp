/*
 * Firmware NodeMCU ESP8266 - cerradura de cabana / barrera de motel
 * ==================================================================
 *  Este sketch corre en la placa instalada en cada cabana (o en la
 *  barrera). Expone un mini servidor HTTP en el puerto 80:
 *
 *    GET /unlock?ms=1000&r=<nonce>
 *        Orden de apertura enviada por el SERVIDOR CENTRAL por WiFi.
 *        Requiere headers X-Timestamp y X-Signature:
 *            firma = HMAC-SHA256(DEVICE_KEY, "<ts>:<ms>:<r>")
 *        Sin firma valida o con firma repetida (replay) responde 401.
 *        Enciende el rele durante "ms" (200..15000, default 1000).
 *
 *    GET /status
 *        JSON con estado de la placa (diagnostico).
 *
 *  BOTON INTERIOR (salida de emergencia):
 *        Abre el rele 5 segundos SIN pedir autorizacion (seguridad).
 *        Ademas avisa al servidor (evento "exit_button").
 *
 *  La placa manda un heartbeat al servidor cada 30 s para que el panel
 *  muestre si esta en linea.
 */

#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ESP8266mDNS.h>
#include <bearssl/bearssl_hmac.h>

#include "config.h"

#define FW_VERSION "1.0.0"

ESP8266WebServer server(80);

// ---------------------------------------------------------------- estado
bool relayOn = false;
unsigned long relayOffAt = 0;
String lastReason = "-";

static const int REPLAY_N = 16;
String replayRing[REPLAY_N];
int replayIdx = 0;

unsigned long lastHeartbeat = 0;
unsigned long lastBlink = 0;
unsigned long lastWifiTry = 0;
bool ledState = false;

// ---------------------------------------------------------------- crypto
String hmacSha256Hex(const String &key, const String &msg) {
  unsigned char mac[32];
  br_hmac_key_context kc;
  br_hmac_context hc;
  br_hmac_key_init(&kc, &br_sha256_vtable, key.c_str(), key.length());
  br_hmac_init(&hc, &kc, 0);
  br_hmac_update(&hc, msg.c_str(), msg.length());
  br_hmac_out(&hc, mac);
  static const char *hexd = "0123456789abcdef";
  char out[65];
  for (int i = 0; i < 32; i++) {
    out[i * 2] = hexd[mac[i] >> 4];
    out[i * 2 + 1] = hexd[mac[i] & 0x0F];
  }
  out[64] = 0;
  return String(out);
}

bool constantTimeEq(const String &a, const String &b) {
  if (a.length() != b.length()) return false;
  uint8_t diff = 0;
  for (size_t i = 0; i < a.length(); i++) diff |= (uint8_t)(a[i] ^ b[i]);
  return diff == 0;
}

// ---------------------------------------------------------------- rele
void relaySet(bool on) {
  relayOn = on;
  digitalWrite(RELAY_PIN,
               RELAY_ACTIVE_LOW ? (on ? LOW : HIGH) : (on ? HIGH : LOW));
}

void relayPulse(unsigned long ms, const String &reason) {
  relaySet(true);
  relayOffAt = millis() + ms;
  lastReason = reason;
  Serial.printf("[RELE] ON %lums (%s)\n", ms, reason.c_str());
}

bool seenBefore(const String &canonical) {
  for (int i = 0; i < REPLAY_N; i++)
    if (replayRing[i] == canonical) return true;
  replayRing[replayIdx] = canonical;
  replayIdx = (replayIdx + 1) % REPLAY_N;
  return false;
}

// ---------------------------------------------------------------- red
void postSigned(const String &path, const String &canonical,
                const String &body) {
  WiFiClient client;
  client.setTimeout(1500);
  if (!client.connect(SERVER_HOST, SERVER_PORT)) {
    Serial.println("[NET] sin conexion con el servidor");
    return;
  }
  String req = String("POST ") + path + " HTTP/1.1\r\n" +
               "Host: " + SERVER_HOST + ":" + String(SERVER_PORT) + "\r\n" +
               "Content-Type: application/json\r\n" +
               "X-Signature: " + hmacSha256Hex(DEVICE_KEY, canonical) + "\r\n" +
               "Connection: close\r\n" +
               "Content-Length: " + String(body.length()) + "\r\n\r\n" + body;
  client.print(req);
  unsigned long t0 = millis();
  while (client.connected() && millis() - t0 < 1500) {
    while (client.available()) client.read();
    delay(5);
  }
  client.stop();
}

void notifyEvent(const char *event, long ms) {
  String n = String(millis());
  String body = String("{\"device_id\":\"") + DEVICE_ID + "\",\"event\":\"" +
                event + "\",\"ms\":" + String(ms) + ",\"n\":" + n + "}";
  String canonical = String(DEVICE_ID ":event:") + event + ":" + n;
  postSigned("/api/devices/event", canonical, body);
  Serial.printf("[NET] evento %s enviado\n", event);
}

void heartbeat() {
  String body = String("{\"device_id\":\"") + DEVICE_ID +
                "\",\"status\":\"online\",\"fw\":\"" FW_VERSION "\",\"ip\":\"" +
                WiFi.localIP().toString() + "\",\"uptime\":" +
                String(millis() / 1000) + "}";
  String canonical = String(DEVICE_ID ":heartbeat");
  postSigned("/api/devices/heartbeat", canonical, body);
}

// ---------------------------------------------------------------- HTTP
void handleUnlock() {
  String ts = server.header("X-Timestamp");
  String sig = server.header("X-Signature");
  String r = server.arg("r");
  long ms = server.arg("ms").toInt();
  if (ms < 200) ms = DEFAULT_UNLOCK_MS;
  ms = constrain(ms, 200, 15000);

  if (ts.length() == 0 || sig.length() == 0) {
    server.send(400, "application/json",
                "{\"ok\":false,\"error\":\"faltan headers de firma\"}");
    return;
  }
  String canonical = ts + ":" + String(ms) + ":" + r;
  String expect = hmacSha256Hex(DEVICE_KEY, canonical);
  if (!constantTimeEq(expect, sig)) {
    Serial.printf("[DENY] firma invalida desde %s\n",
                  server.client().remoteIP().toString().c_str());
    server.send(401, "application/json",
                "{\"ok\":false,\"error\":\"firma invalida\"}");
    return;
  }
  if (seenBefore(canonical)) {
    Serial.println("[DENY] replay detectado");
    server.send(401, "application/json",
                "{\"ok\":false,\"error\":\"comando repetido\"}");
    return;
  }
  relayPulse(ms, "remoto QR");
  server.send(200, "application/json",
              String("{\"ok\":true,\"ms\":") + String(ms) + "}");
  notifyEvent("unlock_remote", ms);
}

void handleStatus() {
  String json = String("{\"ok\":true,\"device_id\":\"") + DEVICE_ID +
                "\",\"kind\":\"" + DEVICE_KIND + "\",\"fw\":\"" FW_VERSION +
                "\",\"ip\":\"" + WiFi.localIP().toString() +
                "\",\"rssi\":" + String(WiFi.RSSI()) +
                ",\"uptime\":" + String(millis() / 1000) +
                ",\"relay\":" + (relayOn ? "true" : "false") +
                ",\"last\":" + String("\"") + lastReason + "\"}";
  server.send(200, "application/json", json);
}

// ---------------------------------------------------------------- setup
void setup() {
  Serial.begin(115200);
  delay(200);

  pinMode(RELAY_PIN, OUTPUT);
  relaySet(false);                       // rele apagado al arrancar
  pinMode(BUTTON_PIN, INPUT_PULLUP);     // boton a GND
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);           // LED onboard apagado (activo bajo)

  Serial.printf("\n[BOOT] %s %s fw %s\n", DEVICE_KIND, DEVICE_ID, FW_VERSION);

  WiFi.mode(WIFI_STA);
  WiFi.hostname(String("motel-") + DEVICE_ID);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  unsigned long t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 30000) {
    delay(250);
    Serial.print(".");
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n[WIFI] IP: %s\n", WiFi.localIP().toString().c_str());
    MDNS.begin(DEVICE_ID);
    MDNS.addService("http", "tcp", 80);
  } else {
    Serial.println("\n[WIFI] sin conexion, se reintentara solo");
  }

  server.on("/unlock", HTTP_GET, handleUnlock);
  server.on("/status", HTTP_GET, handleStatus);
  server.onNotFound([]() {
    server.send(404, "application/json",
                "{\"ok\":false,\"error\":\"ruta no existe\"}");
  });
  server.begin();
  Serial.println("[HTTP] escuchando en puerto 80");

  lastWifiTry = millis();
  lastHeartbeat = millis();
  if (WiFi.status() == WL_CONNECTED) heartbeat();
}

// ---------------------------------------------------------------- loop
void loop() {
  server.handleClient();
  MDNS.update();

  // apagar rele al cumplirse el tiempo
  if (relayOn && (long)(millis() - relayOffAt) >= 0) {
    relaySet(false);
    Serial.println("[RELE] OFF");
  }

  // boton interior: abre 5 s SIN autorizacion (seguridad de salida)
  static bool btnPrev = HIGH;
  static unsigned long btnDeb = 0;
  bool b = digitalRead(BUTTON_PIN);
  if (b != btnPrev && millis() - btnDeb > 40) {
    btnDeb = millis();
    if (b == LOW) {
      Serial.println("[BOTON] salida de emergencia");
      relayPulse(EXIT_UNLOCK_MS, "boton_salida");
      notifyEvent("exit_button", EXIT_UNLOCK_MS);
    }
    btnPrev = b;
  }

  // reconexion WiFi
  if (WiFi.status() != WL_CONNECTED && millis() - lastWifiTry > 15000) {
    lastWifiTry = millis();
    WiFi.begin(WIFI_SSID, WIFI_PASS);
  }

  // heartbeat al servidor
  if (WiFi.status() == WL_CONNECTED &&
      millis() - lastHeartbeat > HEARTBEAT_MS) {
    lastHeartbeat = millis();
    heartbeat();
  }

  // LED: fijo encendido mientras el rele esta activo, parpadeo lento en reposo
  if (relayOn) {
    digitalWrite(LED_PIN, LOW);
  } else if (millis() - lastBlink > 1500) {
    lastBlink = millis();
    ledState = !ledState;
    digitalWrite(LED_PIN, ledState ? LOW : HIGH);
  }

  delay(2);
}
