import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { ORIGEN } from './puertos.js';

const etiquetasAxe = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];
const anchos = [
  { nombre: 'escritorio', width: 1440, height: 900 },
  { nombre: 'movil', width: 390, height: 844 },
];

// Review Focus 1: 200 % de zoom equivale a la mitad de ancho CSS; 320 es el ancho de reflujo de WCAG 1.4.10.
const ampliados = [
  { nombre: 'zoom 200 % en escritorio', width: 720, height: 450, raiz: false },
  { nombre: 'reflujo 320 px', width: 320, height: 568, raiz: false },
  { nombre: 'letra de 20 px en escritorio', width: 1440, height: 900, raiz: true },
  { nombre: 'letra de 20 px en móvil', width: 390, height: 844, raiz: true },
];

const aplicarLetra20 = (page) => page.addStyleTag({ content: 'html { font-size: 20px; }' });

// Texto cortado: contenido que desborda a su caja; solapado: hermanos en flujo cuyas cajas se cruzan.
function buscarProblemas() {
  const problemas = [];
  const describir = (e) => `${e.tagName.toLowerCase()}.${[...e.classList].join('.')} "${(e.textContent ?? '').trim().slice(0, 30)}"`;
  const visible = (e) => e.getClientRects().length > 0 && !e.closest('.visualmente-oculto, .saltar');
  if (document.documentElement.scrollWidth > document.documentElement.clientWidth + 1) problemas.push('scroll horizontal del documento');
  for (const e of document.querySelectorAll('body *')) {
    if (e.namespaceURI !== 'http://www.w3.org/1999/xhtml' || !visible(e)) continue;
    if (e.scrollWidth > e.clientWidth + 1) problemas.push(`desborda: ${describir(e)}`);
    const hijos = [...e.children].filter((h) => visible(h) && !['absolute', 'fixed'].includes(getComputedStyle(h).position));
    // Un hijo en flujo que sale de la caja de su contenedor (altura fija) queda cortado o encima de lo siguiente.
    const caja = e.getBoundingClientRect();
    for (const h of hijos) {
      const r = h.getBoundingClientRect();
      if (r.height && (r.bottom > caja.bottom + 1 || r.top < caja.top - 1)) problemas.push(`sale de su caja: ${describir(h)} en ${describir(e)}`);
    }
    for (let i = 0; i < hijos.length; i++) {
      for (let j = i + 1; j < hijos.length; j++) {
        const a = hijos[i].getBoundingClientRect();
        const b = hijos[j].getBoundingClientRect();
        const cruce = Math.min(a.right, b.right) - Math.max(a.left, b.left) > 1 && Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 1;
        if (cruce && a.width && b.width && a.height && b.height) problemas.push(`se solapan: ${describir(hijos[i])} y ${describir(hijos[j])}`);
      }
    }
  }
  return problemas;
}

for (const ruta of ['/catalogo', '/app/']) {
  for (const { nombre, ...viewport } of anchos) {
    test.describe(`${ruta} ${viewport.width}px`, () => {
      test.use({ viewport });

      test('sin violaciones axe WCAG 2.2 AA y captura', async ({ page }) => {
        await page.goto(ruta);
        const { violations } = await new AxeBuilder({ page }).withTags(etiquetasAxe).analyze();
        expect(violations).toEqual([]);
        if (ruta === '/catalogo') await page.screenshot({ path: `pruebas/capturas/catalogo-${nombre}.png`, fullPage: true });
      });
    });
  }

  // Review Focus 1
  for (const { nombre, raiz, ...viewport } of ampliados) {
    test(`${ruta}: nada se corta ni se solapa con ${nombre}`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await page.goto(ruta);
      if (raiz) await aplicarLetra20(page);
      for (const resumen of await page.locator('summary:visible').all()) await resumen.click(); // menús móviles abiertos
      expect(await page.evaluate(buscarProblemas)).toEqual([]);
    });
  }
}

// Review Focus 2
for (const raiz of [false, true]) {
  test(`móvil: el foco nunca queda bajo lo fijo (letra ${raiz ? '20 px' : 'normal'})`, async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/app/');
    if (raiz) await aplicarLetra20(page);
    // Página larga con muchos elementos enfocables para forzar el desplazamiento al tabular.
    await page.evaluate(() => {
      const principal = document.querySelector('main');
      for (let i = 0; i < 40; i++) {
        const p = document.createElement('p');
        p.innerHTML = `<a href="#f${i}">Enlace de prueba ${i}</a><br><br><br><br>`;
        principal.append(p);
      }
    });
    const zona = () => page.evaluate(() => document.querySelector('.app-nav-tactil').getBoundingClientRect().bottom);
    const reserva = await page.evaluate(() => parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop));
    const revisar = async () => {
      const { arriba, enPrincipal } = await page.evaluate(() => ({
        arriba: document.activeElement.getBoundingClientRect().top,
        enPrincipal: Boolean(document.activeElement.closest('main')),
      }));
      if (enPrincipal) expect(arriba).toBeGreaterThanOrEqual((await zona()) - 0.5);
    };
    for (let i = 0; i < 46; i++) {
      await page.keyboard.press('Tab');
      await revisar();
    }
    // Lo fijo nunca supera la reserva de scroll-padding-top (medida-zona-fija-movil).
    expect(await zona()).toBeLessThanOrEqual(reserva + 1);
    for (let i = 0; i < 20; i++) {
      await page.keyboard.press('Shift+Tab');
      await revisar();
    }
  });
}

