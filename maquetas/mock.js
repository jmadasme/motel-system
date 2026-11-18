/* =====================================================================
   mock.js — Datos de ejemplo para las MAQUETAS del sistema de moteles.
   Intercepta fetch() para que las pantallas reales funcionen sin servidor.
   Escenario: "Motel Los Robles", noche en plena operación (23:05).
   ===================================================================== */

const MK_MOTEL = 'Motel Los Robles';

const MK_STATE = {
  ok: true, motel: MK_MOTEL, ts: '2026-10-13 23:05:00', printer_mode: 'network',
  totals: { libres: 3, ocupadas: 5, recaudacion: 166500, pedidos_pendientes: 2 },
  cabins: [
    { id: 1, name: 'Cabana 1', state: 'ocupada', prices: { '180': 15000, '360': 24000, '720': 38000 },
      scanner_key: 'demo', device_id: 'cab01',
      ticket: { id: 1041, issued_at: '2026-10-13 21:40:00', valid_until: '2026-10-14 00:40:00',
        duration_min: 180, price: 15000, entry_count: 2, plate: 'BJRF-31', token_short: 'A4F2K1' },
      charges: 9500, total: 24500, remaining_min: 95, elapsed_min: 85 },
    { id: 2, name: 'Cabana 2', state: 'libre', prices: { '180': 15000, '360': 24000, '720': 38000 },
      scanner_key: 'demo', device_id: 'cab02' },
    { id: 3, name: 'Cabana 3', state: 'ocupada', prices: { '180': 15000, '360': 24000, '720': 38000 },
      scanner_key: 'demo', device_id: 'cab03',
      ticket: { id: 1043, issued_at: '2026-10-13 22:30:00', valid_until: '2026-10-14 04:30:00',
        duration_min: 360, price: 24000, entry_count: 1, plate: 'HXKT-77', token_short: 'DEMO03' },
      charges: 7500, total: 31500, remaining_min: 325, elapsed_min: 35 },
    { id: 4, name: 'Cabana 4', state: 'ocupada', prices: { '180': 15000, '360': 24000, '720': 38000 },
      scanner_key: 'demo', device_id: 'cab04',
      ticket: { id: 1038, issued_at: '2026-10-13 20:10:00', valid_until: '2026-10-14 08:10:00',
        duration_min: 720, price: 38000, entry_count: 3, plate: 'LPCV-09', token_short: 'C9R7T2' },
      charges: 14500, total: 52500, remaining_min: 545, elapsed_min: 175 },
    { id: 5, name: 'Cabana 5', state: 'libre', prices: { '180': 18000, '360': 28000, '720': 44000 },
      scanner_key: 'demo', device_id: 'cab05' },
    { id: 6, name: 'Cabana 6', state: 'ocupada', prices: { '180': 18000, '360': 28000, '720': 44000 },
      scanner_key: 'demo', device_id: 'cab06',
      ticket: { id: 1044, issued_at: '2026-10-13 22:55:00', valid_until: '2026-10-14 01:55:00',
        duration_min: 180, price: 18000, entry_count: 1, plate: 'RTGB-52', token_short: 'M3V8Z5' },
      charges: 5500, total: 23500, remaining_min: 170, elapsed_min: 10 },
    { id: 7, name: 'Cabana 7', state: 'libre', prices: { '180': 22000, '360': 34000, '720': 52000 },
      scanner_key: 'demo', device_id: 'cab07' },
    { id: 8, name: 'Cabana 8', state: 'ocupada', prices: { '180': 22000, '360': 34000, '720': 52000 },
      scanner_key: 'demo', device_id: 'cab08',
      ticket: { id: 1035, issued_at: '2026-10-13 19:00:00', valid_until: '2026-10-14 01:00:00',
        duration_min: 360, price: 34000, entry_count: 2, plate: 'QWPD-14', token_short: 'F6H1N8' },
      charges: 11000, total: 45000, remaining_min: 115, elapsed_min: 245 }
  ],
  devices: [
    { id: 'cab01', kind: 'cabin', cabin_id: 1, ip: '192.168.1.61', port: 80, last_seen: '2026-10-13 23:04:41', last_event: 'unlock_remote', online: true, status: 'en linea' },
    { id: 'cab02', kind: 'cabin', cabin_id: 2, ip: '192.168.1.62', port: 80, last_seen: '2026-10-13 23:04:12', last_event: 'heartbeat', online: true, status: 'en linea' },
    { id: 'cab03', kind: 'cabin', cabin_id: 3, ip: '192.168.1.63', port: 80, last_seen: '2026-10-13 23:03:58', last_event: 'unlock_remote', online: true, status: 'en linea' },
    { id: 'cab04', kind: 'cabin', cabin_id: 4, ip: '192.168.1.64', port: 80, last_seen: '2026-10-13 23:04:05', last_event: 'exit_button', online: true, status: 'en linea' },
    { id: 'cab05', kind: 'cabin', cabin_id: 5, ip: '192.168.1.65', port: 80, last_seen: '2026-10-13 23:03:50', last_event: 'heartbeat', online: true, status: 'en linea' },
    { id: 'cab06', kind: 'cabin', cabin_id: 6, ip: '192.168.1.66', port: 80, last_seen: '2026-10-13 23:04:22', last_event: 'unlock_remote', online: true, status: 'en linea' },
    { id: 'cab07', kind: 'cabin', cabin_id: 7, ip: '192.168.1.67', port: 80, last_seen: '2026-10-13 22:49:10', last_event: 'heartbeat', online: false, status: 'sin senal 951s' },
    { id: 'cab08', kind: 'cabin', cabin_id: 8, ip: '192.168.1.68', port: 80, last_seen: '2026-10-13 23:04:30', last_event: 'heartbeat', online: true, status: 'en linea' },
    { id: 'gate-01', kind: 'gate', cabin_id: null, ip: '192.168.1.60', port: 80, last_seen: '2026-10-13 23:04:48', last_event: 'open_remote', online: true, status: 'en linea' }
  ],
  events: [
    { ts: '2026-10-13 23:05:00', kind: 'pedido', cabin_name: 'Cabana 1', detail: 'orden #88 $13.500' },
    { ts: '2026-10-13 23:04:41', kind: 'puerta', cabin_name: 'Cabana 1', detail: 'apertura por QR (192.168.1.61 -> ok)' },
    { ts: '2026-10-13 23:04:41', kind: 'scan_ok', cabin_name: 'Cabana 1', detail: 'ticket #1041 entrada #2' },
    { ts: '2026-10-13 23:03:58', kind: 'puerta', cabin_name: 'Cabana 3', detail: 'apertura por QR (192.168.1.63 -> ok)' },
    { ts: '2026-10-13 23:03:52', kind: 'scan_ok', cabin_name: 'Cabana 3', detail: 'ticket #1043 entrada #1' },
    { ts: '2026-10-13 22:58:12', kind: 'pedido', cabin_name: 'Cabana 6', detail: 'orden #90 $5.500' },
    { ts: '2026-10-13 22:55:37', kind: 'barrera', cabin_name: null, detail: 'apertura automatica post check-in' },
    { ts: '2026-10-13 22:55:36', kind: 'checkin', cabin_name: 'Cabana 6', detail: 'ticket #1044 3 horas $18.000' },
    { ts: '2026-10-13 22:51:20', kind: 'dispositivo:exit_button', cabin_name: 'Cabana 4', detail: 'ms=5000' },
    { ts: '2026-10-13 22:47:55', kind: 'pedido_estado', cabin_name: 'Cabana 4', detail: 'orden #89 -> preparando' },
    { ts: '2026-10-13 22:44:03', kind: 'pedido', cabin_name: 'Cabana 4', detail: 'orden #89 $7.500' },
    { ts: '2026-10-13 22:30:21', kind: 'checkin', cabin_name: 'Cabana 3', detail: 'ticket #1043 6 horas $24.000' },
    { ts: '2026-10-13 22:18:44', kind: 'checkout', cabin_name: 'Cabana 2', detail: 'total $34.500 (base $24.000 + servicios $10.500)' },
    { ts: '2026-10-13 21:40:09', kind: 'checkin', cabin_name: 'Cabana 1', detail: 'ticket #1041 3 horas $15.000' },
    { ts: '2026-10-13 20:10:02', kind: 'checkin', cabin_name: 'Cabana 4', detail: 'ticket #1038 12 horas $38.000' },
    { ts: '2026-10-13 19:00:31', kind: 'checkin', cabin_name: 'Cabana 8', detail: 'ticket #1035 6 horas $34.000' }
  ]
};

