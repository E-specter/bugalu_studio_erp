// RF-18 (CA-04, CA-11, CA-12, CA-16, lado Administrador y personal): no asistio, caso excepcional, cancelar por el estudio o a pedido del cliente.
import { test, expect } from '@playwright/test';
import { API, json, errorApi, perfil, conSesion, silenciarApi, sinViolaciones, vigilarConsola, tamanos } from './ayudas-acceso.js';
import { simular } from './ayudas-admin.js';
import { ID, AHORA, noAsistio as noAsistioBase, reserva, vista, cancelada, cuotasPagadas, cuotasSinPagos } from './ayudas-rf18.js';

const comoRol = (page, rol) => page.route(`${API}/perfil`, (r) => r.fulfill(perfil({ rol })));
const ver = (page, query = '') => page.goto(`/app/reservas/detalle?id=${ID}${query}`);
const con = (page, r) => simular(page, 'GET', `/reservas/${ID}`, json(200, r));
const barra = (page) => page.locator('[data-estado-reserva]');
const aviso = (page) => page.locator('[data-avisos] .aviso');
// Lima = UTC-5: AHORA es 10:00.
const t = (hhmm) => `2026-11-15T${hhmm}:00-05:00`;
const EN_VENTANA = { inicio: t('09:40'), fin: t('11:30') }; // pasaron 20 min: ya se puede marcar
const ANTES = { inicio: t('09:50'), fin: t('11:30') }; // pasaron 10 min: se puede desde las 10:05

test.beforeEach(async ({ page }) => {
  await page.clock.setFixedTime(AHORA);
  await conSesion(page);
  await silenciarApi(page);
  await comoRol(page, 'administrador');
});

// --- No asistió ---
const marcar = (page) => page.getByRole('button', { name: 'Marcar no asistió', exact: true });
const panelNA = (page) => page.getByRole('region', { name: /Marcar inasistencia · R-2026-00001/ });
const asistio = (extra = {}) => reserva({ cliente: 'Ana Pérez', ...EN_VENTANA, ...extra });
const noAsistio = (extra = {}) => ({ ...noAsistioBase(), cliente: 'Ana Pérez', ...EN_VENTANA, ...extra });