test('catalogo: HojaReclamacion en sus tres variantes y CargaArchivos variante reclamo', async ({ page }) => {
  await page.goto('/catalogo');
  await expect(page.locator('#g-hoja')).toBeVisible();
  await expect(page.locator('[data-hoja-catalogo] article.hoja')).toHaveCount(3);
  await expect(page.locator('[data-ejemplo="constancia"]')).toContainText('000000001-2026');
  await expect(page.locator('[data-ejemplo="confirmacion"]')).toContainText('Se asigna al enviar');
  await expect(page.locator('bugalu-carga-archivos[variante="reclamo"]')).toBeVisible();
});

// Review Focus 3
test('estados sin color: ARIA más icono, texto, borde o peso', async ({ page }) => {
  await page.goto('/catalogo');

  const filtro = page.locator('a[aria-current="true"]');
  await expect(filtro).toHaveCount(1);
  await expect(filtro.locator('svg')).toHaveCount(1); // check
  const bordes = await page.evaluate(() => [...document.querySelectorAll('a[href^="?estado"]')].map((a) => getComputedStyle(a).borderTopWidth));
  expect(bordes).toEqual(['1px', '2px']);

  const lateral = page.locator('nav[aria-label="Principal, ejemplo estudio"] a[aria-current="page"]');
  await expect(lateral).toHaveCount(1);
  expect(await lateral.evaluate((a) => getComputedStyle(a.querySelector('.lateral-etiqueta')).fontWeight)).toBe('700');
  expect(await lateral.evaluate((a) => getComputedStyle(a).borderTopColor)).not.toBe('rgba(0, 0, 0, 0)');

  const tactil = page.locator('nav[aria-label="Principal, ejemplo táctil"] a[aria-current="page"]');
  await expect(tactil).toHaveCount(1);
  expect(await tactil.evaluate((a) => getComputedStyle(a).borderBottomColor)).not.toBe('rgba(0, 0, 0, 0)');

  const campo = page.locator('#campo-cat-error');
  await expect(campo).toHaveAttribute('aria-invalid', 'true');
  const idError = await campo.getAttribute('aria-describedby');
  const mensaje = page.locator(`#${idError}`);
  await expect(mensaje.locator('svg')).toHaveCount(1);
  await expect(mensaje).toContainText('Escribe un correo completo');

  for (const variante of ['error', 'critico']) {
    const aviso = page.locator(`.aviso-${variante}`);
    await expect(aviso).toHaveAttribute('role', 'alert');
    await expect(aviso.locator('svg').first()).toBeVisible();
    await expect(aviso.locator('.aviso-titulo')).not.toBeEmpty();
  }

  const marcada = page.locator('input[name="cat-b"]');
  await expect(marcada).toBeChecked();
  await expect(marcada.locator('xpath=following-sibling::*[contains(@class,"marca-check")]')).toBeVisible();
  await expect(page.locator('input[name="cat-f"]')).toHaveAttribute('aria-invalid', 'true');
  await expect(page.locator('#cat-error-grupo svg')).toHaveCount(1);
});

test('foco visible en los componentes interactivos', async ({ page }) => {
  await page.goto('/catalogo');
  for (const selector of ['.boton-primario', '.campo-control', '.casilla-entrada', 'a.etiqueta-filtro', '.lateral-destino']) {
    await page.locator(selector).first().focus({ timeout: 2000 });
    await page.keyboard.press('Shift+Tab');
    await page.keyboard.press('Tab');
    const anillo = await page.evaluate(() => {
      const e = document.activeElement;
      const c = getComputedStyle(e);
      return { ancho: c.outlineWidth, estilo: c.outlineStyle, desplazamiento: c.outlineOffset };
    });
    expect(anillo, selector).toEqual({ ancho: '2px', estilo: 'solid', desplazamiento: '2px' });
  }
});

test('isla de contraseña: botón accesible con JS y campo funcional sin JS', async ({ page, browser }) => {
  await page.goto('/catalogo');
  const entrada = page.locator('#campo-cat-clave');
  const boton = page.locator('bugalu-contrasena').first().getByRole('button', { name: 'Mostrar contraseña' });
  await expect(boton).toHaveAttribute('aria-pressed', 'false');
  await boton.click();
  await expect(entrada).toHaveAttribute('type', 'text');
  // Nombre fijo: solo cambian aria-pressed y el icono.
  await expect(boton).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByRole('button', { name: 'Ocultar contraseña' })).toHaveCount(0);
  await boton.click();
  await expect(boton).toHaveAttribute('aria-pressed', 'false');
  await expect(entrada).toHaveAttribute('type', 'password');

  const sinJs = await browser.newContext({ javaScriptEnabled: false });
  const paginaSinJs = await sinJs.newPage();
  await paginaSinJs.goto(`${ORIGEN}/catalogo`);
  await expect(paginaSinJs.getByRole('button', { name: /contraseña/ })).toHaveCount(0);
  await paginaSinJs.locator('#campo-cat-clave').fill('secreta');
  await expect(paginaSinJs.locator('#campo-cat-clave')).toHaveValue('secreta');
  await sinJs.close();
});

test('hidden oculta cualquier componente aunque fije su propio display', async ({ page }) => {
  await page.goto('/catalogo');
  const mostrados = await page.evaluate(() => {
    const clases = ['.boton', '.aviso', '.etiqueta', '.campo', '.casilla', '.panel', '.tabla'];
    return clases.flatMap((c) => [...document.querySelectorAll(c)].slice(0, 1).map((e) => {
      e.hidden = true;
      return getComputedStyle(e).display === 'none' ? null : c;
    })).filter(Boolean);
  });
  expect(mostrados).toEqual([]);
});
