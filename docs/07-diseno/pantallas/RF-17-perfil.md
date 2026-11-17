---
id: pantalla-rf-17-perfil
titulo: Pantalla — Perfil reforzado, consentimientos y textos aceptados (etapa A)
estado: borrador
depende_de: [RF-17, RF-01, ADR-012, RN-25, pantalla-rf-01-perfil, diseno-brief, patron-formularios, patron-estados-sistema, comp-resumen-legal, comp-campo, comp-casilla, comp-panel, comp-tabla, comp-aviso, comp-boton, comp-etiqueta-tecnica]
---

# Perfil reforzado y privacidad

| Campo | Valor |
|---|---|
| Requerimiento | [RF-17](../../03-requerimientos/RF-17.md): CA-06, CA-07 (en el perfil), CA-12, CA-13 (historial), CA-14 |
| Actores | Artista/Cliente. Personal y Administrador conservan el [perfil de RF-01](RF-01-perfil.md) sin cambios |
| Estructura | App, portal ([estructura de app](../patrones/estructura-app.md#app)) |
| Ruta | `/app/perfil` (amplía la [spec de RF-01](RF-01-perfil.md)) y `/app/perfil/privacidad` (nueva). URL: `aviso` |
| Isla | `<bugalu-perfil>` (existente; suma los campos de A3 a A5) en `/app/perfil` y `<bugalu-privacidad>` (nueva, isla propia) en `/app/perfil/privacidad`. **Decisión del brief** (TAREA-RF17-8): la privacidad no comparte isla con los datos porque no comparte formulario, estados ni guardado |

## Recorrido

1. Llega desde "Mi perfil", desde el aviso "Para reservar te falta…" o desde el paso 03 de la [reserva](RF-17-registro-y-aceptaciones.md#recorrido) (que usa los mismos campos).
2. **Datos:** además de lo de RF-01, elige modalidad, escribe su documento y, si quiere, domicilio y redes. Si es una agrupación, registra integrantes y acepta la declaración. "Guardar cambios".
3. **Privacidad** ("Privacidad y textos aceptados" en A2): da o retira cada consentimiento en un paso con "Guardar preferencias" y ve el historial de lo que aceptó.

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Modalidad | `Perfil.modalidad` | [Casilla](../componentes/casilla.md) Radio: Individual (detalle "Reservas a tu nombre.") · Agrupación (detalle "Banda, dúo o colectivo. Tú eres el responsable de la cuenta.") |
| Nombre artístico | `nombre_artistico` | Etiqueta según modalidad: NOMBRE ARTÍSTICO O PROYECTO · NOMBRE DE LA AGRUPACIÓN |
| Documento | `documento.{tipo, numero}` | TIPO DE DOCUMENTO ([campo](../componentes/campo.md) Selector: DNI · Carné de extranjería · Pasaporte) + NÚMERO, en fila. DNI: `inputmode="numeric"`, 8 dígitos; CE y pasaporte: 6 a 12 letras o cifras, la isla los pasa a mayúsculas |
| Teléfono | `telefono` | Como en RF-01; la ayuda suma "Lo necesitas para reservar." |
| Menor | `es_menor` | Casilla "Soy menor de 18 años", sin marcar, con la ayuda del [paso 03](RF-17-registro-y-aceptaciones.md#copy) |
| Domicilio | `domicilio` | Texto, opcional, `maxlength="200"`, `autocomplete="street-address"` |
| Redes | `redes[].{red, valor}`, hasta 5 | [Filas repetibles](../patrones/formularios.md#composición): RED (Selector: Instagram · TikTok · Facebook · YouTube · Spotify · Otra) + USUARIO O ENLACE |
| Integrantes | `integrantes[].{nombre, rol}`, 1 a 20, solo agrupación | Filas repetibles: NOMBRE + ROL ("Voz", "Batería") |
| Declaración | `declaracion_agrupacion` vigente, sin aceptación en `GET /aceptaciones/mias` | [Resumen legal](../componentes/resumen-legal.md) Obligatoria; se envía `POST /aceptaciones {contexto: "registro"}` **antes** del `PATCH /perfil` |
| Le falta para reservar | `datos_para_reservar` y campos vacíos | Lista en el aviso: "documento de identidad", "teléfono" |
| Consentimientos | `Perfil.consentimientos` → `PUT /perfil/consentimientos` | Cuatro casillas, sin marcar mientras no se hayan dado |
| Textos aceptados | `GET /aceptaciones/mias` → `[Aceptacion]` | Más reciente primero; fecha `D MMM AAAA, HH:mm`; versión enlazada a su [página pública](RF-17-textos-legales.md#páginas-públicas) |

## Composición

| Vista | Región | Componente (variante) | Contenido |
|---|---|---|---|
| Datos | Avisos | [aviso](../componentes/aviso.md) | Existentes + Información "Para reservar te falta: {lista}." si `datos_para_reservar` es `false` + Aviso de menor (Estados) |
| Datos | Principal (un `<form>`) | [paneles](../componentes/panel.md) `A1 TUS DATOS` (existente) → `A3 IDENTIDAD` (modalidad, documento, menor) → `A4 INTEGRANTES` (solo agrupación: filas + declaración) → `A5 DOMICILIO Y REDES` | Primario "Guardar cambios" al final, como hoy |
| Datos | Lateral | panel Lateral `A2 CUENTA` (existente) | Suma el enlace "Privacidad y textos aceptados" |
| Privacidad | Principal (un `<form>`) | panel `P1 PROMOCIONES` (resumen legal Opcional con título POLÍTICA DE PRIVACIDAD, enlace a la política, casillas correo y WhatsApp) → panel `P2 USOS PROMOCIONALES` (resumen legal Opcional con título CONDICIONES DE CONTRATACIÓN, enlace a las condiciones, casillas fotos y videos, excluir mi material) | Primario "Guardar preferencias". El título del resumen es el **nombre del texto** ([ficha](../componentes/resumen-legal.md#anatomía)), no repite el del panel |
| Privacidad | Principal | panel `P3 TEXTOS ACEPTADOS` + [tabla](../componentes/tabla.md) Compacta | TEXTO (nombre + versión enlazada) · DÓNDE (Registro · Reserva, enlazada a su detalle por `Aceptacion.id_operacion`: `/app/reservas/detalle?id={id_operacion}`; sin `id_operacion`, texto sin enlace · Pago · Promociones · Usos promocionales) · FECHA · ESTADO ("Retirado el 3 dic 2026" o "—") |

Marcar y desmarcar cuestan lo mismo y se guardan con el mismo botón: retirar un consentimiento es desmarcar y guardar (CA-12, CA-13). Las casillas de modalidad no cambian lo ya escrito: al pasar a Individual, A4 se oculta pero sus filas se conservan hasta guardar. Adaptabilidad: como RF-01; filas repetibles en una columna < `punto-quiebre-tableta`.

## Estados

Los de [RF-01](RF-01-perfil.md#estados) siguen igual. Nuevos:

| Bloque | Situación | Forma y texto |
|---|---|---|
| Datos | Errores de campo | "Elige el tipo de documento." · "Escribe los 8 dígitos de tu DNI." · "Escribe de 6 a 12 letras o cifras, sin espacios ni guiones." · "El domicilio admite hasta 200 caracteres." · "Escribe tu usuario o el enlace." · "Añade al menos un integrante." · "Escribe el nombre del integrante." · "Escribe qué hace en la agrupación, por ejemplo, voz." · declaración sin marcar: "Marca la casilla para registrar la agrupación." |
| Datos | 409 `documento_en_uso` (mientras el contrato lo tenga) | Error bajo NÚMERO: "Ese documento ya está en otra cuenta. Si es tuyo, escríbenos y lo revisamos." |
| Datos | Menor guardado | Aviso Aviso "Aún no puedes reservar en línea" + texto del [paso 03](RF-17-registro-y-aceptaciones.md#estados) y el contacto |
| Datos | 5 redes / 20 integrantes | "Añadir…" se oculta; ayuda "Máximo 5 redes." / "Máximo 20 integrantes." |
| Privacidad | Carga | Paneles con "Cargando…", `aria-busy` |
| Privacidad | Sin teléfono | Casilla de WhatsApp deshabilitada (`aria-disabled`, sigue enfocable) con el detalle "Añade tu teléfono en Tus datos para elegir WhatsApp." y el enlace |
| Privacidad | 422 `telefono_requerido` | El mismo texto como error de la casilla |
| Privacidad | 409 `texto_desactualizado` | Los resúmenes se repintan con la versión nueva; las casillas **conservan** la elección; aviso Información "Actualizamos el texto a la versión {v}. Revísalo y vuelve a guardar." |
| Privacidad | Éxito | Aviso Éxito "Preferencias guardadas." y P3 recargado |
| P3 | Vacío | "Aún no has aceptado ningún texto." |
| P3 | Error | Aviso Error del bloque + "Reintentar"; el formulario sigue usable |
| Ambas | 401, 503, red, no JSON | Textos de RF-01 (carga y guardado) |

Permisos: las vistas nuevas y los paneles A3 a A5 solo para `rol = cliente`; a otros roles `/app/perfil/privacidad` responde con el 403 de la vista ("Esta sección es para artistas.") + "Volver a mi perfil".

## Copy

| Elemento | Texto |
|---|---|
| Privacidad: ruta, título, descripción | Inicio / Perfil / Privacidad · PRIVACIDAD · "Tú decides si recibes promociones y si usamos tu imagen. Nada de esto cambia tu servicio." |
| Ayudas | A3: "Lo pedimos una vez para que tus reservas sean seguras." · A4: "Tú eres el responsable de la agrupación ante el estudio." · Redes: "Opcional. Nos ayuda a conocer tu trabajo." |
| Casillas de P1 y P2 | Las de los [resúmenes](../../08-legal/resumenes-para-pantallas.md#promociones) |
| Acciones | Guardar cambios · Guardar preferencias · Añadir red · Añadir integrante · "Quitar {red / integrante}" |

## Accesibilidad

- A3, A4 y A5 son `<section>` con `<h2>`; MODALIDAD, cada fila repetible y cada resumen con casillas, `<fieldset>` + `<legend>`.
- Al elegir Agrupación, A4 aparece después de A3 en el DOM; no se mueve el foco y la región `role="status"` anuncia "Añade a los integrantes de la agrupación".
- P3 es `<table>` con `<caption>` "Textos que aceptaste".

## Pendientes

- **leader / dev-backend:** decisión 4 (documento repetido se marca, no se bloquea) contradice el 409 `documento_en_uso` del contrato; proponemos quitarlo de `PATCH /perfil`.
- **leader / dev-backend:** `PATCH /perfil {modalidad: "agrupacion"}` sin la declaración aceptada: proponemos 409 `declaracion_requerida`, para que no dependa del orden de dos llamadas.
