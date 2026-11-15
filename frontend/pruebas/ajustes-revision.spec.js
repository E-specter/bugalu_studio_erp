// Ajustes de la revision visual de RF-01 (TAREA-RF01-8): medidas y comportamientos comprobables.
import { test, expect } from '@playwright/test';
import { API, json, errorApi, perfil, conSesion, silenciarApi, solicitud } from './ayudas-acceso.js';

// Resuelve un token a pixeles (los tokens se leen del CSS real, no se repiten aqui).
const px = (page, token) =>
  page.evaluate((t) => {
    const sonda = Object.assign(document.createElement('div'), { style: `position:absolute;inline-size:var(${t});visibility:hidden` });
    document.body.append(sonda);
    const v = sonda.getBoundingClientRect().width;
    sonda.remove();
    return v;
  }, token);
const caja = (loc) => loc.evaluate((e) => { const r = e.getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height, b: r.bottom }; });

test.describe('layout Acceso (puntos 2 y 3)', () => {
  test('escritorio: logo a medida-logo-acceso, espacio-6 al titulo, etiquetas al pie sobre regla fina', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/acceso');
    const logo = await caja(page.locator('.acceso-logo svg'));
    expect(logo.h).toBeCloseTo(await px(page, '--medida-logo-acceso'), 0);
    const codigo = await caja(page.locator('.acceso-marca-texto:visible .acceso-codigo'));
    const logoEnlace = await caja(page.locator('.acceso-logo'));
    // Del logo (su contorno) al titulo: espacio-6.
    expect(codigo.y - logoEnlace.b).toBeCloseTo(await px(page, '--espacio-6'), 0);
    const etiquetas = page.locator('.acceso-marca-texto:visible .acceso-etiquetas');
    const marca = await caja(page.locator('.acceso-marca'));
    const e = await caja(etiquetas);
    const relleno = await px(page, '--espacio-8');
    expect(marca.b - e.b).toBeCloseTo(relleno, 0); // al pie
    const regla = await etiquetas.evaluate((el) => getComputedStyle(el).borderTopWidth);
    expect(regla).toBe(`${await px(page, '--borde-grosor-fino')}px`);
    await page.screenshot({ path: 'pruebas/capturas/acceso-marca-1440.png', fullPage: true });
  });

  test('movil: logo a medida-logo-min y sin hueco entre marca y formulario', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/acceso');
    const logo = await caja(page.locator('.acceso-logo svg'));
    expect(logo.h).toBeCloseTo(await px(page, '--medida-logo-min'), 0);
    const marca = await caja(page.locator('.acceso-marca'));
    const columna = await caja(page.locator('.acceso-columna'));
    expect(Math.abs(columna.y - marca.b)).toBeLessThanOrEqual(1);
    expect(marca.h).toBeLessThan(200);
  });
});

test('medidor: el icono de cada condicion queda centrado en la primera linea del texto', async ({ page }) => {
  for (const ancho of [1440, 390]) {
    await page.setViewportSize({ width: ancho, height: 900 });
    await page.goto('/acceso/registro');
    const filas = page.locator('[data-condicion]');
    for (let i = 0; i < (await filas.count()); i++) {
      const [icono, linea] = await filas.nth(i).evaluate((li) => {
        const centro = (r) => r.top + r.height / 2;
        const rango = document.createRange();
        rango.selectNodeContents(li.querySelector('span:not([data-icono])'));
        return [centro(li.querySelector('[data-icono] svg').getBoundingClientRect()), centro(rango.getClientRects()[0])];
      });
      expect(Math.abs(icono - linea), `condicion ${i} a ${ancho}`).toBeLessThanOrEqual(1);
    }
  }
});

test('restablecer con enlace caducado: tambien se oculta el texto de introduccion', async ({ page }) => {
  await page.goto('/acceso/nueva-contrasena');
  await expect(page.locator('.aviso-error')).toContainText('El enlace caducó o ya se usó.');
  await expect(page.getByText('Elige una contraseña nueva para tu cuenta.')).toBeHidden();
});

