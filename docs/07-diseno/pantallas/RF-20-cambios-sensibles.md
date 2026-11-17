---
id: pantalla-rf-20-cambios-sensibles
titulo: Pantalla — Cambios sensibles con barreras, impuestos y desglose de IGV
estado: borrador
depende_de: [RF-20, RF-02, RF-03, ADR-013, ADR-015, diseno-brief, patron-formularios, patron-estados-sistema, comp-tabla, comp-panel, comp-campo, comp-casilla, comp-barra-acciones, comp-aviso, comp-boton]
---

# Cambios sensibles, impuestos y desglose de IGV

| Campo | Valor |
|---|---|
| Requerimiento | [RF-20](../../03-requerimientos/RF-20.md): CA-01 a CA-07, CA-09, CA-10 (el registro, en [registro de cambios](RF-20-registro-cambios.md)) |
| Actores | Administrador (cambia); Visitante y Artista/Cliente (ven el desglose) |
| Estructura | App, panel interno, dentro de las vistas de [tarifas](RF-02-tarifas.md) y [parámetros](RF-03-franjas.md); el desglose, donde ya hay precio |
| Ruta | Las existentes + `/app/tarifas/impuestos` (URL: `aviso`). El paso de revisión **no tiene URL** (ver decisión) |
| Isla | `<bugalu-cambio-sensible>` (nueva, la monta `<bugalu-tarifas>` o `<bugalu-franjas>`); `<bugalu-tarifas vista="impuestos">` (vista nueva) |
| Origen Figma | Ninguno ([brecha](../figma.md#brecha-detectada)) |

**Decisión del brief:** la revisión es un estado de la vista, no una página: su token caduca a los 10 min y llevar los valores propuestos en la URL los expondría al historial. Recargar devuelve al formulario sin cambios aplicados.

## Flujo con barreras

1. El Administrador edita como hoy y pulsa el botón de guardar de la vista. La isla de la vista compara con lo cargado: **sin campos sensibles cambiados** (tabla abajo), guarda en un paso como hoy.
2. **Con alguno cambiado**, el botón pasa a Carga ("Calculando impacto…") y la isla monta `<bugalu-cambio-sensible>` con `POST /cambios-sensibles/previsualizar {recurso, id_recurso?, cambios}`: solo los sensibles (en `parametros`, todos los cambios). Red de seguridad: si el endpoint de siempre responde 428 `confirmacion_requerida`, se hace lo mismo con `detalles.campos`.
3. Los paneles de la vista se ocultan y aparece la revisión (C1, C2, C3); el foco va al `<h2>` de C1.
4. Escribe CONFIRMAR y pulsa "Aplicar cambio" → `POST /cambios-sensibles/confirmar {token, palabra}`. O pulsa "Cancelar": vuelve al formulario con lo que escribió, nada guardado, aviso Información "No se aplicó ningún cambio." y foco en el botón de guardar.
5. Al confirmar (200), si quedaban cambios no sensibles (`activo`, especialistas por defecto) la isla los envía al endpoint de siempre; luego, el éxito de la vista.

| Vista | Campos sensibles (etiqueta en C1 · formato) |
|---|---|
| Servicio (S2) | TARIFA POR HORA, MONTO FIJO · importe |
| Especialista (E2) | MONTO FIJO, MONTO VARIABLE · importe; UNIDAD · "Por hora" / "Por media hora" |
| Recargos (R1) | NOCHE (%), FIN DE SEMANA (%), FERIADO (%) · porcentaje; NOCHE DESDE / HASTA · `HH:mm`. Los feriados (R2) no pasan por aquí |
| Parámetros | DÍAS ANTES DEL INICIO · "N días"; HORAS DESDE LA SOLICITUD, LÍMITE DEL NIVEL 1 y 2 · "N h"; ADELANTO PARA CONFIRMAR · porcentaje. La anticipación (P2) sola no pasa por aquí |
| Impuestos | PORCENTAJE DE IGV · porcentaje; LOS PRECIOS INCLUYEN IGV · "Sí" / "No" |

Formatos: [formato de datos](../patrones/estructura-app.md#formato-de-datos) (porcentaje "18 %", importe `S/ 120,00`). `anterior` y `nuevo` llegan como texto; la isla solo los formatea.

### Composición de la revisión

| Panel | Componente (variante) | Contenido |
|---|---|---|
| `C1 QUÉ CAMBIA` | [panel](../componentes/panel.md) Base + [tabla](../componentes/tabla.md) Compacta | Ayuda: `nombre_recurso`. CAMPO · ANTES · DESPUÉS; DESPUÉS en `fuente-peso-titulo` (la diferencia no se marca solo con color) |
| `C2 IMPACTO` | panel Base + tabla Partidas | EJEMPLO · ANTES · DESPUÉS (`impacto.ejemplos`, `concepto` tal cual) → [aviso](../componentes/aviso.md) Información con `operaciones_vigentes` |
| `C3 CONFIRMAR` | panel Base + [campo](../componentes/campo.md) Texto + [barra de acciones](../componentes/barra-acciones.md) Formulario | ESCRIBE CONFIRMAR (`autocomplete="off"`, `autocapitalize="characters"`, `spellcheck="false"`; se puede pegar) → "Cancelar" (Secundario grande) + "Aplicar cambio" (Primario grande) |

"Aplicar cambio" lleva `aria-disabled="true"` (sigue enfocable) hasta que el campo, sin espacios a los extremos, sea exactamente `CONFIRMAR`; pulsarlo antes muestra el error del campo. "Cancelar" tiene el mismo tamaño y peso visual (CA-09). Una sola columna también en escritorio: la revisión se lee de arriba abajo.

### Estados de la revisión

| Situación | Forma y texto |
|---|---|
| Calculando | Botón de guardar en Carga "Calculando impacto…"; los demás envíos de la vista, deshabilitados |
| Previsualizar 422 `datos_invalidos` (`detalles.campo`) | Vuelve al formulario con el error bajo ese campo (textos de la vista) y el resumen de errores |
| 422 `plazos_incoherentes` | Formulario; bajo LÍMITE DEL NIVEL 2: "Debe ser menor que el límite del nivel 1 ({n} h)." (también se valida al enviar) |
| 422 `sin_cambios` | Formulario; aviso Información "Ya tiene esos valores. No hay nada que cambiar." |
| 404 | Aviso Información de la vista ("No encontramos este servicio.") + "Volver a tarifas" |
| Aplicando | "Aplicar cambio" en Carga "Aplicando…"; "Cancelar" deshabilitado |
| Palabra distinta (local o 422 `palabra_incorrecta`) | Error bajo el campo: "Escribe CONFIRMAR, en mayúsculas, para aplicar el cambio." El token sigue vigente |
| 409 `confirmacion_no_valida` (caducó o ya se usó) | La isla pide otra vista previa con los mismos cambios y la repinta; aviso Información "La vista previa caducó y la actualizamos. Revisa el impacto y vuelve a aplicar." Conserva lo escrito: así no hay límite de tiempo que haga perder el trabajo (WCAG 2.2.1) |
| 409 `cambio_desactualizado` | Nueva vista previa; aviso Aviso "Otro administrador cambió {nombre_recurso} mientras revisabas. ANTES ya muestra los valores actuales: revísalos y vuelve a escribir CONFIRMAR." Campo vacío. Si la nueva vista previa da `sin_cambios`: formulario recargado y "Otro administrador ya aplicó estos mismos valores." |
| 403 al confirmar | Formulario; aviso Error "Esta vista previa la pidió otra cuenta. Vuelve a guardar para generar la tuya." |
| 401 · 503 · red · no JSON | Textos de la vista ([tarifas](RF-02-tarifas.md#estados)); nada aplicado y lo escrito se conserva |
| Éxito | El de la vista con la acción "Ver en el registro de cambios" (`/app/cambios?recurso=`). Recargos y parámetros se quedan en la vista con su aviso; servicio y especialista vuelven a la lista con su `?aviso=` |
| Confirmado pero falla el resto (paso 5) | Aviso Error "La tarifa se cambió, pero no pudimos guardar {Activo / Especialistas por defecto}. Vuelve a guardar." Formulario con los valores aplicados |

## Integración sin rehacer las pantallas

- [Tarifas](RF-02-tarifas.md): S2, E2 y R1 conservan campos, botones y avisos; bajo "Guardar servicio", "Guardar especialista" y "Guardar recargos" se añade la ayuda "Si cambias un importe o un porcentaje, te mostraremos el impacto y te pediremos confirmarlo." En Lista, la ranura `acciones` suma "Impuestos" (Secundario como enlace) junto a "Recargos y feriados".
- [Parámetros](RF-03-franjas.md): se añade el panel `P3 CANCELACIÓN Y ADELANTO` (LÍMITE DEL NIVEL 1 (HORAS), LÍMITE DEL NIVEL 2 (HORAS), ADELANTO PARA CONFIRMAR (%): `type="number"`, `step="1"`, obligatorios; adelanto de 1 a 100) antes de "Guardar parámetros", con la misma ayuda bajo el botón. Los parámetros sensibles de ADR-015 que aún no tienen nombre en el contrato se suman a P3 con RF-18.
- El aviso fijo de S2 y E2 y el éxito de parámetros ya dicen que solo cambian las reservas nuevas: se mantienen.

## Impuestos

Ruta Inicio / Tarifas / Impuestos · `[A8] CATÁLOGO / IMPUESTOS` · título IMPUESTOS · "El IGV que se aplica a los precios. Un cambio rige solo para las reservas nuevas."

| Región | Componente | Contenido |
|---|---|---|
| Principal | panel `I1 IGV` | PORCENTAJE DE IGV (%) (`type="number"`, `min="0"`, `max="99.99"`, `step="0.01"`, valor sin ceros de relleno) → `<fieldset>` LOS PRECIOS INCLUYEN IGV, [casillas](../componentes/casilla.md) Radio: "Sí" (detalle "El cliente ve el total; el IGV va desglosado dentro.") · "No" (detalle "Las tarifas son netas y el total suma el IGV.") → Primario "Revisar cambio" (siempre lleva a la revisión) |
| Lateral | panel Lateral `I2 CÓMO SE MUESTRA` | Texto fijo de CA-02: "Con IGV incluido, un total de S/ 150,00 al 18 % se muestra con base S/ 127,12 e IGV S/ 22,88. Los comprobantes se emiten fuera de la app." |

Datos: `GET /impuestos` → `Impuestos`. Validación: "Escribe un porcentaje de 0 a 99,99, con hasta dos decimales." Carga, 401, 403, 503 y sin JS: como [tarifas](RF-02-tarifas.md#estados). Éxito: "IGV actualizado. Rige para las simulaciones y reservas nuevas."

## Desglose de IGV

Origen: `Simulacion.impuesto` y `Reserva.precio.impuesto` (`{nombre, porcentaje, incluido, base, monto}`), `Pago.impuesto` (`{porcentaje, base, monto}`), `GET /impuestos`. El navegador nunca calcula base ni IGV.

| Dónde | Cambio |
|---|---|
| Tabla Partidas de [reservar](RF-04-reservar.md#datos) (02 y R2) y [mis reservas](RF-04-mis-reservas.md) (D2) | `incluido`: TOTAL → fila "Incluye IGV ({p} %)" con `monto` → ANTICIPO. No incluido: SUBTOTAL (`base`) → "IGV ({p} %)" → TOTAL → ANTICIPO. La fila del IGV va en `fuente-peso-regular` (no es un total) |
| Resumen persistente y Listo (05) | Bajo el total, `fuente-tamano-pequeno`: "Incluye IGV ({p} %): S/ 22,88" o "Más IGV ({p} %): S/ 22,88" |
| SERVICIO del paso 02 (las tarifas públicas) | Ayuda de la `<legend>`: "Precios con IGV incluido ({p} %)." o "Precios sin IGV: el IGV ({p} %) se suma al total." |
| [Registrar pago](RF-05-registrar-pago.md), lateral | Bajo IMPORTE DE LA CUOTA: "Incluye IGV ({p} %)." con el porcentaje de la reserva |
| [Pagos](RF-05-pagos.md), V2 PAGO | `<dl>` suma IGV INCLUIDO ({p} %): "S/ 11,44 · base S/ 63,56" y la nota "Informativo: el comprobante se emite fuera de la app." |

`{p}` es el porcentaje guardado en la operación, no el vigente (CA-03, CA-07).

## Accesibilidad

- Al abrir la revisión, el foco va al `<h2>` de C1; al cancelar, al botón de guardar; al fallar, al aviso. La región `role="status"` de la isla anuncia "Revisión lista: {n} cambios, {N} reservas vigentes conservan sus condiciones" y cada resultado.
- C1 y C2 son `<table>` con `<caption>` (QUÉ CAMBIA, IMPACTO) y `<th scope="row">` en CAMPO y EJEMPLO.
- La ayuda de ESCRIBE CONFIRMAR va en `aria-describedby`; "Aplicar cambio" explica su bloqueo con la misma ayuda.

## Pendientes

- **leader / dev-backend:** `impacto.ejemplos[].antes/despues` mezcla importes y fechas (plazos de pago): proponemos `tipo: "importe"|"fecha_hora"|"texto"` para formatearlos.
- **leader / dev-backend:** nombre de `campo` en `recargos` (anidado); proponemos `noche.porcentaje`, `noche.desde`, `fin_de_semana.porcentaje`…
- **leader / dev-backend:** la etiqueta "ANTICIPO 50 %" y "Al reservar · 50 %" deben salir de `porcentaje_adelanto`; proponemos exponerlo en `Simulacion` (en `Reserva` ya va en `parametros_aplicados`). `Cuota` sin `impuesto`: basta el porcentaje de la reserva (sin importe) salvo que se decida añadirlo.
- **leader:** nombres de los parámetros de ADR-015 (penalización, tolerancia, crédito, reprogramaciones) para P3 (RF-18).
