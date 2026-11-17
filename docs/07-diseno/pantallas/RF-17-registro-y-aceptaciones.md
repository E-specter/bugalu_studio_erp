---
id: pantalla-rf-17-registro-y-aceptaciones
titulo: Pantalla — Aceptación de textos legales en el registro, la reserva y el pago (etapa A)
estado: borrador
depende_de: [RF-17, RF-01, RF-04, RF-05, ADR-012, ADR-015, RN-25, RN-26, diseno-brief, patron-flujo-por-pasos, patron-formularios, patron-estados-sistema, comp-resumen-legal, comp-casilla, comp-campo, comp-aviso, comp-barra-acciones, comp-boton, comp-panel]
---

# Registro y aceptaciones

| Campo | Valor |
|---|---|
| Requerimiento | [RF-17](../../03-requerimientos/RF-17.md), etapa A: CA-03, CA-04, CA-05, CA-07, CA-08, CA-13, CA-14. El perfil y los consentimientos: [perfil](RF-17-perfil.md); los textos y el Administrador: [textos legales](RF-17-textos-legales.md) |
| Actores | Artista/Cliente (y Visitante que se registra) |
| Estructura | Acceso para `/acceso/textos`; Flujo para los pasos de la [reserva](RF-04-reservar.md) |
| Ruta | `/acceso/textos?volver=` · `/reservar/cuenta?{elección}&aviso=` (nuevo paso 03 con página) · `/reservar/confirmar` · `/app/reservas/pagar` |
| Isla | `<bugalu-aceptacion>` (nueva); `<bugalu-reserva paso="cuenta">` (paso nuevo) y `paso="confirmar"`; `<bugalu-pago>` |

Todas las aceptaciones usan el [resumen legal](../componentes/resumen-legal.md): resumen visible, enlace a la versión y casilla **sin marcar**; no aceptar es tan fácil como aceptar (CA-13, D. Leg. 1729).

## Recorrido

