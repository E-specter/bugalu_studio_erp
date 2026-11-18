---
id: pantalla-rf-04-reservar
titulo: Pantalla — Reservar sala (flujo por pasos)
estado: borrador
depende_de: [RF-04, RF-02, RF-03, RF-01, ADR-009, flujo-registrar-reserva, diseno-brief, patron-flujo-por-pasos, patron-formularios, patron-estados-sistema, comp-calendario, comp-pasos, comp-resumen-persistente, comp-casilla, comp-tabla, comp-campo, comp-aviso, comp-barra-acciones, comp-indicador-estado]
---

# Reservar sala

| Campo | Valor |
|---|---|
| Requerimiento | [RF-04](../../03-requerimientos/RF-04.md): CA-01 a CA-04, CA-09, CA-10; simulación de [RF-02](../../03-requerimientos/RF-02.md): CA-05; aforo de [RF-03](../../03-requerimientos/RF-03.md): CA-11 |
| Actores | Visitante (crea su cuenta o inicia sesión en el paso 03) y Artista/Cliente |
| Estructura | Flujo ([flujo por pasos](../patrones/flujo-por-pasos.md)), [flujo de dominio](../../02-dominio/flujos/registrar-reserva.md) |
| Ruta | `/reservar` → `/reservar/servicio` → (sin sesión: `/acceso?volver=`) → `/reservar/confirmar` → `/reservar/listo?id=` |
| URL | `fecha`, `vista`, `sala`, `inicio` (ISO con zona), `duracion` (minutos), `servicio` (id), `esp` (ids separados por comas), `id`, `aviso` (`cuenta-creada`) |
| Isla | [`<bugalu-calendario modo="reserva">`](../componentes/calendario.md), `<bugalu-reserva paso="horario\|servicio\|confirmar\|listo">`; el paso 03 es `<bugalu-acceso>` del [acceso](RF-01-acceso.md) |