const MK_REVENUE = {
  ok: true,
  hoy: { n: 9, base: 141000, services: 25500, total: 166500 },
  mes: { n: 118, base: 1872000, services: 342000, total: 2214000 },
  en_curso_total: 166500,
  en_curso: [
    { id: 1041, cabin_name: 'Cabana 1', issued_at: '2026-10-13 21:40:00', valid_until: '2026-10-14 00:40:00', duration_min: 180, price: 15000, services: 9500, total_now: 24500 },
    { id: 1043, cabin_name: 'Cabana 3', issued_at: '2026-10-13 22:30:00', valid_until: '2026-10-14 04:30:00', duration_min: 360, price: 24000, services: 7500, total_now: 31500 },
    { id: 1038, cabin_name: 'Cabana 4', issued_at: '2026-10-13 20:10:00', valid_until: '2026-10-14 08:10:00', duration_min: 720, price: 38000, services: 14500, total_now: 52500 },
    { id: 1044, cabin_name: 'Cabana 6', issued_at: '2026-10-13 22:55:00', valid_until: '2026-10-14 01:55:00', duration_min: 180, price: 18000, services: 5500, total_now: 23500 },
    { id: 1035, cabin_name: 'Cabana 8', issued_at: '2026-10-13 19:00:00', valid_until: '2026-10-14 01:00:00', duration_min: 360, price: 34000, services: 11000, total_now: 45000 }
  ],
  historial: [
    { id: 1042, cabin_name: 'Cabana 2', issued_at: '2026-10-13 20:41:00', closed_at: '2026-10-13 22:18:44', duration_min: 360, price: 24000, total_charged: 34500 },
    { id: 1040, cabin_name: 'Cabana 5', issued_at: '2026-10-13 19:52:00', closed_at: '2026-10-13 21:37:12', duration_min: 180, price: 18000, total_charged: 22500 },
    { id: 1039, cabin_name: 'Cabana 7', issued_at: '2026-10-13 18:20:00', closed_at: '2026-10-13 21:05:33', duration_min: 360, price: 34000, total_charged: 46500 },
    { id: 1037, cabin_name: 'Cabana 1', issued_at: '2026-10-13 16:10:00', closed_at: '2026-10-13 18:44:05', duration_min: 180, price: 15000, total_charged: 18500 },
    { id: 1036, cabin_name: 'Cabana 3', issued_at: '2026-10-13 14:05:00', closed_at: '2026-10-13 17:32:48', duration_min: 240, price: 20000, total_charged: 26000 },
    { id: 1034, cabin_name: 'Cabana 4', issued_at: '2026-10-13 01:20:00', closed_at: '2026-10-13 04:55:10', duration_min: 180, price: 15000, total_charged: 19000 },
    { id: 1033, cabin_name: 'Cabana 2', issued_at: '2026-10-12 23:40:00', closed_at: '2026-10-13 02:10:44', duration_min: 180, price: 15000, total_charged: 15000 },
    { id: 1032, cabin_name: 'Cabana 8', issued_at: '2026-10-12 22:15:00', closed_at: '2026-10-13 01:02:19', duration_min: 180, price: 22000, total_charged: 29500 },
    { id: 1031, cabin_name: 'Cabana 5', issued_at: '2026-10-12 21:05:00', closed_at: '2026-10-12 23:55:02', duration_min: 180, price: 18000, total_charged: 21500 },
    { id: 1030, cabin_name: 'Cabana 6', issued_at: '2026-10-12 20:30:00', closed_at: '2026-10-12 23:40:37', duration_min: 180, price: 18000, total_charged: 18000 },
    { id: 1029, cabin_name: 'Cabana 1', issued_at: '2026-10-12 18:55:00', closed_at: '2026-10-12 21:20:11', duration_min: 180, price: 15000, total_charged: 24500 },
    { id: 1028, cabin_name: 'Cabana 7', issued_at: '2026-10-12 17:40:00', closed_at: '2026-10-12 20:05:49', duration_min: 180, price: 22000, total_charged: 26500 }
  ],
  por_dia: [
    { dia: '2026-09-30', n: 14, base: 236000, services: 41500, total: 277500 },
    { dia: '2026-10-01', n: 12, base: 198000, services: 33000, total: 231000 },
    { dia: '2026-10-02', n: 18, base: 292000, services: 52000, total: 344000 },
    { dia: '2026-10-03', n: 21, base: 342000, services: 61000, total: 403000 },
    { dia: '2026-10-04', n: 20, base: 305000, services: 48500, total: 353500 },
    { dia: '2026-10-05', n: 11, base: 178000, services: 26000, total: 204000 },
    { dia: '2026-10-06', n: 10, base: 162000, services: 21500, total: 183500 },
    { dia: '2026-10-07', n: 13, base: 204000, services: 30500, total: 234500 },
    { dia: '2026-10-08', n: 15, base: 241000, services: 38500, total: 279500 },
    { dia: '2026-10-09', n: 19, base: 308000, services: 54000, total: 362000 },
    { dia: '2026-10-10', n: 24, base: 396000, services: 72500, total: 468500 },
    { dia: '2026-10-11', n: 23, base: 372000, services: 64500, total: 436500 },
    { dia: '2026-10-12', n: 16, base: 258000, services: 41500, total: 299500 },
    { dia: '2026-10-13', n: 9, base: 141000, services: 25500, total: 166500 }
  ]
};