test.describe('Tu solicitud (punto 6)', () => {
  const MIA = `${API}/solicitudes-acceso/mia`;
  const estados = {
    pendiente: (r) => r.fulfill(solicitud()),
    rechazada: (r) => r.fulfill(solicitud({ estado: 'rechazada', motivo: 'Sin plazas.', revisada_en: '2026-11-12T10:00:00Z' })),
    formulario: (r) => r.fulfill(errorApi(404, 'no_encontrado')),
    error: (r) => r.fulfill(errorApi(503, 'x')),
  };
  for (const ancho of [1440, 390]) {
    test(`panel a todo el ancho de la columna y acciones en fila a su ancho natural a ${ancho}`, async ({ page }) => {
      await page.setViewportSize({ width: ancho, height: 900 });
      await conSesion(page);
      const anchos = [];
      for (const [n, r] of Object.entries(estados)) {
        await page.unrouteAll({ behavior: 'ignoreErrors' });
        await page.route(MIA, r);
        await page.goto('/acceso/interno/solicitud');
        await expect(page.locator('[data-salida] .panel')).toBeVisible();
        await expect(page.locator('[aria-busy]')).toHaveCount(0);
        const panel = await caja(page.locator('[data-salida] .panel'));
        const formulario = await caja(page.locator('.acceso-formulario'));
        anchos.push(panel.w);
        expect(panel.w, n).toBeCloseTo(formulario.w, 0);
        const botones = page.locator('.solicitud .acciones .boton:visible');
        const cuantos = await botones.count();
        if (cuantos < 2) continue;
        const bs = [];
        for (let i = 0; i < cuantos; i++) bs.push(await caja(botones.nth(i)));
        for (const b of bs) expect(b.w, n).toBeLessThan(panel.w - 40); // ninguno a ancho completo
        if (ancho === 1440) for (const b of bs) expect(Math.abs(b.y - bs[0].y), n).toBeLessThanOrEqual(1); // en fila
      }
      expect(new Set(anchos.map(Math.round)).size).toBe(1); // cambiar de estado no cambia el ancho
    });
  }
});

test.describe('estado neutro de la navegacion (punto 9)', () => {
  test('con GET /perfil lento y rol cliente nunca aparece PANEL INTERNO ni Estudio', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await conSesion(page);
    let soltar;
    const espera = new Promise((r) => (soltar = r));
    await page.route(`${API}/perfil`, async (r) => { await espera; await r.fulfill(perfil({ rol: 'cliente' })); });
    // Vigila en el propio navegador cada cambio de texto visible.
    await page.addInitScript(() => {
      window.__vistos = new Set();
      const mirar = () => document.querySelectorAll('[data-seccion],[data-area]').forEach((e) => getComputedStyle(e).visibility !== 'hidden' && e.textContent.trim() && window.__vistos.add(e.textContent.trim()));
      new MutationObserver(mirar).observe(document, { subtree: true, childList: true, characterData: true, attributes: true });
      setInterval(mirar, 20);
    });
    await page.goto('/app/');
    await page.waitForTimeout(400);
    for (const e of await page.locator('[data-seccion],[data-area]').all()) {
      await expect(e).toHaveCSS('visibility', 'hidden');
      await expect(e).toHaveText('');
    }
    soltar();
    await expect(page.locator('.lateral-seccion')).toHaveText('Portal');
    await expect(page.locator('.cabecera-area')).toHaveText('Portal del artista');
    expect((await page.evaluate(() => [...window.__vistos])).sort()).toEqual(['Portal', 'Portal del artista']);
  });

  test('si el perfil falla, titulo de seccion y area siguen ocultos', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await conSesion(page);
    await page.route(`${API}/perfil`, (r) => r.fulfill(errorApi(503, 'x')));
    await page.goto('/app/');
    await page.waitForTimeout(400);
    for (const e of await page.locator('[data-seccion],[data-area]').all()) {
      await expect(e).toHaveCSS('visibility', 'hidden');
      await expect(e).toHaveText('');
    }
  });
});
