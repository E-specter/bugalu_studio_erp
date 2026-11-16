---
id: pantalla-rf-04-reservar
titulo: Pantalla — Reservar sala (flujo por pasos)
estado: borrador
depende_de: [RF-04, RF-02, RF-03, RF-01, ADR-009, flujo-registrar-reserva, diseno-brief, patron-flujo-por-pasos, patron-formularios, patron-estados-sistema, comp-calendario, comp-pasos, comp-resumen-persistente, comp-tarjeta-opcion, comp-casilla, comp-tabla, comp-campo, comp-aviso, comp-barra-acciones, comp-indicador-estado]
---

# Reservar sala

| Campo | Valor |
|---|---|
| Requerimiento | [RF-04](../../03-requerimientos/RF-04.md): CA-01 a CA-04, CA-09, CA-10; simulación de [RF-02](../../03-requerimientos/RF-02.md): CA-05 |
| Actores | Visitante (crea su cuenta en el paso 03) y Artista/Cliente |
| Estructura | Flujo ([flujo por pasos](../patrones/flujo-por-pasos.md)), [flujo de dominio](../../02-dominio/flujos/registrar-reserva.md) |
| Ruta | `/reservar` → `/reservar/servicio` → `/reservar/cuenta` → `/reservar/confirmar` → `/reservar/listo?id=` |
| URL | `fecha`, `vista`, `sala`, `inicio` (ISO con zona), `duracion` (minutos), `servicio` (id), `esp` (ids separados por comas), `cuenta` (`registrar\|iniciar`), `id` |
| Isla | [`<bugalu-calendario modo="reserva">`](../componentes/calendario.md), `<bugalu-reserva paso="horario\|servicio\|confirmar\|listo">` (nueva), `<bugalu-acceso>` del [acceso](RF-01-acceso.md) |

