---
id: operacion-pruebas-locales
titulo: Pruebas en el entorno de desarrollo
estado: borrador
depende_de: [operacion-montaje-local, protocolo-pruebas]
---

# Pruebas en el entorno de desarrollo

Qué se prueba y con qué criterio: [pruebas](../05-protocolos/pruebas.md). Aquí, cómo se ejecuta con el entorno de [montaje-local](montaje-local.md).

## Backend (desde `backend/`)

```bash
uv run pytest               # unitarias + integración contra el stack local
uv run pytest -m "not integracion"   # solo unitarias (no necesitan Supabase)
uv run ruff check .
uv run mypy src
```

Las pruebas de integración se saltan, con un mensaje, si el stack local no responde; con `EXIGIR_INTEGRACION=1`, fallan.

## Base de datos (pgTAP)

Desde la raíz, con el stack en marcha: `npx supabase test db` (pruebas en `supabase/tests/`).

## Frontend (desde `frontend/`)

```bash
npm run check               # tokens, literales visuales y astro check
npm run build               # salida estática en dist/
npm run test:e2e            # Playwright + axe; construye el sitio y simula la API con page.route
```

`test:e2e` no necesita backend ni Supabase (usa valores ficticios) y deja capturas en `frontend/pruebas/capturas/`. La primera vez, instala el navegador con `npx playwright install chromium`. Usa los puertos 4321 y 4322; con `PUERTO_PRUEBAS` corre en otros. `/catalogo` existe en `npm run dev` y en el build de pruebas (`PUBLIC_CATALOGO=1`, en `dist-pruebas/`, lo activa `test:e2e`); nunca en `npm run build`.

## Recorridos reales (sin `page.route`)

`npm run test:e2e:real` (aparte de `test:e2e`, que lo ignora). Necesita el stack de Supabase local con Mailpit, `backend/.env` (con `URL_BASE_DATOS_ADMIN`) y `frontend/.env`, y `uv` instalado. La config `playwright.real.config.js` levanta el backend en el puerto 8010 (`uvicorn`, sin tocar el 8000) y `astro dev` en `localhost:4321` (el único origen al que Auth redirige) con `PUBLIC_URL_API` apuntando al 8010; el puerto 4321 debe estar libre. Sin stack, se salta; con `EXIGIR_INTEGRACION` definida, falla.

**RF-01:** `frontend/pruebas/real/rf01.real.spec.js` registra tres usuarios `rf01-*@prueba.bugalu.pe`, lee Mailpit por su API, promueve a uno con `crear_administrador` y, al terminar (pase o falle), `limpiar.py` los borra con `URL_BASE_DATOS_ADMIN` y comprueba que no quedan huérfanos. Las capturas quedan en `frontend/pruebas/capturas/real-rf01-*.png`.

**Reservas:** el mismo `npm run test:e2e:real` ejecuta también `frontend/pruebas/real/reservas.real.spec.js` (RF-02 CA-05, RF-03, RF-04). Necesita lo mismo que RF-01 más la bandeja de correos: la config real arranca el backend con `INTERVALO_ENVIO_CORREOS=2` (SMTP por defecto `127.0.0.1:45625`, el de Mailpit) para que `reserva_creada` y `reserva_caducada` lleguen a Mailpit en segundos; si lo lanzas a mano, usa esa variable o `uv run python -m bugalu.herramientas.enviar_correos`. Las fechas se calculan desde ahora en Lima (martes y miércoles de la semana siguiente, dentro de la ventana de 2 h a 8 semanas), así que no depende del día en que se corra. Seis pasos en serie: (1) un Administrador (promovido con `crear_administrador`) publica franjas en `/app/franjas/` desde la plantilla editable; (2) un visitante elige horario, servicio y un especialista adicional en `/reservar/`, el total de la simulación coincide con `POST /simulaciones`, se registra desde el acceso y confirma; (3) el correo llega a Mailpit con folio y fecha límite; (4) `/app/reservas/`, tramo OCUPADO para otro cliente sin datos del primero y agenda del Administrador; (5) cancelación desde el detalle y tramo libre; (6) caducidad: `frontend/pruebas/real/caducar.py <folio>` pone `vence_pago` en el pasado y corre `caducar_reservas()` con `URL_BASE_DATOS_ADMIN`. Requiere el catálogo del seed (sala, "Grabación de voces", "Productor o arreglista") y que la semana siguiente no tenga franjas publicadas. Al terminar (pase o falle), `limpiar.py` borra usuarios `res-*@prueba.bugalu.pe`, reservas (con cuotas y especialistas), avisos, franjas y cierres que crearon y comprueba que no quedan huérfanos. Capturas: `frontend/pruebas/capturas/real-reservas-*.png`.

