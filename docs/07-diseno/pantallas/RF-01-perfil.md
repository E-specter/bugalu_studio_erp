---
id: pantalla-rf-01-perfil
titulo: Pantalla — Perfil
estado: borrador
depende_de: [RF-01, ADR-008, diseno-brief, patron-estructura-app, patron-formularios, patron-estados-sistema, comp-encabezado-pantalla, comp-panel, comp-campo, comp-aviso, comp-boton, comp-etiqueta-tecnica]
---

# Perfil

| Campo | Valor |
|---|---|
| Requerimiento | [RF-01](../../03-requerimientos/RF-01.md): CA-06, CA-09, CA-12, CA-13 |
| Actores | Artista/Cliente, Personal interno, Administrador (cada uno el suyo) |
| Estructura | App ([estructura de app](../patrones/estructura-app.md#app)), portal o panel interno según el rol |
| Ruta | `/app/perfil` (URL: `aviso`; `verificar=1` al volver del enlace de verificación). Se llega desde el menú de la [cabecera](../componentes/cabecera-app.md) ("Mi perfil") |
| Isla | `<bugalu-perfil>` (existente: pasa de lectura a edición y suma la verificación del correo) |
| Origen Figma | Ninguno ([brecha](../figma.md#brecha-detectada)); vista del brief |

## Recorrido

1. Llega desde "Mi perfil" del menú, o redirigido tras crear la cuenta (`?aviso=cuenta-creada`) o cambiar la contraseña (`?aviso=contrasena-cambiada`).
2. Si su correo no está verificado, ve el aviso y pide un enlace con "Verificar mi correo" (CA-06). El enlace vuelve a `/app/perfil?verificar=1`; la isla llama a `POST /perfil/verificar-correo` y quita `verificar` de la URL.
3. Edita nombre y teléfono; el cliente, también su nombre artístico (CA-09) → "Guardar cambios" (`PATCH /perfil`).
4. Ve, sin poder cambiarlos, su correo, rol y especialidad.
5. Cierra sesión desde el menú de la cabecera ([acceso](RF-01-acceso.md#recorrido), paso 6).

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Nombre | `GET /perfil` → `Perfil.nombre`; `PATCH {nombre}` | [Campo](../componentes/campo.md) Texto, obligatorio, `autocomplete="name"` |
| Teléfono | `Perfil.telefono`; `PATCH {telefono}` | Campo Texto `tel`, opcional; la isla quita espacios; 9 a 15 dígitos, `+` inicial opcional |
| Nombre artístico | `Perfil.nombre_artistico`; `PATCH {nombre_artistico}` | Campo Texto, solo si `rol = cliente` (si no, 422 `campo_no_permitido`) |
| Correo | `Perfil.correo` | Solo lectura, tal cual |
| Correo verificado | `Perfil.correo_confirmado` | [Etiqueta](../componentes/etiqueta-tecnica.md) Éxito "VERIFICADO" o Aviso "SIN VERIFICAR" tras el correo, separada `espacio-2`; si no cabe, pasa a la línea siguiente |
| Rol | `Perfil.rol` | Solo lectura: Cliente · Personal del estudio · Administrador |
| Especialidad | `Perfil.especialidad` | Solo lectura; no se muestra si es `null` y el rol es cliente; "Sin especialidad" en personal |

## Composición

| Región | Componente (variante) | Contenido |
|---|---|---|
| Encabezado | [encabezado-pantalla](../componentes/encabezado-pantalla.md) (App) | Ruta Inicio / Perfil, índice `[00] CUENTA`, título PERFIL, descripción. Sin acción en el encabezado: la principal cierra el formulario |
| Avisos | [aviso](../componentes/aviso.md) | Resultado (`aviso` de la URL o del guardado) y, si falta, "Verifica tu correo" (variante Aviso) con [botón](../componentes/boton.md) Secundario "Verificar mi correo" |
| Principal | [panel](../componentes/panel.md) Base `A1 TUS DATOS` | Nombre → teléfono → nombre artístico (cliente) → [botón](../componentes/boton.md) Primario "Guardar cambios" al final, a su ancho natural. Una sola acción: sin [barra de acciones](../componentes/barra-acciones.md#cuándo-se-usa) |
| Lateral | panel Lateral `A2 CUENTA` | `<dl>`: correo + etiqueta, rol, especialidad; ayuda "El rol y la especialidad los asigna el Administrador." |

Patrones: [formularios](../patrones/formularios.md), [estados del sistema](../patrones/estados-sistema.md). Adaptabilidad: < `punto-quiebre-escritorio`, una columna (A1 y después A2).

**Decisión del brief:** lo no editable va en una `<dl>`, no en campos de solo lectura: un campo enfocable que no se puede cambiar confunde con lector de pantalla y teclado.

## Estados

La isla conserva sus estados y textos actuales y suma los de edición.

| Bloque | Situación | Forma y texto |
|---|---|---|
| Perfil | Carga | Panel con "Cargando…" y `aria-busy="true"` (existente) |
| Perfil | Datos | Formulario A1 + lista A2 |
| Perfil | 401 | Aviso "Tu sesión no es válida. Inicia sesión para ver tu perfil." + "Ir al acceso" (existente; enlace con `?volver=/app/perfil`) |
| Perfil | 404 `perfil_no_encontrado` | Aviso Error "No encontramos tu perfil. Tu cuenta existe, pero aún no tiene perfil. Pide al estudio que lo cree." (existente) |
| Perfil | Red caída | Aviso Error "Sin conexión. No hay conexión con el servidor. Revisa tu red e inténtalo de nuevo." + "Reintentar" (existente) |
| Perfil | 503 | Aviso Error "Servicio no disponible. El servicio de acceso no responde. Inténtalo de nuevo en unos minutos." + "Reintentar" (existente) |
| Perfil | 403, no JSON u otro | Aviso Error "No pudimos cargar tu perfil. Algo salió mal. Inténtalo de nuevo." + "Reintentar" (existente) |
| Perfil | Sin JS | Aviso Error "Esta página necesita JavaScript. Actívalo en tu navegador y recarga la página." (existente) |
| Guardar | Error de campo (en el navegador) | Error bajo el campo; al enviar, aviso Error resumen "Revisa 1 campo" con enlace. Textos: "Escribe tu nombre." · "Escribe entre 9 y 15 dígitos; puedes empezar con +." |
| Guardar | Enviando | "Guardando…" en el botón; campos sin cambios |
| Guardar | Éxito | Aviso Éxito "Cambios guardados." sobre A1; A1 y A2 muestran los datos devueltos |
| Guardar | 422 `datos_invalidos` / `campo_no_permitido` | Aviso Error con el `mensaje` del servidor (es texto para la persona); datos conservados |
| Guardar | 401 | Aviso "Tu sesión caducó. Inicia sesión y vuelve a guardar." + "Ir al acceso" (`?volver=/app/perfil`) |
| Guardar | 503, red caída, no JSON | Aviso Error con el texto del caso de carga, sin "Reintentar": el botón "Guardar cambios" sigue disponible y los datos se conservan |
| Pedir enlace | Enviando | "Enviando…" en el botón secundario |
| Pedir enlace | Éxito | El aviso cambia su texto: "Te enviamos un enlace a {correo}. Ábrelo para verificar tu correo." |
| Pedir enlace | 429 | "Ya te enviamos uno hace poco. Espera unos minutos antes de pedir otro." |
| Pedir enlace | 5xx o red caída | "No pudimos enviar el correo. Inténtalo de nuevo en unos minutos." |
| Verificar (`?verificar=1`) | Éxito | Aviso Éxito "Correo verificado."; desaparece el aviso de verificación y la etiqueta pasa a VERIFICADO |
| Verificar | 409 `verificacion_no_valida` | Aviso Error "No pudimos verificar tu correo. Abre el enlace del último correo en este navegador, o pide otro con \"Verificar mi correo\"." |
| Verificar | 401 | Aviso Error "Tu sesión caducó. Inicia sesión y vuelve a abrir el enlace." |
| Verificar | 503, red caída, no JSON | Aviso Error con el texto del caso de carga |
| URL | `?aviso=cuenta-creada` | Aviso Éxito "Cuenta creada. Ya puedes reservar." |
| URL | `?aviso=contrasena-cambiada` | Aviso Éxito "Contraseña actualizada. Usa la nueva la próxima vez que inicies sesión." |

Permisos: cada uno ve y edita solo su perfil (CA-09); nadie ve aquí un control de rol o especialidad. El nombre artístico no se muestra a personal ni Administrador.

## Copy

| Elemento | Texto |
|---|---|
| `<title>` y título | Perfil · PERFIL |
| Descripción | Los datos de tu cuenta en el estudio. |
| Paneles | `A1 TUS DATOS` (ayuda: "Así te verá el estudio.") · `A2 CUENTA` |
| Etiquetas | NOMBRE · TELÉFONO (opcional) · NOMBRE ARTÍSTICO O PROYECTO · CORREO · ROL · ESPECIALIDAD |
| Ayudas | Teléfono: "Solo números; con + y código de país si no es de Perú." |
| Acción principal | Guardar cambios |
| Aviso de verificación | Título "Verifica tu correo"; texto "Lo necesitarás antes de registrar tu primer pago. Te enviaremos un enlace de un solo uso." |
| Acción del aviso | Verificar mi correo (texto de [RF-01](../../03-requerimientos/RF-01.md) CA-06) |

**Decisión de la revisión visual (RF-01):** un solo verbo, *verificar*, en botón, título, etiqueta y resultados. Nada de "reenviar" ni "otro correo": al registrarse no se envía ningún correo (la verificación es propia, [ADR-008](../../00-proyecto/decisiones/ADR-008-acceso-y-roles-v1.md)), así que el primer enlace es el que pide la persona.

## Accesibilidad

- `<main>` empieza con el encabezado (`<h1>` PERFIL); A1 y A2 son `<section>` con `<h2>`.
- Orden de foco: aviso de verificación (su botón) → campos de A1 → "Guardar cambios" → A2 no tiene controles.
- Anuncios: la región `role="status"` estable de la isla anuncia una vez cada resultado (carga, guardado, error, enlace pedido, verificación); los avisos clonados no llevan rol ([aviso](../componentes/aviso.md#accesibilidad)). Al fallar el envío, el foco va al aviso de errores; tras guardar, se queda en el botón. Tras "Reintentar", al título del panel (existente).
- El estado del correo va en texto en la etiqueta, no solo en color.

## Pendientes

Ninguno. El de `enable_confirmations` quedó resuelto con la verificación propia ([RF-01](../../03-requerimientos/RF-01.md), notas de implementación).
- **Ampliada por RF-17** para el cliente: identidad, agrupación, domicilio, redes y privacidad ([perfil reforzado](RF-17-perfil.md)).