**Decisión del brief:** no hay borrador en el servidor. Lo elegido viaja en la consulta de la URL de cada paso ([flujo por pasos](../patrones/flujo-por-pasos.md#reglas), regla 1) y se guarda solo al confirmar: recargar, volver o compartir el enlace conserva la elección. Si a un paso le falta un dato de uno anterior, la isla va (`location.replace`) al primer paso incompleto.

## Recorrido

1. **01 Horario** (`/reservar`): el bloque del [calendario](RF-03-calendario.md). Elige una media hora libre (inicio) y la duración; "Continuar".
2. **02 Servicio** (`/reservar/servicio`): elige el servicio y los especialistas; ve el precio simulado con su desglose y el anticipo; "Continuar".
3. **03 Cuenta** (`/reservar/cuenta`): sin sesión, crea su cuenta o inicia sesión aquí ([acceso, desde un flujo](RF-01-acceso.md#desde-un-flujo-reservar-o-agendar)); con sesión, este paso se salta y queda HECHO.
4. **04 Confirmar** (`/reservar/confirmar`): revisa todo, ve de nuevo el precio, deja el detalle opcional y pulsa "Confirmar reserva" (`POST /reservas`).
5. **05 Listo** (`/reservar/listo?id=`): folio, fecha límite de pago y siguientes pasos; va a su reserva en [mis reservas](RF-04-mis-reservas.md).

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Inicio | Evento `calendario-inicio` → `inicio` | `D MMM, HH:mm` ([formato](../patrones/estructura-app.md#formato-de-datos)) |
| Duración | `duracion`; opciones de 30 en 30 min hasta `minutosMaximos` (tope 480) | [Duración de reserva](../patrones/estructura-app.md#formato-de-datos): "30 min" … "8 h". Por defecto, la de la URL o 1 h (30 min si solo cabe eso) |
| Fin | `inicio` + `duracion`, enviado como `fin` | `HH:mm` |
| Servicios | `GET /servicios`, solo `ocupa_sala` y `activo` | [Tarjeta de opción](../componentes/tarjeta-opcion.md) Servicio: `nombre`; descripción según `categoria` (Copy); metadato `tarifa_hora` "S/ 120,00 por hora" |
| Especialistas | `GET /especialistas`, solo `activo` | [Casilla](../componentes/casilla.md): `nombre`; detalle "S/ 30,00 + S/ 25,00 por hora" (`monto_fijo`, `monto_variable`, `unidad`: "por hora" / "por media hora") |
| Por defecto | `Servicio.especialistas_por_defecto` | Marcados y deshabilitados (`aria-disabled` + detalle "Incluido con este servicio"): solo el Administrador los quita ([RF-02](../../03-requerimientos/RF-02.md) CA-02). Al cambiar de servicio se marcan los suyos; los elegidos a mano se conservan |
| Precio simulado | `POST /simulaciones {id_sala, id_servicio, inicio, fin, especialistas}` → `Simulacion` | [Tabla](../componentes/tabla.md) Partidas: CONCEPTO · CANTIDAD · IMPORTE; filas de `lineas`, después `recargos` ("Recargo de noche · 2 bloques de 30 min"); pie TOTAL (`total`) y ANTICIPO 50 % (`anticipo`). Importes `S/ 1 250,00` |
| Detalle | Campo Área → `detalle?` | Opcional; `maxlength` según el contrato (ver Pendientes) |
| Reserva creada | `POST /reservas` → 201 `Reserva`; en Listo, `GET /reservas/{id}` | `folio` (Invertida), `vence_pago` como [plazo restante](../patrones/estructura-app.md#formato-de-datos), `precio.total`, `precio.anticipo` |
| Correo del aviso | Sesión de Supabase Auth (`email`) | Tal cual |

La simulación se repite (con 400 ms de espera tras el último cambio) al elegir servicio o especialistas; el navegador nunca suma importes ni envía precios.

## Composición

Todas: [cabecera-app](../componentes/cabecera-app.md) Flujo (contexto: etiqueta Neutra "SALA · LA MOLINA"; en Listo, el folio en etiqueta Invertida) → [pasos](../componentes/pasos.md) (HORARIO · SERVICIO · CUENTA · CONFIRMAR · LISTO) → [encabezado](../componentes/encabezado-pantalla.md) Flujo ("PASO 02 / 05") → principal + [resumen persistente](../componentes/resumen-persistente.md) Solicitud "TU RESERVA", etiqueta "SIN CONFIRMAR": SALA, FECHA, HORARIO, DURACIÓN, SERVICIO, ESPECIALISTAS; total y "Anticipo 50 %" cuando hay simulación.

| Paso | Principal | Cierre |
|---|---|---|
| 01 | [Panel](../componentes/panel.md) `01 ELIGE TU HORARIO` con el [calendario](../componentes/calendario.md); panel `02 DURACIÓN` con [campo](../componentes/campo.md) Selector DURACIÓN | [Botón](../componentes/boton.md) Primario grande "Continuar" (`arrow-right`) |
| 02 | `<fieldset>` SERVICIO (tarjetas Servicio); `<fieldset>` ESPECIALISTAS (casillas); panel `PRECIO SIMULADO`: tabla Partidas + [aviso](../componentes/aviso.md) Información de simulación | [Barra de acciones](../componentes/barra-acciones.md) Flujo: "Anterior" + "Continuar" |
| 03 | Panel `C1 CREA TU CUENTA` o `C1 INICIA SESIÓN` (formulario del [acceso](RF-01-acceso.md)) | El del formulario; "Anterior" como enlace bajo el panel |
| 04 | Panel `R1 TU RESERVA` (`<dl>` con enlace "Cambiar" por dato); `R2 PRECIO` (tabla Partidas + aviso); `R3 DETALLE` (campo Área); `R4 PAGO Y CANCELACIÓN` (texto) | Barra Flujo: "Anterior" + "Confirmar reserva" |
| 05 | [Aviso](../componentes/aviso.md) Éxito; panel Destacado `L1 RESERVA {folio}` (`<dl>` + [indicador](../componentes/indicador-estado.md) Barra Pendiente "PRE-RESERVADA" con el plazo); panel `SIGUIENTES PASOS` (`<ol>`) | Botón Primario "Ver mi reserva"; enlace "Reservar otro horario". Sin barra de flujo |

Adaptabilidad: la del [flujo por pasos](../patrones/flujo-por-pasos.md#móvil): pasos Compacta, resumen en `<details>` "Ver resumen · S/ 450,00" sobre la barra, botones apilados; el calendario pasa a lista de días ([ficha](../componentes/calendario.md#adaptabilidad)).

## Estados

| Situación | Forma y texto |
|---|---|
| 01 sin inicio al continuar | Error del paso: "Elige una hora de inicio en el calendario." (foco a la cuadrícula); DURACIÓN deshabilitada con ayuda "Elige primero la hora de inicio." |
| Calculando precio | Panel PRECIO con `aria-busy`, "Calculando precio…"; resumen "—" |
| Simulación 422 `tramo_invalido` | Aviso Error "Ese horario ya no es válido. Vuelve a elegirlo." + "Elegir otro horario" (paso 01 con `fecha`) |
| Simulación 422 `servicio_no_reservable` / `datos_invalidos` | Aviso Error "Ese servicio no se reserva en sala. Elige otro." / "No pudimos calcular el precio con estos datos. Revisa tu elección." |
| Simulación 503, red, no JSON | Aviso Error en PRECIO + "Reintentar". En 02 se puede continuar; en 04 "Confirmar reserva" queda deshabilitado con el motivo "Necesitamos mostrarte el precio antes de confirmar." |
| Servicios o especialistas: error / vacío | Aviso Error + "Reintentar" / "Ahora no hay servicios disponibles para reservar. Vuelve pronto." |
| Confirmando | Botón en Carga "Confirmando…", "Anterior" deshabilitado |
| 409 `tramo_no_disponible` | Aviso Error "Alguien reservó ese horario hace un momento. Elige otro; lo demás se conserva." + "Elegir otro horario" |
| 403 `ensayo_no_disponible` | Aviso Error "El ensayo es para quien ya tiene una sesión confirmada con nosotros. Elige grabación o live session." + "Cambiar servicio" |
| 422 `fuera_de_franja` / `anticipacion_insuficiente` / `anticipacion_excesiva` | "Ese horario ya no está publicado." / "Ese horario empieza demasiado pronto para reservarlo." / "Ese horario aún no se puede reservar: está demasiado lejos." + "Elegir otro horario" |
| 422 `duracion_invalida` / `servicio_no_reservable` / `datos_invalidos` | "La duración va de 30 min a 8 h, en bloques de 30 min." + paso 01 / texto de la simulación + paso 02 / "Algo en tu reserva no es válido. Revisa los pasos." |
| 401 al confirmar | Aviso "Tu sesión caducó. Inicia sesión para confirmar; tu elección se conserva." + "Iniciar sesión" (paso 03 `?cuenta=iniciar`) |
| 503 / red / no JSON al confirmar | "El servicio no responde. Tu reserva no se guardó; inténtalo en unos minutos." / "Sin conexión. Tu reserva no se guardó; revisa tu red." / "Algo salió mal. Revisa en Mis reservas si se guardó antes de repetir." Sin "Reintentar": el botón sigue disponible |
| Listo sin datos (`GET` falla) | Aviso Éxito "Reserva registrada." + "Ver mis reservas"; el resto no se pinta |
| Sin JS | `<noscript>`: aviso Información "Para reservar necesitas JavaScript. Actívalo en tu navegador y recarga la página." |

Los errores al confirmar van en un aviso arriba del paso, con el foco en él ([formularios](../patrones/formularios.md#validación)); el paso afectado de [pasos](../componentes/pasos.md) pasa a REVISAR. Permisos: pantalla pública; reservar exige sesión de cliente (paso 03).

## Copy

| Paso | Título (`<h1>`) | Descripción |
|---|---|---|
| 01 | ELIGE TU HORARIO | Elige el día, la hora de inicio y cuánto tiempo necesitas la sala. |
| 02 | SERVICIO Y PRECIO | Elige qué vas a hacer y quién te acompaña. El precio se calcula al momento. |
| 03 | TU CUENTA | Crea tu cuenta o inicia sesión para guardar la reserva. Lo que elegiste se conserva. |
| 04 | CONFIRMA TU RESERVA | Revisa todo antes de confirmar. |
| 05 | RESERVA REGISTRADA | Tu horario queda apartado mientras pagas el anticipo. |

- Descripción por categoría: grabación "Graba voces, instrumentos o tu banda en vivo."; ensayo "Ensaya en sala. Disponible si ya tienes una sesión confirmada con nosotros."; live "Sesión en vivo grabada en sala."
- DURACIÓN, ayuda: "Desde las {HH:mm} caben hasta {N h}. Tras cada sesión la sala necesita 30 min de preparación." ESPECIALISTAS, ayuda: "El ingeniero de sonido viene incluido."
- Aviso de simulación ([RN-15](../../02-dominio/reglas-negocio.md)): "Esta simulación no tiene valor de cotización. El precio de tu reserva se calcula al confirmarla, con las mismas tarifas."
- R3: QUÉ NECESITAS (opcional), ayuda "Cuéntanos qué vas a grabar o qué equipo necesitas." R4 ([RN-18](../../02-dominio/reglas-negocio.md), [RN-20](../../02-dominio/reglas-negocio.md)): "Pagas el 50 % para confirmar y el resto al terminar la sesión. Tienes un plazo para pagar el anticipo; te lo decimos al confirmar y por correo. Si vence sin pago, la reserva se cancela y el horario se libera. Puedes cancelarla sin costo mientras no hayas registrado ningún pago."
- Listo, siguientes pasos: "1. Paga el anticipo de {anticipo} antes del {vence_pago}. 2. Registra tu comprobante desde tu reserva. 3. Cuando lo validemos, tu reserva pasará a Confirmada." Debajo: "Te enviamos estos datos a {correo}."

## Accesibilidad

- `<title>` "Elige tu horario · Paso 1 de 5 · Reservar sala"; al cargar cada paso, el foco va al `<h1>` ([flujo por pasos](../patrones/flujo-por-pasos.md#accesibilidad)).
- Orden de foco: pasos → contenido del paso → cierre → resumen (en móvil, `<details>` antes de la barra).
- Una región `role="status"` estable de `<bugalu-reserva>` anuncia el total al terminar cada simulación ("Total S/ 450,00, anticipo S/ 225,00"), nunca en cada cambio; el calendario anuncia lo suyo.
- SERVICIO y ESPECIALISTAS son `<fieldset>` con `<legend>`; el especialista incluido sigue enfocable para leer por qué no se quita.
- El plazo restante no tiene límite que expire en la página (WCAG 2.2.1): se informa; no se retiene ni se cuenta nada en el flujo.

## Pendientes

- **dev-backend:** ¿`especialistas` debe incluir los por defecto o el backend los añade? La isla los envía marcados. ¿Longitud máxima de `detalle`?
- **leader:** el paso 2 de Listo ("registra tu comprobante") llega con [RF-05](../../03-requerimientos/RF-05.md); hasta entonces ninguna reserva puede detener su caducidad. Registrar `<bugalu-reserva>` en [frontend-islas](../../01-arquitectura/frontend-islas.md).
- **Usuario:** ¿la reserva pide aceptar condiciones con una casilla? Hoy R4 solo informa.