**Pagos:** el mismo `npm run test:e2e:real` ejecuta `frontend/pruebas/real/pagos.real.spec.js` (RF-05 CA-01..09, RF-06 CA-01..05). Necesita lo de reservas más `CLAVE_SERVICIO_SUPABASE_PRUEBAS` (entorno o `backend/.env`; sin ella se salta, o falla con `EXIGIR_INTEGRACION`) y los métodos de pago activos del seed (Yape, contacto del estudio). Seis pasos en serie, con usuarios `pag-*@prueba.bugalu.pe`: (1) el Administrador publica franjas y el cliente reserva; (2) el cliente registra el pago de `al_reservar` con un PNG real y ve "Pago en validación" y "Pago por validar"; llega `pago_registrado` al Administrador; (3) el Administrador ve el contador de PAGOS, la captura cargada desde la URL firmada de Storage y rechaza con motivo; llega `pago_rechazado` y el detalle muestra el motivo; (4) el cliente registra otro pago con un PDF y ve el aviso y el contacto del estudio en lugar de Cancelar; el Administrador lo aprueba, la reserva queda Confirmada y llega `pago_aprobado` con "confirmada"; (5) el Administrador cancela con nota obligatoria; el cliente ve la nota y llega `reserva_cancelada_estudio`; (6) `frontend/pruebas/real/finalizar.py <folio>` deja una segunda reserva confirmada con la sesión ya terminada (SQL de administración, en medias horas) y corre `avanzar_reservas()`: `Finalizada` con `reserva_finalizada_saldo`, saldo y "Registrar pago" en el historial. Al terminar (pase o falle), `capturas.py` lista los ids de los usuarios, se borran sus objetos de `comprobantes` por la API de Storage con la clave de servicio, `limpiar.py` borra usuarios, reservas, cuotas, comprobantes, avisos y franjas, y el recorrido falla si queda algún huérfano en la base o en el bucket. El número de operación se guarda en mayúsculas. Capturas: `frontend/pruebas/capturas/real-pagos-*.png`.

**Cambios sensibles (RF-20):** el mismo `npm run test:e2e:real` ejecuta `frontend/pruebas/real/cambios-sensibles.real.spec.js` (CA-04 a CA-09), con usuarios `cam-*@prueba.bugalu.pe` y las mismas fechas calculadas desde ahora. Siete pasos en serie: (1) un Administrador publica franjas, un cliente reserva (reserva A) y se anotan los valores iniciales (tarifa de "Grabación de voces", IGV, `porcentaje_adelanto`) y el número de filas del registro; (2) el Administrador cambia la tarifa en `/app/tarifas/servicio`, ve antes/después e impacto, escribe CONFIRMAR y aplica: una simulación nueva usa la tarifa nueva y la reserva A conserva su precio; (3) en `/app/tarifas/impuestos` pasa el IGV a "no incluido" con otro porcentaje: la simulación nueva muestra subtotal, más IGV y total en ese orden y la reserva A conserva su desglose; (4) cambia el adelanto en `/app/franjas/parametros` y una reserva nueva usa el adelanto nuevo, la A el anterior; (5) `/app/cambios` muestra cada cambio con autor, antes y después (y la API suma exactamente 4 filas); (6) un `PATCH` directo con un campo sensible (también mezclado con uno no sensible) responde 428 por `fetch` desde la página con el token del Administrador y no cambia nada; (7) restaura los tres valores por el mismo flujo y comprueba que la simulación vuelve al precio inicial y que el registro suma 8 filas. Es la única prueba que cambia datos compartidos del catálogo: corre sola contra la base (no en paralelo con otro recorrido) y, si un paso falla, `afterAll` restaura por la API (vista previa y confirmación) antes de `limpiar.py`. El registro de cambios es inmutable: no se limpia, solo se cuenta de forma relativa. La API no expone `parametros_aplicados` de la reserva: el adelanto guardado se comprueba por `precio.porcentaje_adelanto` y `precio.anticipo`. Capturas: `frontend/pruebas/capturas/real-rf20-*.png`.

## Documentación

```bash
python scripts/validar_docs.py docs --ids-desde docs/superpowers/specs/PROYECTO-v0.2.md
python -m unittest scripts/test_validar_docs.py
```