1. **Registro:** el alta no cambia ([acceso](RF-01-acceso.md)). Al terminar el registro o un ingreso (también con Google), `<bugalu-acceso>` lee `GET /perfil`: si `pendientes` no está vacío y `volver` no es de `/reservar`, va a `/acceso/textos?volver=`. En la reserva lo resuelve el paso 03.
2. **`/acceso/textos`:** lee el resumen, marca la casilla y pulsa "Aceptar y continuar" (`POST /aceptaciones {contexto: "registro", textos}`) → `volver` o `/app/`. O pulsa "Ahora no" → mismo destino, sin registrar nada.
3. **Mientras falte** (incluida la **reaceptación** de una versión mayor de términos, CA-05): el script de `LayoutApp`, que ya carga el perfil, pinta al inicio del `<main>` un [aviso](../componentes/aviso.md) Aviso "Tienes textos por aceptar" + "Revisar y aceptar" (`/acceso/textos?volver={ruta actual}`). No es descartable; la persona sigue viendo, pagando y cancelando lo suyo.
4. **Reserva:** al cargar `/reservar/confirmar`, si `datos_para_reservar` es `false`, hay `pendientes` o `es_menor`, la isla va (`location.replace`) a `/reservar/cuenta` con la misma elección. Allí completa lo que falta y acepta lo pendiente → "Guardar y continuar" → paso 04.
5. **Paso 04:** lee el resumen de las condiciones, marca la casilla y confirma; la reserva guarda `version_condiciones`.
6. **Pago:** el resumen va junto a "Registrar pago", sin casilla.

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Pendientes | `GET /perfil` → `pendientes[].{tipo, version, contexto}`, `datos_para_reservar`, `es_menor` | — |
| Resumen y versión | `GET /textos-legales` → `TextoResumen` del `tipo` y `version` (el que no está `programada`) | Resumen tal cual; "versión 1.0.0" |
| ¿Primera vez o actualización? | `GET /aceptaciones/mias`: hay una aceptación anterior del mismo `tipo` | Elige título y descripción (Copy) |
| Datos que faltan (paso 03) | `Perfil.nombre`, `documento`, `telefono` → `PATCH /perfil` | Solo los vacíos: NOMBRE; DOCUMENTO (TIPO Selector + NÚMERO, en fila); TELÉFONO. Reglas y textos de error del [perfil](RF-17-perfil.md#datos) |
| Menor | `PATCH /perfil {es_menor}` | [Casilla](../componentes/casilla.md) "Soy menor de 18 años", sin marcar |
| Contacto | `GET /contacto-estudio` → `texto` | Tal cual; vacío → sin línea |
| Reserva | `POST /reservas {…, version_condiciones}` | Versión del resumen mostrado |

## Composición

| Vista | Región | Componente (variante) | Contenido |
|---|---|---|---|
| `/acceso/textos` | Marca y visual | Los del [acceso](RF-01-acceso.md#composición) | Sin cambios |
| `/acceso/textos` | Formulario | [Etiqueta](../componentes/etiqueta-tecnica.md) Invertida "CUENTA", `<h1>`, descripción, resumen legal Obligatoria (uno por texto pendiente; términos y política comparten casilla), [botones](../componentes/boton.md) Primario grande "Aceptar y continuar" y Secundario grande "Ahora no", ambos a ancho completo y apilados | El Secundario va **debajo** del Primario con el mismo tamaño |
| Paso 03 | Principal | [panel](../componentes/panel.md) `D1 TUS DATOS` (solo si faltan) → panel `D2 TÉRMINOS` (solo si hay pendientes) | Campos que faltan + casilla de menor; resumen legal Obligatoria |
| Paso 03 | Cierre | [Barra de acciones](../componentes/barra-acciones.md) Flujo | "Anterior" + "Guardar y continuar"; [resumen persistente](../componentes/resumen-persistente.md) como en 01 y 02 |
| Paso 04 | Principal | `R4 PAGO Y CANCELACIÓN` pasa a `R4 CONDICIONES` | Resumen legal Obligatoria de `condiciones_contratacion` (sustituye al texto de R4) |
| Pago | Principal, antes de la barra | Resumen legal Lectura "REGISTRO DE UN PAGO" | Resumen y enlace del [resumen de pago](../../08-legal/resumenes-para-pantallas.md#registro-de-un-pago) |

El paso 03 sigue siendo CUENTA en [pasos](../componentes/pasos.md): sin sesión es el acceso; con datos completos y nada pendiente se salta y queda HECHO. Así no se pasa de cinco pasos.

## Estados

| Situación | Forma y texto |
|---|---|
| Cargando textos | Bloque con "Cargando…", `aria-busy`; la acción que depende, deshabilitada |
| Textos no cargan (503, red) | Aviso Error del bloque + "Reintentar"; acción deshabilitada con "Necesitamos mostrarte las condiciones antes de continuar." |
| `/acceso/textos` sin pendientes | `location.replace(volver)` |
| Casilla obligatoria sin marcar | Error de grupo: "Marca la casilla para aceptar los términos; sin ella no podemos activar tus reservas." · en 04: "… las condiciones; sin ella no podemos registrar tu reserva." |
| 409 `texto_desactualizado` | Estado del [resumen legal](../componentes/resumen-legal.md#estados): versión nueva, casilla desmarcada, foco al aviso del bloque |
| Aceptado | `/acceso/textos` → `volver` con `?aviso=textos-aceptados`: aviso Éxito "Listo. Ya puedes reservar." |
| Menor (al cargar el paso 03 o tras guardar con la casilla) | D1 y D2 se sustituyen por un aviso Crítico "Aún no puedes reservar en línea" + "Como eres menor de 18 años, tu madre, padre o tutor tiene que autorizar la reserva, y eso todavía no se puede hacer en la app. Escríbenos y reservamos contigo:" + contacto; acción "Volver al inicio". La barra solo conserva "Anterior" |
| 04 → 409 `perfil_incompleto` / `reaceptacion_requerida` / `autorizacion_menor_pendiente` | Paso 03 con `?aviso=faltan-datos` · `textos-pendientes` · (menor) y la elección intacta: aviso Información "Antes de confirmar necesitamos {tus datos / que aceptes los términos actualizados}." |
| 04 → 422 `datos_invalidos` (`version_condiciones`) | Como "Textos no cargan" |
| Paso 03: guardar falla | Errores del [perfil](RF-17-perfil.md#estados) bajo cada campo; 401, 503, red y no JSON como el paso 04 de la [reserva](RF-04-reservar.md#estados), con los datos conservados |
| Sin JS | `<noscript>` de cada estructura (existente) |

Claves `aviso` (lista cerrada): en `/app/*`, `textos-aceptados`; en el paso 03, `faltan-datos`, `textos-pendientes`.

## Copy

| Elemento | Texto |
|---|---|
| `/acceso/textos`, primera vez | ANTES DE EMPEZAR · "Lee el resumen y acepta los términos para reservar con nosotros." |
| `/acceso/textos`, actualización | TÉRMINOS ACTUALIZADOS · "Cambiamos los términos de uso. Para hacer reservas nuevas, léelos y acéptalos. Tus reservas actuales siguen con las condiciones que aceptaste." |
| Casillas | Las de los [resúmenes](../../08-legal/resumenes-para-pantallas.md) con la versión real: registro, declaración de agrupación, reserva de sala |
| Paso 03 | Título COMPLETA TUS DATOS · "Antes de tu primera reserva necesitamos saber quién eres. Solo te lo pedimos una vez." · `<title>` "Completa tus datos · Paso 3 de 5 · Reservar sala" |
| Ayuda de la casilla de menor | "Si lo marcas, por ahora no podrás reservar en línea: te ayudaremos por otro canal." |
| Aviso de `LayoutApp` | "Tienes textos por aceptar" · "Mientras tanto no puedes hacer reservas nuevas. Puedes ver, pagar y cancelar las que ya tienes." · "Revisar y aceptar" |
| Botones | Aceptar y continuar · Ahora no · Guardar y continuar · Confirmar reserva (sin cambios) |

En [mis reservas](RF-04-mis-reservas.md#detalle), D1 suma CONDICIONES: "versión 1.0.0", enlazada a esa versión (`Reserva.version_condiciones`).

## Accesibilidad

- Cada resumen es un `<fieldset>` con `<legend>` ([ficha](../componentes/resumen-legal.md#accesibilidad)); el foco al cargar va al `<h1>`.
- Orden de foco en `/acceso/textos`: resumen → enlace(s) → casilla → "Aceptar y continuar" → "Ahora no".
- El aviso de `LayoutApp` va antes del encabezado en el DOM y no lleva rol (no es resultado de una acción); el aviso Crítico del menor, `role="alert"` al aparecer tras guardar.
- Ninguna casilla se marca sola al volver a un paso (las aceptaciones no viajan en la URL).

## Pendientes

- **leader / dev-backend:** los [resúmenes](../../08-legal/resumenes-para-pantallas.md) son **por paso** (registro, reserva, pago, promociones) y el contrato guarda **un** `resumen` por versión de texto. Proponemos `resumenes: {contexto: texto}` en cada versión. El de la reserva lleva `[fecha y hora límite]`: proponemos guardarlo sin datos de la reserva (R1 y Listo ya los muestran).
- **leader / dev-backend:** decisión 8 registra la versión de las condiciones en el pago, pero `POST /pagos` no la recibe y el resumen enlaza la política: falta el campo y aclarar qué texto se enlaza.
- **leader / dev-backend:** sin `pendientes[].motivo` (`nuevo` / `actualizado`) la isla necesita `GET /aceptaciones/mias` para el título; y no hay "qué cambia" de una versión mayor: proponemos `resumen_cambios` opcional.
- **leader:** ¿pendientes de `registro` bloquean `POST /reservas` (como `reaceptacion_requerida`)? La pantalla lo asume.
