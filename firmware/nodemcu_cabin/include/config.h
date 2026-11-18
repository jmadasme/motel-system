#pragma once
// ============================================================
//  config.h - copia este archivo si necesitas uno nuevo.
//  Edita estos valores ANTES de flashear la placa.
// ============================================================

// --- WiFi de la intranet del motel ---
#define WIFI_SSID      "MOTEL-WIFI"
#define WIFI_PASS      "cambiar-esta-clave"

// --- Identidad de ESTA placa.
//     Debe coincidir EXACTAMENTE con la tabla "devices" del servidor:
//     el servidor firma los comandos con este mismo secreto. ---
#define DEVICE_ID      "cab01"          // ej: cab01, cab02, gate-01
#define DEVICE_KIND    "cabin"          // "cabin" o "gate"
#define DEVICE_KEY     "CAMBIAR-SECRETO-IGUAL-QUE-EN-EL-SERVIDOR"

// --- Servidor central ---
#define SERVER_HOST    "192.168.1.100"
#define SERVER_PORT    8080

// --- Pines (NodeMCU v2/v3) ---
#define RELAY_PIN      5      // D1 -> IN del modulo rele
#define RELAY_ACTIVE_LOW 1    // 1 = modulo rele tipico (activo en LOW)
#define BUTTON_PIN     4      // D2 -> boton de salida (a GND, con pull-up interno)
#define LED_PIN        2      // LED onboard (D4)

// --- Tiempos (ms) ---
#define DEFAULT_UNLOCK_MS 1000    // apertura por QR
#define EXIT_UNLOCK_MS    5000    // boton interior (salida de emergencia)
#define HEARTBEAT_MS      30000   // aviso "estoy vivo" al servidor
