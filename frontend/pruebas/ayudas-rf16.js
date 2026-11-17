// Datos comunes de las pruebas de RF-16 (Libro de Reclamaciones). La API se simula con page.route.
import { perfil } from './ayudas-acceso.js';

export const H1 = '3f2a9c1e-5b7d-4e8a-9c4b-1a2b3c4d5e6f';
export const H2 = '4a2a9c1e-5b7d-4e8a-9c4b-1a2b3c4d5e70';
export const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==', 'base64');
export const archivo = (nombre = 'voucher.png', tipo = 'image/png', buffer = PNG) => ({ name: nombre, mimeType: tipo, buffer });
export const HOY = new Date('2026-11-17T17:00:00Z'); // martes 17 nov 2026, 12:00 en Lima

export const PROVEEDOR = { razon_social: 'Aural Perú E.I.R.L.', ruc: '20615656128', domicilio: 'Av. Javier Prado Este 5920, La Molina, Lima' };

// Hoja de la API (Hoja del contrato); `extra` pisa lo que haga falta.
export const hoja = (extra = {}) => ({
  id: H1, numero: '000000001-2026', creada_en: '2026-11-17T19:30:00Z', vence_respuesta: '2026-12-09T04:59:59Z', dias_habiles_restantes: 15,
  proveedor: PROVEEDOR,
  consumidor: { nombre: 'Ana Pérez', tipo_documento: 'dni', documento: '12345678', domicilio: 'Av. Siempre Viva 123, Lima', telefono: '987654321', correo: 'ana@correo.com' },
  es_menor: false,
  bien: { tipo: 'servicio', monto: '1250.00', descripcion: 'Mezcla de mi EP, reserva R-2026-00014.' },
  tipo: 'reclamo', detalle: 'Entregaron la mezcla con tres días de retraso.\nNadie me avisó.', pedido: 'Que me devuelvan la mitad del importe.',
  medio_respuesta: 'correo', adjuntos: [], origen: 'web', estado: 'pendiente', ...extra,
});
export const RESPUESTA = { texto: 'Lamentamos el retraso.\nTe devolvemos S/ 625,00.', medio: 'correo', enviada_en: '2026-11-20T15:00:00Z', respondida_por: { id: 'a1', nombre: 'Luis Admin' } };
export const resumen = (extra = {}) => ({ id: H1, numero: '000000001-2026', creada_en: '2026-11-17T19:30:00Z', tipo: 'reclamo', estado: 'pendiente', vence_respuesta: '2026-12-09T04:59:59Z', dias_habiles_restantes: 15, consumidor: { nombre: 'Ana Pérez' }, ...extra });

export const PERFIL_CLIENTE = {
  rol: 'cliente', nombre: 'Ana Pérez', correo: 'ana@correo.com', telefono: '987654321', documento: { tipo: 'dni', numero: '12345678' }, domicilio: 'Av. Siempre Viva 123, Lima', es_menor: false, modalidad: 'individual', redes: [], integrantes: [],
};
export const perfilCliente = (extra = {}) => perfil({ ...PERFIL_CLIENTE, ...extra });

// Responde un POST multipart y devuelve lo que vio: {datos (JSON de `datos`), adjuntos (nombres), auth, tipo}.
export async function simularMultipart(page, camino, resp = null) {
  const vistas = [];
  await page.route((u) => u.pathname === `/api/v1${camino}`, (r) => {
    const req = r.request();
    if (req.method() !== 'POST') return r.fallback();
    const texto = req.postDataBuffer()?.toString('utf8') ?? '';
    const m = /name="datos"\r\n\r\n([\s\S]*?)\r\n--/.exec(texto);
    vistas.push({ datos: m ? JSON.parse(m[1]) : null, adjuntos: [...texto.matchAll(/name="adjuntos"; filename="([^"]*)"/g)].map((x) => x[1]), auth: req.headers().authorization, tipo: req.headers()['content-type'] });
    return typeof resp === 'function' ? resp(r, vistas.length) : r.fulfill(resp);
  });
  return vistas;
}