const MK_PRODUCTS = {
  ok: true,
  products: [
    { id: 1, name: 'Coca-Cola 350cc', category: 'bebidas', price: 2500, active: 1 },
    { id: 2, name: 'Sprite 350cc', category: 'bebidas', price: 2500, active: 1 },
    { id: 3, name: 'Agua mineral 500cc', category: 'bebidas', price: 1500, active: 1 },
    { id: 4, name: 'Cerveza lata', category: 'bebidas', price: 3500, active: 1 },
    { id: 5, name: 'Jugo natural', category: 'bebidas', price: 2000, active: 1 },
    { id: 6, name: 'Bebida energetica', category: 'bebidas', price: 3500, active: 1 },
    { id: 7, name: 'Sandwich completo', category: 'comidas', price: 5500, active: 1 },
    { id: 8, name: 'Pizza personal', category: 'comidas', price: 6500, active: 1 },
    { id: 9, name: 'Papas fritas porcion', category: 'comidas', price: 3000, active: 1 },
    { id: 10, name: 'Completo italiano', category: 'comidas', price: 3500, active: 1 },
    { id: 11, name: 'Empanada de queso', category: 'comidas', price: 2500, active: 1 },
    { id: 12, name: 'Desayuno completo', category: 'desayuno', price: 8000, active: 1 },
    { id: 13, name: 'Cafe con leche', category: 'desayuno', price: 1800, active: 1 },
    { id: 14, name: 'Tostadas', category: 'desayuno', price: 2000, active: 1 },
    { id: 15, name: 'Helado', category: 'otros', price: 2500, active: 1 },
    { id: 16, name: 'Cigarrillos', category: 'otros', price: 4000, active: 1 },
    { id: 17, name: 'Preservativos', category: 'otros', price: 1500, active: 1 },
    { id: 18, name: 'Kit de aseo', category: 'otros', price: 1200, active: 1 }
  ]
};

