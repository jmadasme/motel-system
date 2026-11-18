#pragma once
// ============================================================
//  config.example.h
//  Copia este archivo como config.h y edita los valores.
//  (config.h ya viene en el repo con valores de ejemplo;
//   cada placa flasheada debe tener los SUYOS)
// ============================================================

// --- WiFi de la intranet del motel ---
#define WIFI_SSID      "MOTEL-WIFI"
#define WIFI_PASS      "cambiar-esta-clave"

// --- Identidad de ESTA placa.
//     Debe coincidir EXACTAMENTE con la tabla "devices" del servidor. ---
#define DEVICE_ID      "cab01"
#define DEVICE_KIND    "cabin"
#define DEVICE_KEY     "CAMBIAR-SECRETO-IGUAL-QUE-EN-EL-SERVIDOR"

// --- Servidor central ---
#define SERVER_HOST    "192.168.1.100"
#define SERVER_PORT    8080

// --- Pines (NodeMCU v2/v3) ---
#define RELAY_PIN      5
#define RELAY_ACTIVE_LOW 1
#define BUTTON_PIN     4
#define LED_PIN        2

// --- Tiempos (ms) ---
#define DEFAULT_UNLOCK_MS 1000
#define EXIT_UNLOCK_MS    5000
#define HEARTBEAT_MS      30000