for (const t of tamanos) {
  test(`no asistió: el Administrador lo marca pasada la tolerancia, a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await con(page, asistio());
    const llamadas = await simular(page, 'POST', `/reservas/${ID}/inasistencia`, json(200, noAsistio()));
    await ver(page);
    await expect(marcar(page)).toBeVisible();
    await expect(marcar(page)).not.toHaveAttribute('aria-disabled', 'true');
    await marcar(page).click();
    await expect(page.getByRole('heading', { name: /Marcar inasistencia · R-2026-00001/ })).toBeFocused();
    await expect(panelNA(page)).toContainText('Ana Pérez no llegó en los primeros 15 minutos.');
    await expect(panelNA(page)).toContainText('Se retiene lo pagado (S/ 100,00), se anula el saldo y no hay crédito ni cobro adicional. El horario sigue ocupado. Avisamos al cliente por correo. No se puede deshacer: solo el Administrador puede tratarla después como nivel 1.');
    await sinViolaciones(page);
    await page.screenshot({ path: `pruebas/capturas/rf18-no-asistio-panel-${t.nombre}.png`, fullPage: true });
    await panelNA(page).getByRole('button', { name: 'Marcar no asistió', exact: true }).click();
    expect(llamadas).toHaveLength(1);
    await expect(aviso(page)).toContainText('Inasistencia registrada. Avisamos al cliente por correo.');
    await expect(aviso(page)).toBeFocused();
    await expect(barra(page)).toContainText('No asistió');
    await expect(barra(page)).toContainText('No llegó en los primeros 15 minutos. Se retuvo lo pagado (S/ 100,00); no hay crédito ni cobro adicional.');
    await expect(panelNA(page)).toBeHidden();
    await expect(marcar(page)).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
  });
}

test('no asistió: antes de la tolerancia el botón está deshabilitado pero se enfoca, con la hora y sin panel', async ({ page }) => {
  await con(page, asistio(ANTES));
  const llamadas = await simular(page, 'POST', `/reservas/${ID}/inasistencia`, json(200, noAsistio()));
  await ver(page);
  const boton = marcar(page);
  await expect(boton).toHaveAttribute('aria-disabled', 'true');
  await boton.focus();
  await expect(boton).toBeFocused();
  const ayuda = page.getByText('Podrás marcarlo desde las 10:05, 15 minutos después del inicio.');
  await expect(ayuda).toBeVisible();
  const id = await ayuda.getAttribute('id');
  await expect(boton).toHaveAttribute('aria-describedby', new RegExp(id));
  await boton.click({ force: true });
  await expect(page.locator('[data-ayuda-na]')).toHaveText('Aún no pasaron 15 minutos desde el inicio. Podrás marcarlo desde las 10:05.');
  await expect(panelNA(page)).toBeHidden();
  expect(llamadas).toHaveLength(0);
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf18-no-asistio-espera-1440.png', fullPage: true });
});

test('no asistió: fuera de la ventana inicio-fin no hay botón', async ({ page }) => {
  await con(page, asistio({ inicio: t('10:30'), fin: t('12:00') }));
  await ver(page);
  await expect(marcar(page)).toHaveCount(0);
  await con(page, asistio({ inicio: t('08:00'), fin: t('09:30') }));
  await ver(page);
  await expect(marcar(page)).toHaveCount(0);
});

test('no asistió: el personal también lo marca; el cliente no lo ve', async ({ page }) => {
  await comoRol(page, 'personal');
  await con(page, asistio());
  await ver(page);
  await expect(marcar(page)).toBeVisible();
  await expect(page.getByRole('button', { name: /Tratar como nivel 1|Cancelar reserva/ })).toHaveCount(0);
  await comoRol(page, 'cliente');
  await ver(page);
  await expect(marcar(page)).toHaveCount(0);
});

test('no asistió: ?accion=inasistencia abre el panel solo si ya se puede', async ({ page }) => {
  await con(page, asistio());
  await ver(page, '&accion=inasistencia');
  await expect(panelNA(page)).toBeVisible();
  await con(page, asistio(ANTES));
  await ver(page, '&accion=inasistencia');
  await expect(panelNA(page)).toBeHidden();
  await expect(page.getByText('Podrás marcarlo desde las 10:05, 15 minutos después del inicio.')).toBeVisible();
});

test('no asistió: 409 tolerancia_no_cumplida dice la hora; 409 no_aplicable recarga y explica', async ({ page }) => {
  let lecturas = 0;
  await simular(page, 'GET', `/reservas/${ID}`, (r) => r.fulfill(json(200, lecturas++ >= 1 ? reserva({ estado: 'cancelada', motivo_cancelacion: 'cliente', ...EN_VENTANA }) : asistio())));
  let codigo = 'tolerancia_no_cumplida';
  await simular(page, 'POST', `/reservas/${ID}/inasistencia`, (r) => r.fulfill(errorApi(409, codigo)));
  await ver(page);
  await marcar(page).click();
  await panelNA(page).getByRole('button', { name: 'Marcar no asistió', exact: true }).click();
  await expect(page.getByText('Aún no pasaron 15 minutos desde el inicio. Podrás marcarlo desde las 09:55.')).toBeVisible();
  await expect(panelNA(page)).toBeHidden();
  codigo = 'no_aplicable';
  await marcar(page).click();
  await panelNA(page).getByRole('button', { name: 'Marcar no asistió', exact: true }).click();
  await expect(aviso(page)).toContainText('Esta reserva ya no admite marcar la inasistencia: está cancelada.');
  await expect(aviso(page)).toBeFocused();
  await expect(marcar(page)).toHaveCount(0);
  await sinViolaciones(page);
});

test('no asistió: 503 deja el botón disponible y avisa sin Reintentar; volver devuelve el foco', async ({ page }) => {
  await con(page, asistio());
  await simular(page, 'POST', `/reservas/${ID}/inasistencia`, (r) => r.fulfill(errorApi(503, 'x')));
  await ver(page);
  await marcar(page).click();
  await panelNA(page).getByRole('button', { name: 'Marcar no asistió', exact: true }).click();
  await expect(aviso(page)).toContainText('El servicio no responde. Inténtalo de nuevo en unos minutos.');
  await expect(page.getByRole('button', { name: 'Reintentar' })).toHaveCount(0);
  await page.keyboard.press('Escape');
  await expect(panelNA(page)).toBeHidden();
  await expect(marcar(page)).toBeFocused();
});

// --- Tratar como nivel 1 ---
const tratar = (page) => page.getByRole('button', { name: 'Tratar como nivel 1', exact: true });
const panelEx = (page) => page.getByRole('region', { name: /Tratar como nivel 1 · R-2026-00001/ });
const cancelada2 = (extra = {}) => {
  const base = cancelada(2);
  return { ...base, cliente: 'Ana Pérez', cancelacion: { ...base.cancelacion, ...extra } };
};

for (const t of tamanos) {
  test(`excepción: tratar como nivel 1 una cancelación de nivel 2, a ${t.nombre}`, async ({ page }) => {
    const consola = vigilarConsola(page);
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await con(page, cancelada2());
    const llamadas = await simular(page, 'POST', `/reservas/${ID}/excepcion`, json(200, cancelada2({ credito: '50.00', retenido: '0.00', excepcion: { motivo: 'Duelo familiar con sustento', por: 'Ana', en: '2026-11-15T10:00:00-05:00' } })));
    await ver(page);
    await tratar(page).click();
    await expect(page.getByRole('heading', { name: /Tratar como nivel 1 · R-2026-00001/ })).toBeFocused();
    await expect(panelEx(page)).toContainText('Para emergencias de salud, duelos, desastres o paros que impidieron avisar a tiempo, con un sustento razonable.');
    await expect(panelEx(page).locator('dl')).toContainText('Retenido hoy');
    await expect(panelEx(page).locator('dl')).toContainText('S/ 50,00');
    await expect(panelEx(page)).toContainText('Lo retenido (S/ 50,00) pasa a un crédito de caso excepcional que vence 30 días después de hoy y admite devolución. Solo se puede hacer una vez por reserva y queda registrado quién y por qué. No se puede deshacer.');
    await expect(panelEx(page)).toContainText('Qué pasó y qué sustento recibiste. El cliente lo verá en su reserva.');
    await sinViolaciones(page);
    await page.screenshot({ path: `pruebas/capturas/rf18-excepcion-panel-${t.nombre}.png`, fullPage: true });
    // Validación local: motivo de 10 a 500.
    await panelEx(page).getByRole('button', { name: 'Tratar como nivel 1', exact: true }).click();
    await expect(page.getByText('Escribe el motivo, de 10 a 500 caracteres.').first()).toBeVisible();
    await expect(aviso(page)).toBeFocused();
    await page.getByLabel(/Motivo/).fill('corto');
    await panelEx(page).getByRole('button', { name: 'Tratar como nivel 1', exact: true }).click();
    expect(llamadas).toHaveLength(0);
    await page.getByLabel(/Motivo/).fill('Duelo familiar con sustento');
    await panelEx(page).getByRole('button', { name: 'Tratar como nivel 1', exact: true }).click();
    expect(llamadas[0].cuerpo).toEqual({ motivo: 'Duelo familiar con sustento' });
    await expect(aviso(page)).toContainText('Tratada como nivel 1. S/ 50,00 pasaron a crédito del cliente, con devolución posible.');
    await expect(aviso(page)).toBeFocused();
    await expect(page.getByRole('region', { name: /D4 Cancelación/i })).toContainText('Tratada como nivel 1 el 15 nov: Duelo familiar con sustento');
    await expect(tratar(page)).toHaveCount(0);
    await sinViolaciones(page);
    expect(consola).toEqual([]);
  });
}

test('excepción: aparece en una inasistencia con pagado y solo para el Administrador', async ({ page }) => {
  await con(page, noAsistio());
  await ver(page);
  await expect(tratar(page)).toBeVisible();
  await comoRol(page, 'personal');
  await ver(page);
  await expect(tratar(page)).toHaveCount(0);
});

const NO_APLICA = [
  ['nivel 1', cancelada(1)],
  ['cancelada por el estudio', cancelada(2, { motivo_cancelacion: 'administrador', cancelacion: { ...cancelada(2).cancelacion, por: 'estudio' } })],
  ['nada retenido', cancelada(2, { cancelacion: { ...cancelada(2).cancelacion, retenido: '0.00' } })],
  ['ya aplicada', cancelada2({ excepcion: { motivo: 'Ya', por: 'Ana', en: '2026-11-15T10:00:00-05:00' } })],
  ['inasistencia sin pagado', noAsistio({ cancelacion: { ...noAsistioBase().cancelacion, retenido: '0.00' } })],
];
for (const [nombre, r] of NO_APLICA) {
  test(`excepción: no se ofrece (${nombre})`, async ({ page }) => {
    await con(page, r);
    await ver(page);
    await expect(barra(page)).toBeVisible();
    await expect(tratar(page)).toHaveCount(0);
  });
}

for (const [codigo, texto] of [
  ['excepcion_ya_aplicada', 'Esta reserva ya se trató como nivel 1, quizá desde otra sesión.'],
  ['excepcion_no_aplicable', 'Esta reserva no admite el caso excepcional.'],
]) {
  test(`excepción: 409 ${codigo} cierra el panel, recarga y explica`, async ({ page }) => {
    await con(page, cancelada2());
    await simular(page, 'POST', `/reservas/${ID}/excepcion`, (r) => r.fulfill(errorApi(409, codigo)));
    await ver(page);
    await tratar(page).click();
    await page.getByLabel(/Motivo/).fill('Duelo familiar con sustento');
    await panelEx(page).getByRole('button', { name: 'Tratar como nivel 1', exact: true }).click();
    await expect(aviso(page)).toContainText(texto);
    await expect(aviso(page)).toHaveClass(/aviso-informacion/);
    await expect(panelEx(page)).toBeHidden();
    await sinViolaciones(page);
  });
}

test('excepción: 422 va bajo el motivo y 503 avisa sin Reintentar', async ({ page }) => {
  await con(page, cancelada2());
  let estado = 422;
  await simular(page, 'POST', `/reservas/${ID}/excepcion`, (r) => r.fulfill(errorApi(estado, estado === 422 ? 'datos_invalidos' : 'x')));
  await ver(page);
  await tratar(page).click();
  await page.getByLabel(/Motivo/).fill('Duelo familiar con sustento');
  await panelEx(page).getByRole('button', { name: 'Tratar como nivel 1', exact: true }).click();
  await expect(page.getByText('Escribe el motivo, de 10 a 500 caracteres.').first()).toBeVisible();
  await expect(page.getByLabel(/Motivo/)).toHaveAttribute('aria-invalid', 'true');
  estado = 503;
  await panelEx(page).getByRole('button', { name: 'Tratar como nivel 1', exact: true }).click();
  await expect(aviso(page)).toContainText('El servicio no responde.');
  await expect(page.getByRole('button', { name: 'Reintentar' })).toHaveCount(0);
});

// --- Cancelar (estudio o a pedido del cliente) ---
const abrirCancelar = (page) => page.getByRole('button', { name: 'Cancelar reserva', exact: true });
const panelC = (page) => page.getByRole('region', { name: /Cancelar reserva R-2026-00001/ });
const confirmarC = (page) => panelC(page).getByRole('button', { name: 'Cancelar reserva R-2026-00001' });
const conPagos = () => reserva({ cliente: 'Ana Pérez' });
const sinPagos = () => reserva({ cliente: 'Ana Pérez', estado: 'pre_reservada', cuotas: cuotasSinPagos(), pagado: '0.00', vence_pago: new Date(AHORA.getTime() + 864e5).toISOString() });

for (const t of tamanos) {
  test(`cancelar (Administrador): sin opción elegida pide elegir y no envía, a ${t.nombre}`, async ({ page }) => {
    await page.setViewportSize({ width: t.ancho, height: t.alto });
    await con(page, conPagos());
    const llamadas = await simular(page, 'POST', `/reservas/${ID}/cancelar`, json(200, cancelada(3)));
    await ver(page);
    await abrirCancelar(page).click();
    await expect(page.getByRole('heading', { name: /Cancelar reserva R-2026-00001/ })).toBeFocused();
    const grupo = panelC(page).getByRole('group', { name: '¿Quién pide cancelar?' });
    await expect(grupo.getByRole('radio')).toHaveCount(2);
    await expect(grupo.getByRole('radio', { checked: true })).toHaveCount(0);
    await expect(grupo).toContainText('Falla técnica, ausencia del especialista o fuerza mayor.');
    await expect(grupo).toContainText('Te escribió por WhatsApp, correo o teléfono.');
    await confirmarC(page).click();
    await expect(page.getByText('Elige quién pide cancelar.').first()).toBeVisible();
    expect(llamadas).toHaveLength(0);
    await sinViolaciones(page);
    await page.screenshot({ path: `pruebas/capturas/rf18-cancelar-admin-${t.nombre}.png`, fullPage: true });
  });
}

test('cancelar por el estudio con pagos: la nota es obligatoria y las consecuencias explican las dos opciones', async ({ page }) => {
  const consola = vigilarConsola(page);
  await con(page, conPagos());
  const llamadas = await simular(page, 'POST', `/reservas/${ID}/cancelar`, json(200, reserva({ estado: 'cancelada', motivo_cancelacion: 'administrador', cliente: 'Ana Pérez', cuotas: cuotasPagadas({}, { estado: 'anulada' }), cancelacion: { nivel: null, aviso_en: '2026-11-15T10:00:00-05:00', por: 'estudio', pagado: '100.00', retenido: '0.00', credito: '0.00', nota: 'Falla técnica' } })));
  await ver(page);
  await abrirCancelar(page).click();
  await panelC(page).getByRole('radio', { name: /El estudio/ }).check();
  await expect(panelC(page)).toContainText('El horario se libera al momento. El cliente elegirá en la app entre reprogramar sin costo o la devolución íntegra de S/ 100,00, que haces en un máximo de 7 días hábiles. Le avisamos por correo.');
  await expect(page.getByLabel(/Nota para el cliente/)).toHaveAttribute('maxlength', '300');
  await expect(page.getByLabel(/Fecha del aviso/)).toBeHidden();
  await confirmarC(page).click();
  await expect(page.getByText('Escribe la nota para el cliente.').first()).toBeVisible();
  await expect(page.getByLabel(/Nota para el cliente/)).toHaveAttribute('aria-invalid', 'true');
  expect(llamadas).toHaveLength(0);
  await page.getByLabel(/Nota para el cliente/).fill('Falla técnica');
  await confirmarC(page).click();
  expect(llamadas[0].cuerpo).toEqual({ por: 'estudio', nota: 'Falla técnica' });
  await expect(aviso(page)).toContainText('Reserva cancelada. El horario quedó libre y avisamos al cliente para que elija entre reprogramar sin costo o la devolución íntegra.');
  await expect(aviso(page)).toBeFocused();
  await expect(page.getByRole('region', { name: /D4 Cancelación/i })).toContainText('Del estudio');
  await sinViolaciones(page);
  expect(consola).toEqual([]);
});

test('cancelar por el estudio sin pagos: la nota es opcional y no se manda vacía', async ({ page }) => {
  await con(page, sinPagos());
  const llamadas = await simular(page, 'POST', `/reservas/${ID}/cancelar`, json(200, reserva({ estado: 'cancelada', motivo_cancelacion: 'administrador', cliente: 'Ana Pérez', cuotas: cuotasSinPagos(), pagado: '0.00' })));
  await ver(page);
  await abrirCancelar(page).click();
  await panelC(page).getByRole('radio', { name: /El estudio/ }).check();
  await expect(panelC(page)).toContainText('El horario se libera al momento y avisamos al cliente por correo.');
  await confirmarC(page).click();
  expect(llamadas[0].cuerpo).toEqual({ por: 'estudio' });
  await expect(aviso(page)).toContainText('Reserva cancelada. El horario quedó libre y avisamos al cliente por correo.');
});

test('cancelar a pedido del cliente: fecha y hora del aviso, vista previa con ?aviso_en= y envío', async ({ page }) => {
  const consola = vigilarConsola(page);
  await con(page, conPagos());
  const previas = await simular(page, 'GET', `/reservas/${ID}/cancelacion`, json(200, vista(2)));
  const base = cancelada(2);
  const llamadas = await simular(page, 'POST', `/reservas/${ID}/cancelar`, json(200, { ...base, cliente: 'Ana Pérez', cancelacion: { ...base.cancelacion, nota: 'WhatsApp: no puede venir' } }));
  await ver(page);
  await abrirCancelar(page).click();
  await panelC(page).getByRole('radio', { name: /El cliente, por otro canal/ }).check();
  await expect(panelC(page)).toContainText('Se aplica la misma política que si cancelara desde la app, con el nivel que corresponde a la fecha y hora de su mensaje.');
  await expect(panelC(page)).toContainText('Las de su mensaje, hora de Lima.');
  await expect(panelC(page)).toContainText('Canal y lo que pidió.');
  await page.getByLabel(/Fecha del aviso/).fill('2026-11-14');
  await page.getByLabel(/Hora del aviso/).fill('10:00');
  await expect(panelC(page)).toContainText('Nivel 2: avisas entre 24 y 48 h antes.');
  await expect(panelC(page)).toContainText('Faltan 1 d 6 h para la sesión.');
  expect(previas.at(-1).url.searchParams.get('aviso_en')).toBe('2026-11-14T10:00:00-05:00');
  await sinViolaciones(page);
  await page.screenshot({ path: 'pruebas/capturas/rf18-cancelar-admin-cliente-1440.png', fullPage: true });
  await confirmarC(page).click();
  await expect(page.getByText('Escribe la nota para el cliente.').first()).toBeVisible();
  expect(llamadas).toHaveLength(0);
  await page.locator('#cancelar-nota-cliente').fill('WhatsApp: no puede venir');
  await confirmarC(page).click();
  expect(llamadas[0].cuerpo).toEqual({ por: 'cliente', nota: 'WhatsApp: no puede venir', aviso_en: '2026-11-14T10:00:00-05:00' });
  await expect(aviso(page)).toContainText('Reserva cancelada a pedido del cliente (nivel 2). Le avisamos con el detalle.');
  await expect(page.getByRole('region', { name: /D4 Cancelación/i })).toContainText('WhatsApp: no puede venir');
  await sinViolaciones(page);
  expect(consola).toEqual([]);
});

test('cancelar a pedido del cliente: sin fecha no hay envío y 422 aviso_invalido va bajo la fecha', async ({ page }) => {
  await con(page, conPagos());
  await simular(page, 'GET', `/reservas/${ID}/cancelacion`, (r) => r.fulfill(errorApi(422, 'aviso_invalido')));
  const llamadas = await simular(page, 'POST', `/reservas/${ID}/cancelar`, (r) => r.fulfill(errorApi(422, 'aviso_invalido')));
  await ver(page);
  await abrirCancelar(page).click();
  await panelC(page).getByRole('radio', { name: /El cliente, por otro canal/ }).check();
  await page.locator('#cancelar-nota-cliente').fill('WhatsApp');
  await confirmarC(page).click();
  await expect(page.getByText('Elige la fecha y la hora del aviso.').first()).toBeVisible();
  expect(llamadas).toHaveLength(0);
  await page.getByLabel(/Fecha del aviso/).fill('2030-01-01');
  await page.getByLabel(/Hora del aviso/).fill('10:00');
  await expect(page.getByText('El aviso no puede ser futuro ni anterior a cuando se hizo la reserva.').first()).toBeVisible();
  await expect(page.getByLabel(/Fecha del aviso/)).toHaveAttribute('aria-invalid', 'true');
  await confirmarC(page).click();
  await expect(page.getByText('El aviso no puede ser futuro ni anterior a cuando se hizo la reserva.').first()).toBeVisible();
  expect(llamadas).toHaveLength(1);
  await sinViolaciones(page);
});

test('cancelar (Administrador): nota de más de 300 caracteres, 409 no_cancelable y Escape', async ({ page }) => {
  let lecturas = 0;
  await simular(page, 'GET', `/reservas/${ID}`, (r) => r.fulfill(json(200, lecturas++ ? reserva({ estado: 'en_curso', cliente: 'Ana Pérez' }) : conPagos())));
  await simular(page, 'POST', `/reservas/${ID}/cancelar`, (r) => r.fulfill(errorApi(409, 'no_cancelable')));
  await ver(page);
  await abrirCancelar(page).click();
  await page.keyboard.press('Escape');
  await expect(abrirCancelar(page)).toBeFocused();
  await abrirCancelar(page).click();
  await panelC(page).getByRole('radio', { name: /El estudio/ }).check();
  await page.getByLabel(/Nota para el cliente/).evaluate((e) => { e.value = 'x'.repeat(301); });
  await confirmarC(page).click();
  await expect(page.getByText('La nota admite hasta 300 caracteres.').first()).toBeVisible();
  await page.getByLabel(/Nota para el cliente/).fill('Falla técnica');
  await confirmarC(page).click();
  await expect(aviso(page)).toContainText('Esta reserva ya no se puede cancelar: está en curso.');
  await expect(panelC(page)).toBeHidden();
});

// --- Agenda ---
const hoy = (hhmm) => `2026-11-15T${hhmm}:00-05:00`;
const fila = (id, folio, extra = {}) => ({ id, folio, estado: 'confirmada', inicio: hoy('09:40'), fin: hoy('11:30'), sala: 'La Molina', servicio: 'Grabación', cliente: 'Ana Pérez', politica: { minutos_tolerancia_inasistencia: 15 }, pagado: '100.00', ...extra });
const montarAgenda = async (page, reservas, rol = 'personal') => {
  await comoRol(page, rol);
  await page.route(`${API}/salas`, (r) => r.fulfill(json(200, [{ id: 'sala-1', nombre: 'La Molina' }])));
  await page.route(`${API}/reservas?**`, (r) => r.fulfill(json(200, reservas)));
};

test('agenda: LISTA suma NO ASISTIÓ y la acción "Marcar no asistió" solo dentro de la ventana', async ({ page }) => {
  const consola = vigilarConsola(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await montarAgenda(page, [
    fila('r1', 'R-1'),
    fila('r2', 'R-2', { inicio: hoy('09:50') }),
    fila('r3', 'R-3', { estado: 'no_asistio', inicio: hoy('08:00'), fin: hoy('09:00') }),
    fila('r4', 'R-4', { estado: 'finalizada', inicio: hoy('07:00'), fin: hoy('08:00') }),
    fila('r5', 'R-5', { estado: 'en_curso' }),
  ]);
  await page.goto('/app/agenda/?vista=lista&fecha=2026-11-15');
  const f = (folio) => page.getByRole('row', { name: new RegExp(folio) });
  await expect(f('R-1').getByRole('link', { name: 'Marcar no asistió · R-1' })).toHaveAttribute('href', `/app/reservas/detalle?id=r1&accion=inasistencia`);
  await expect(f('R-2').getByRole('link', { name: /Marcar no asistió/ })).toHaveCount(0);
  await expect(f('R-3')).toContainText('No asistió');
  await expect(f('R-3').getByRole('link', { name: /Marcar no asistió/ })).toHaveCount(0);
  await expect(f('R-4').getByRole('link', { name: /Marcar no asistió/ })).toHaveCount(0);
  await expect(f('R-5').getByRole('link', { name: 'Marcar no asistió · R-5' })).toBeVisible();
  await sinViolaciones(page);
  expect(consola).toEqual([]);
  await page.screenshot({ path: 'pruebas/capturas/rf18-agenda-lista-1440.png', fullPage: true });
});

test('agenda: la cuadrícula muestra NO ASISTIÓ como estado en texto', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await comoRol(page, 'administrador');
  await page.route(`${API}/salas`, (r) => r.fulfill(json(200, [{ id: 'sala-1', nombre: 'La Molina' }])));
  await page.route(`${API}/disponibilidad?**`, (r) => r.fulfill(json(200, {
    limites: { desde: hoy('08:00'), hasta: '2026-12-15T10:00:00-05:00' },
    franjas: [{ id: 'f1', inicio: hoy('08:00'), fin: hoy('14:00') }],
    ocupados: [{ inicio: hoy('08:00'), fin: hoy('09:00'), propia: false, detalle: { id_reserva: 'r3', cliente: 'Ana Pérez', servicio: 'Grabación', estado: 'no_asistio' } }],
    cierres: [], dias: ['09', '10', '11', '12', '13', '14', '15'].map((d) => ({ fecha: `2026-11-${d}`, minutos_libres: 0 })),
  })));
  await page.goto('/app/agenda/?vista=semana&fecha=2026-11-15');
  await expect(page.getByRole('link', { name: /Ana Pérez/ })).toContainText('No asistió');
  await sinViolaciones(page);
});