const MK_ORDERS = {
  ok: true,
  orders: [
    { id: 88, cabin_name: 'Cabana 1', created_at: '2026-10-13 23:05:00', status: 'nuevo', total: 13500,
      items: [{ name: 'Pizza personal', qty: 1, price: 6500 }, { name: 'Cerveza lata', qty: 2, price: 3500 }] },
    { id: 89, cabin_name: 'Cabana 4', created_at: '2026-10-13 22:44:03', status: 'preparando', total: 7500,
      items: [{ name: 'Sandwich completo', qty: 1, price: 5500 }, { name: 'Jugo natural', qty: 1, price: 2000 }] },
    { id: 90, cabin_name: 'Cabana 6', created_at: '2026-10-13 22:58:12', status: 'nuevo', total: 5500,
      items: [{ name: 'Papas fritas porcion', qty: 1, price: 3000 }, { name: 'Coca-Cola 350cc', qty: 1, price: 2500 }] },
    { id: 91, cabin_name: 'Cabana 3', created_at: '2026-10-13 23:01:30', status: 'listo', total: 4000,
      items: [{ name: 'Preservativos', qty: 1, price: 1500 }, { name: 'Helado', qty: 1, price: 2500 }] },
    { id: 87, cabin_name: 'Cabana 8', created_at: '2026-10-13 22:20:10', status: 'entregado', total: 7000,
      items: [{ name: 'Cerveza lata', qty: 2, price: 3500 }] },
    { id: 86, cabin_name: 'Cabana 1', created_at: '2026-10-13 21:55:44', status: 'entregado', total: 5500,
      items: [{ name: 'Sandwich completo', qty: 1, price: 5500 }] }
  ]
};