**Decisión del brief:** no hay borrador en el servidor. Lo elegido viaja en la consulta de la URL de cada paso ([flujo por pasos](../patrones/flujo-por-pasos.md#reglas), regla 1) y se guarda solo al confirmar: recargar, volver o compartir el enlace conserva la elección. Si a un paso le falta un dato de uno anterior, la isla va (`location.replace`) al primer paso incompleto.

**Decisión del brief (TAREA-RF04-6):** el paso 03 no tiene página propia. Sin sesión, "Continuar" del paso 02 (y la carga directa de `/reservar/confirmar`) lleva al [acceso](RF-01-acceso.md) con `volver` = URL del paso 04 con toda la elección; al registrarse o iniciar sesión vuelve ahí ([flujo por pasos](../patrones/flujo-por-pasos.md#reglas), regla 7).

## Recorrido

1. **01 Horario** (`/reservar`): el bloque del [calendario](RF-03-calendario.md). Elige una media hora libre (inicio) y la duración; "Continuar".
2. **02 Servicio** (`/reservar/servicio`): elige el servicio y los especialistas; ve el precio simulado con su desglose y el anticipo; "Continuar".
3. **03 Cuenta**: con sesión, se salta y queda HECHO. Sin sesión, va al acceso (`?volver=`); "Crear cuenta de artista" conserva `volver`. Vuelve al paso 04 (con `?aviso=cuenta-creada` si se registró).
4. **04 Confirmar** (`/reservar/confirmar`): revisa todo, ve de nuevo el precio, deja el detalle opcional y pulsa "Confirmar reserva" (`POST /reservas`).
5. **05 Listo** (`/reservar/listo?id=`): folio, fecha límite de pago y siguientes pasos; va a su reserva en [mis reservas](RF-04-mis-reservas.md).

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Inicio | Evento `calendario-inicio` → `inicio` | `D MMM, HH:mm` ([formato](../patrones/estructura-app.md#formato-de-datos)) |
| Duración | `duracion`; opciones de 30 en 30 min hasta `minutosMaximos` (tope 480) | [Duración de reserva](../patrones/estructura-app.md#formato-de-datos): "30 min" … "8 h". Por defecto, la de la URL o 1 h (30 min si solo cabe eso) |
| Fin | `inicio` + `duracion`, enviado como `fin` | `HH:mm` |
| Servicios | `GET /servicios`, solo `ocupa_sala` y `activo` | [Casilla](../componentes/casilla.md) Radio con detalle: `nombre`; detalle "{descripción según `categoria`} · S/ 120,00 por hora" |
| Especialistas | `GET /especialistas`, solo `activo` | [Casilla](../componentes/casilla.md): `nombre`; detalle "S/ 30,00 + S/ 25,00 por hora" (`monto_fijo` si > 0, `monto_variable`, `unidad`: "por hora" / "por media hora") |
| Por defecto | `Servicio.especialistas_por_defecto` | Marcados y deshabilitados (`aria-disabled` + detalle "Incluido con este servicio"): solo el Administrador los quita ([RF-02](../../03-requerimientos/RF-02.md) CA-02). Al cambiar de servicio se marcan los suyos; los elegidos a mano se conservan |
| Precio simulado | `POST /simulaciones {id_sala, id_servicio, inicio, fin, especialistas}` → `Simulacion` | [Tabla](../componentes/tabla.md) Partidas: CONCEPTO · CANTIDAD · IMPORTE. Filas de `lineas` y de `recargos` ("Recargo de noche"); pie `<tfoot>` TOTAL y ANTICIPO 50 %. CANTIDAD: unidad `hora` como [duración de reserva](../patrones/estructura-app.md#formato-de-datos) ("2 h 30 min", nunca "2.0 h" ni "2,5 h"); `lapso_30` y recargos "5 × 30 min"; `fijo` "1". Importes `S/ 1 250,00`. El mismo formato en [mis reservas](RF-04-mis-reservas.md) (un solo formateador) |
| Detalle | Campo Área → `detalle?` | Opcional; `maxlength="500"` |
| Reserva creada | `POST /reservas` → 201 `Reserva`; en Listo, `GET /reservas/{id}` | `folio` (Invertida), `vence_pago` como [plazo restante](../patrones/estructura-app.md#formato-de-datos), `precio.total`, `precio.anticipo` |
| Correo del aviso | Sesión de Supabase Auth (`email`) | Tal cual |

La simulación se repite (con 400 ms de espera tras el último cambio) al elegir servicio o especialistas; el navegador nunca suma importes ni envía precios.

## Composición

Todas: [cabecera-app](../componentes/cabecera-app.md) Flujo → [encabezado](../componentes/encabezado-pantalla.md) Flujo ("PASO 02 / 05") → [pasos](../componentes/pasos.md) (HORARIO · SERVICIO · CUENTA · CONFIRMAR · LISTO; los HECHO son enlace al paso, salvo CUENTA, que no tiene página) → principal + [resumen persistente](../componentes/resumen-persistente.md) Solicitud "TU RESERVA", etiqueta "SIN CONFIRMAR": SALA, FECHA, HORARIO, DURACIÓN, SERVICIO, ESPECIALISTAS; al pie, total y "Anticipo 50 %" cuando hay simulación. En 04 no se pinta el resumen: R1 y R2 ya lo muestran entero.

| Paso | Principal | Cierre |
|---|---|---|
| 01 | [Panel](../componentes/panel.md) del [calendario](../componentes/calendario.md) (su `<h2>` es el periodo); panel `TIEMPO DE SALA` con [campo](../componentes/campo.md) Selector DURACIÓN. Sin códigos de panel en 01 y 02 | [Botón](../componentes/boton.md) Primario grande "Continuar" (`arrow-right`) |
| 02 | `<fieldset>` SERVICIO (casillas Radio); `<fieldset>` ESPECIALISTAS (casillas); panel `PRECIO SIMULADO`: tabla Partidas + [aviso](../componentes/aviso.md) Información de simulación | [Barra de acciones](../componentes/barra-acciones.md) Flujo: "Anterior" + "Continuar" |
| 03 | Página del [acceso](RF-01-acceso.md) con `volver` (fuera de esta isla) | El del formulario de acceso |
| 04 | Panel `R1 TU RESERVA` (`<dl>` con enlace "Cambiar" por dato, sin importes); `R2 PRECIO SIMULADO` (tabla Partidas + aviso); `R3 DETALLE` (campo Área); `R4 PAGO Y CANCELACIÓN` (texto) | Barra Flujo: "Anterior" + "Confirmar reserva" |
| 05 | [Aviso](../componentes/aviso.md) Éxito; panel Destacado `L1 RESERVA {folio}` (código como en los demás paneles; `<dl>` sin repetir el folio + [indicador](../componentes/indicador-estado.md) Barra Pendiente "PRE-RESERVADA" con el plazo); panel `SIGUIENTES PASOS` (`<ol>`) | Botón Primario "Ver mi reserva"; enlace "Reservar otro horario". Sin barra de flujo |

Entre avisos, paneles y bloques del principal, hueco `espacio-5` (también en Listo y entre el aviso de error y la rejilla).

Adaptabilidad: < `punto-quiebre-escritorio`, pasos Compacta; el resumen deja de ser lateral y va como `<aside>` tras el cierre del paso ([ficha](../componentes/resumen-persistente.md)); botones apilados; el calendario pasa a lista de días ([ficha](../componentes/calendario.md#adaptabilidad)). La tabla Partidas sigue siendo tabla (no pasa a tarjetas).

## Estados

| Situación | Forma y texto |
|---|---|
| 01 sin inicio al continuar | Aviso Error "Elige una hora de inicio en el calendario." con el foco en el primer inicio **visible** (en móvil, el primer botón de hora de la lista de días o, si no hay ninguno abierto, el primer `<summary>` con horas libres); DURACIÓN deshabilitada con ayuda "Elige primero la hora de inicio." |
| Calculando precio | Panel PRECIO con `aria-busy`, "Calculando precio…"; resumen "—" |
| Simulación 422 `tramo_invalido` | Aviso Error "Ese horario ya no es válido. Vuelve a elegirlo." + "Elegir otro horario" (paso 01 con `fecha`) |
| Simulación 422 `servicio_no_reservable` / `datos_invalidos` | Aviso Error "Ese servicio no se reserva en sala. Elige otro." / "No pudimos calcular el precio con estos datos. Revisa tu elección." |
| Simulación 503, red, no JSON | Aviso Error en PRECIO + "Reintentar". En 02 se puede continuar; en 04 "Confirmar reserva" queda deshabilitado con el motivo "Necesitamos mostrarte el precio antes de confirmar." |
| Servicios o especialistas: error / vacío | Aviso Error + "Reintentar" / "Ahora no hay servicios disponibles para reservar. Vuelve pronto." |
| 04 con `?aviso=cuenta-creada` | Aviso Éxito "Cuenta creada. Revisa tu reserva y confírmala." |
| Confirmando | Botón en Carga "Confirmando…", "Anterior" deshabilitado |
| 409 `tramo_no_disponible` | Aviso Error "Alguien reservó ese horario hace un momento. Elige otro; lo demás se conserva." + "Elegir otro horario" |
| 403 `ensayo_no_disponible` | Aviso Error "El ensayo es para quien ya tiene una sesión confirmada con nosotros. Elige grabación o live session." + "Cambiar servicio" |
| 422 `fuera_de_franja` / `anticipacion_insuficiente` / `anticipacion_excesiva` | "Ese horario ya no está publicado." / "Ese horario empieza demasiado pronto para reservarlo." / "Ese horario aún no se puede reservar: está demasiado lejos." + "Elegir otro horario" |
| 422 `duracion_invalida` / `servicio_no_reservable` / `datos_invalidos` | "La duración va de 30 min a 8 h, en bloques de 30 min." + paso 01 / texto de la simulación + paso 02 / "Algo en tu reserva no es válido. Revisa los pasos." |
| 401 al confirmar | Aviso "Tu sesión caducó. Inicia sesión para confirmar; tu elección se conserva." + "Iniciar sesión" (`/acceso?volver=` con el paso 04) |
| 503 / red / no JSON al confirmar | "El servicio no responde. Tu reserva no se guardó; inténtalo en unos minutos." / "Sin conexión. Tu reserva no se guardó; revisa tu red." / "Algo salió mal. Revisa en Mis reservas si se guardó antes de repetir." Sin "Reintentar": el botón sigue disponible |
| Listo sin datos (`GET` falla) | Aviso Éxito "Reserva registrada." + "Ver mis reservas"; el resto no se pinta |
| Sin JS | `<noscript>`: aviso Información "Para reservar necesitas JavaScript. Actívalo en tu navegador y recarga la página." En 01 basta el del calendario: no se pintan dos |

Los errores al confirmar van en un aviso arriba del paso, con el foco en él ([formularios](../patrones/formularios.md#validación)); el paso afectado de [pasos](../componentes/pasos.md) pasa a REVISAR. Permisos: pantalla pública; reservar exige sesión de cliente (paso 03).

## Copy

| Paso | Título (`<h1>`) | Descripción |
|---|---|---|
| 01 | ELIGE TU HORARIO | Elige el día, la hora de inicio y cuánto tiempo necesitas la sala. |
| 02 | SERVICIO Y PRECIO | Elige qué vas a hacer y quién te acompaña. El precio se calcula al momento. |
| 04 | CONFIRMA TU RESERVA | Revisa todo antes de confirmar. |
| 05 | RESERVA REGISTRADA | Tu horario queda apartado mientras pagas el anticipo. |

- Descripción por categoría: grabación "Graba voces, instrumentos o tu banda en vivo."; ensayo "Ensaya en sala. Disponible si ya tienes una sesión confirmada con nosotros."; live "Sesión en vivo grabada en sala."
- TIEMPO DE SALA (título del panel; el campo se llama DURACIÓN), ayuda: "Desde las {HH:mm} caben hasta {N h}. Tras cada sesión la sala necesita 30 min de preparación." ESPECIALISTAS, ayuda: "El ingeniero de sonido viene incluido."
- Aviso de simulación ([RN-15](../../02-dominio/reglas-negocio.md)): "Esta simulación no tiene valor de cotización. El precio de tu reserva se calcula al confirmarla, con las mismas tarifas."
- R3: QUÉ NECESITAS (opcional), ayuda "Cuéntanos qué vas a grabar o qué equipo necesitas." R4 ([RN-18](../../02-dominio/reglas-negocio.md), [RN-20](../../02-dominio/reglas-negocio.md)): "Pagas el 50 % para confirmar y el resto al terminar la sesión. Tienes un plazo para pagar el anticipo; te lo decimos al confirmar y por correo. Si vence sin pago, la reserva se cancela y el horario se libera. Puedes cancelarla sin costo mientras no hayas registrado ningún pago."
- Listo, siguientes pasos: "1. Paga el anticipo de {anticipo} antes del {vence_pago}. 2. Registra tu comprobante desde tu reserva. 3. Cuando lo validemos, tu reserva pasará a Confirmada." Debajo: "Te enviamos estos datos a {correo}."

## Accesibilidad

- `<title>` "Elige tu horario · Paso 1 de 5 · Reservar sala"; al cargar cada paso, el foco va al `<h1>` ([flujo por pasos](../patrones/flujo-por-pasos.md#accesibilidad)), sin anillo ([estados comunes](../componentes/README.md#estados-comunes)).
- Pasos: `<nav aria-label="Progreso de la reserva">`. Orden de foco: pasos → contenido del paso → cierre → resumen (también en móvil).
- Una región `role="status"` estable de `<bugalu-reserva>` anuncia el total al terminar cada simulación ("Total S/ 450,00, anticipo S/ 225,00"), nunca en cada cambio; el calendario anuncia lo suyo.
- SERVICIO y ESPECIALISTAS son `<fieldset>` con `<legend>`; el especialista incluido sigue enfocable para leer por qué no se quita.
- El plazo restante no tiene límite que expire en la página (WCAG 2.2.1): se informa; no se retiene ni se cuenta nada en el flujo.

## Ampliación aforo (RF-03 CA-10 a CA-13)

Dato: `GET /salas` → la `Sala` de `sala` (o la única): `aforo` e `itse.certificado`. Con `aforo: null` no se pinta nada de esta sección. La decisión de qué ve el público es la del [calendario](RF-03-calendario.md#ampliación-aforo-rf-03-ca-10-a-ca-13): número del certificado, nunca su vencimiento ni "vigente".

| Paso | Dónde | Forma y texto |
|---|---|---|
| 01 | Línea del calendario | La del [calendario](RF-03-calendario.md#ampliación-aforo-rf-03-ca-10-a-ca-13) |
| 04 | Fila AFORO de `R1 TU RESERVA`, tras SALA, sin "Cambiar" | Valor "Máximo 6 personas" (1 → "1 persona"); debajo, en `fuente-tamano-pequeno` y `color-texto-secundario`, el texto de la regla de [aforo](../../08-legal/condiciones-uso-y-danos.md#reglas): "Cuenta a todas las personas dentro de la sala, también al personal del estudio. Al llegar indicas quiénes te acompañan; quien exceda el aforo espera en la recepción." y "Certificado ITSE {certificado}" |
| 04 | Cargando / `GET /salas` falla | "—" / "No pudimos cargar el aforo; lo verás en el cartel de la sala." Confirmar no se bloquea: el aforo informa, no cambia la reserva |

Accesibilidad: es una fila más del `<dl>` (`<dt>` AFORO); ITSE va en `<abbr title="Inspección Técnica de Seguridad en Edificaciones">`. Sin icono ni color como único portador. En 390 la fila se apila como las demás de R1.

## Pendientes

- **leader:** el paso 2 de Listo ("registra tu comprobante") llega con [RF-05](../../03-requerimientos/RF-05.md); hasta entonces ninguna reserva puede detener su caducidad.
- **Decidido (usuario, [ADR-009](../../00-proyecto/decisiones/ADR-009-reservas-tarifas-y-caducidad.md)):** sin casilla de condiciones hasta que el estudio tenga el texto legal; la pantalla solo informa.
- **Ampliada por RF-17 y RF-20:** paso 03 con página cuando faltan datos o textos, `R4 CONDICIONES` con casilla (sustituye la decisión anterior de no tener casilla) ([aceptaciones](RF-17-registro-y-aceptaciones.md)) y desglose de IGV ([cambios sensibles](RF-20-cambios-sensibles.md#desglose-de-igv)).