const MK_CABIN_STATE = {
  ok: true, cabin: { id: 3, name: 'Cabana 3' }, state: 'ocupada',
  ticket: { valid_until: '2026-10-14 04:30:00', duration_min: 360, price: 24000, entry_count: 1 },
  charges: 7500,
  orders: [
    { id: 91, created_at: '2026-10-13 23:01:30', status: 'listo', total: 4000,
      items: [{ name: 'Preservativos', qty: 1, price: 1500 }, { name: 'Helado', qty: 1, price: 2500 }] },
    { id: 85, created_at: '2026-10-13 22:35:18', status: 'entregado', total: 3500,
      items: [{ name: 'Cerveza lata', qty: 1, price: 3500 }] }
  ]
};

/* ---------- interceptacion de fetch ---------- */
const MK_RESP = (data) => new Response(JSON.stringify(data), {
  status: 200, headers: { 'Content-Type': 'application/json' } });

window.fetch = async (url, opts = {}) => {
  const path = String(url).split('?')[0];
  const method = (opts.method || 'GET').toUpperCase();
  let body = {};
  try { body = opts.body ? JSON.parse(opts.body) : {}; } catch (e) {}

  if (path === '/api/config') return MK_RESP({ ok: true, motel: MK_MOTEL, require_keys: false });
  if (path === '/api/state' && method === 'GET') return MK_RESP(MK_STATE);
  if (path === '/api/revenue' && method === 'GET') return MK_RESP(MK_REVENUE);
  if (path === '/api/products') return MK_RESP(MK_PRODUCTS);
  if (path === '/api/orders' && method === 'GET') return MK_RESP(MK_ORDERS);
  if (path === '/api/cabin_state') return MK_RESP(MK_CABIN_STATE);

  if (path === '/api/scan') {
    const code = String(body.code || '').trim().toUpperCase();
    if (code.startsWith('MTL1-') || code.length === 6)
      return MK_RESP({ ok: true, cabin: 'Cabana 3', valid_until: '2026-10-14 04:30:00',
        price: 24000, entries: 2,
        unlock: { ok: true, simulated: false,
          detail: 'http://192.168.1.63/unlock?ms=1000&r=demo -> {"ok":true,"ms":1000}' } });
    return MK_RESP({ ok: false, reason: 'Codigo no reconocido', cabin: 'Cabana 3' });
  }

  if (path === '/api/orders' && method === 'POST')
    return MK_RESP({ ok: true, order_id: 92, total: 5000 });
  if (path === '/api/orders/status') {
    const o = MK_ORDERS.orders.find(x => x.id === body.order_id);
    if (o) o.status = body.status;
    return MK_RESP({ ok: true, order_id: body.order_id, status: body.status });
  }
  if (path === '/api/exit_request')
    return MK_RESP({ ok: true, unlock: { ok: true, detail: 'pulso 5000 ms enviado (demo)' } });
  if (path === '/api/panel/open')
    return MK_RESP({ ok: true, unlock: { ok: true, detail: 'pulso 1000 ms enviado (demo)' } });
  if (path === '/api/gate/open')
    return MK_RESP({ ok: true, unlock: { ok: true, detail: 'barrera: pulso 1500 ms enviado (demo)' } });
  if (path === '/api/checkin') {
    const c = MK_STATE.cabins.find(x => x.id === body.cabin_id) || MK_STATE.cabins[4];
    return MK_RESP({ ok: true,
      ticket: { id: 1050, cabin_id: c.id, cabin_name: c.name, issued_at: '2026-10-13 23:06:00',
        valid_until: '2026-10-14 02:06:00', duration_min: body.duration_min || 180,
        price: c.prices[String(body.duration_min || 180)], token_short: 'DEMO50', plate: body.plate || null },
      qr_payload: 'MTL1-demoejemplo12345678',
      print: { ok: true, mode: 'network', detail: 'enviado a 192.168.1.50:9100' },
      gate: { ok: true, detail: 'barrera: pulso 1500 ms enviado (demo)' } });
  }
  if (path === '/api/checkout')
    return MK_RESP({ ok: true, cabin: 'Cabana 4', base: 38000, charges: 14500, total: 52500,
      gate: { ok: true, detail: 'barrera abierta (demo)' } });
  if (path === '/api/reprint')
    return MK_RESP({ ok: true, qr_payload: 'MTL1-demoejemplo12345678', token_short: 'DEMO50',
      print: { ok: true, mode: 'network', detail: 'enviado a 192.168.1.50:9100' } });

  return MK_RESP({ ok: false, error: 'ruta no simulada en la maqueta: ' + path });
};
