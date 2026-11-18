---
id: pantalla-rf-15-ficha
titulo: Pantalla — Ficha pública del profesional ("Mi perfil", etapa A)
estado: borrador
depende_de: [RF-15, RF-01, RF-17, pantalla-rf-01-perfil, pantalla-rf-17-perfil, diseno-brief, patron-estructura-app, patron-formularios, patron-estados-sistema, comp-panel, comp-campo, comp-casilla, comp-carga-archivos, comp-avatar, comp-etiqueta-tecnica, comp-boton, comp-aviso]
---

# Ficha pública del profesional

| Campo | Valor |
|---|---|
| Requerimiento | [RF-15](../../03-requerimientos/RF-15.md): CA-01 (solo lo suyo), CA-03, CA-17 (panel del profesional: Mi perfil) |
| Actores | Profesional artístico (la suya). El Administrador usa la misma vista para cualquier profesional, con lo suyo de más ([administración](RF-15-administracion.md#ficha-de-un-profesional)) |
| Estructura | App, panel interno ([estructura de app](../patrones/estructura-app.md#app)) |
| Ruta | `/app/ficha/`. URL: `aviso` |
| Isla | `<bugalu-profesional vista="ficha">` (nueva; el `id` sale de `GET /perfil`; el Administrador lo pasa con `?id=`) |

**Decisión del brief:** el "Mi perfil" del profesional se llama **FICHA** en la navegación y la ruta. "Mi perfil" ya es la cuenta de [RF-01](RF-01-perfil.md) (nombre, teléfono, contraseña) en el menú de la cabecera, y dos destinos con el mismo nombre confunden. La ficha no comparte isla con la cuenta: otro endpoint, otro formulario y otros estados (como la privacidad de [RF-17](RF-17-perfil.md)).

## Recorrido

1. El profesional entra por FICHA (`id-card`), destino que solo se pinta para el rol `profesional`. Arriba ve si su perfil ya es público y, si no, qué falta.
2. Edita nombre artístico, presentación, especialidades y redes → "Guardar ficha"; se queda en la vista con el aviso.
3. Sube, cambia o quita su foto en el lateral (se guarda sola, aparte).
4. Con el perfil publicado, "Ver mi perfil público" abre el [perfil público](RF-15-perfil-publico.md); "Mis horarios" lleva a [horarios](RF-15-horarios.md).

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Id | `GET /perfil` → `Perfil.id` (ver Pendientes) | — |
| Ficha | `GET /profesionales/{id}` → `Profesional` (con `activo` y `publicado`) | — |
| Nombre | `Profesional.nombre` | `<dl>`, tal cual; no se edita aquí |
| Nombre artístico | `nombre_artistico` | [Campo](../componentes/campo.md) Texto, opcional, `maxlength="80"` |
| Presentación | `presentacion` | Campo Área, opcional, `maxlength="600"` |
| Especialidades | `GET /especialidades-asesoria` (activas) + `Profesional.especialidades[].id` | [Casillas](../componentes/casilla.md), marcadas las suyas, en el orden del catálogo |
| Redes | `redes[].{red, valor}`, hasta 5 | [Filas repetibles](../patrones/formularios.md#composición) como en [RF-17](RF-17-perfil.md#datos): RED (Selector) + USUARIO O ENLACE |
| Guardar | `PATCH /profesionales/{id} {nombre_artistico, presentacion, redes, especialidades: [id]}` → 200 `Profesional` | Vacíos opcionales se envían como `null` |
| Foto | `foto_url`; `PUT /profesionales/{id}/foto` (`archivo`) → 200 · `DELETE …/foto` → 204 | [Carga de archivos](../componentes/carga-archivos.md#foto-de-perfil) Foto de perfil con [avatar](../componentes/avatar.md) Miniatura |
| Publicación | `publicado`, `activo`, `especialidades`, `duraciones` | [Etiqueta](../componentes/etiqueta-tecnica.md) Éxito PUBLICADO o Aviso SIN PUBLICAR; lo que falta, en texto |
| Precios | `duraciones[].{minutos, precio}` | "30 min · S/ 80,00"; duración sin precio: "No ofreces asesorías de 1 h" |

## Composición

| Región | Componente (variante) | Contenido |
|---|---|---|
| Encabezado | [encabezado-pantalla](../componentes/encabezado-pantalla.md) App | Ruta, índice, título y descripción; ranura `acciones`: "Ver mi perfil público" ([botón](../componentes/boton.md) Secundario como enlace, `external-link`, pestaña nueva), solo si `publicado` |
| Avisos | [aviso](../componentes/aviso.md) | Resultado + Información "Tu perfil aún no es público. Falta: {lista}." si `publicado = false` |
| Principal (un `<form>`) | [panel](../componentes/panel.md) `F1 PRESENTACIÓN` → `F2 ESPECIALIDADES` → `F3 REDES` | F1: `<dl>` NOMBRE + nombre artístico + presentación. F2: `<fieldset>` de casillas. F3: filas. Al final, Primario "Guardar ficha" (sin barra de acciones) |
| Lateral | panel Lateral `F4 FOTO` (su propio `<form>`) | Avatar Miniatura con la foto o las iniciales → "Elegir foto" / "Cambiar foto" → con archivo elegido, Secundario "Subir foto"; con foto guardada, Secundario "Quitar foto" |
| Lateral | panel Lateral `F5 PUBLICACIÓN` | `<dl>`: ESTADO (etiqueta), ACTIVO ("Sí" / "No"), PRECIOS (una línea por duración); ayuda "La activación y los precios los fija el Administrador."; enlace "Mis horarios" |

Lista de "Falta", en este orden y unida con comas: "que el Administrador active tu perfil" (`activo = false`), "elegir al menos una especialidad" (sin especialidades), "que el Administrador fije tus precios" (`duraciones` vacío). Patrones: [formularios](../patrones/formularios.md), [estados del sistema](../patrones/estados-sistema.md). Adaptabilidad: < `punto-quiebre-escritorio`, una columna: avisos → F1 a F3 → F4 → F5; filas de redes en una columna < `punto-quiebre-tableta`.

## Estados

| Bloque | Situación | Forma y texto |
|---|---|---|
| Ficha | Carga | Paneles con "Cargando…", `aria-busy` |
| F2 | Catálogo vacío | "Aún no hay especialidades. El Administrador debe crearlas antes de que elijas." Sin casillas; se puede guardar lo demás |
| Validación | Al salir y al enviar (también 422 `datos_invalidos` con `detalles.campo`) | "El nombre artístico admite hasta 80 caracteres." · "La presentación admite hasta 600 caracteres." · "Elige al menos una especialidad." · "Elige como máximo 5 especialidades." · "Elige la red." · "Escribe tu usuario o el enlace." Aviso resumen "Revisa {n} campos" con enlaces |
| F2 | 422 por especialidad inactiva | Se recarga el catálogo (la inactiva desaparece) + aviso Información "Una especialidad ya no está disponible y la quitamos. Revisa y vuelve a guardar." Lo demás se conserva |
| F3 | 5 redes | "Añadir red" se oculta; ayuda "Máximo 5 redes." |
| Guardar | Enviando · éxito | Primario en Carga "Guardando…"; aviso Éxito "Ficha guardada." (y "Ya está en el directorio." si pasó a publicado). F5 se repinta |
| F4 | Elección inválida en el navegador | Error del campo: "La foto pesa más de 2 MB. Elige una más liviana." · "Elige una foto JPG, PNG o WebP." |
| F4 | 413 `archivo_muy_grande` · 422 `formato_no_admitido` | Los mismos textos; la foto anterior sigue |
| F4 | Subiendo · quitando · éxito | "Subiendo…" / "Quitando…" en el botón; aviso Éxito en F4 "Foto actualizada." / "Foto quitada. Se mostrarán tus iniciales." |
| Todas | 401 | Aviso "Tu sesión no es válida. Inicia sesión para continuar." + "Ir al acceso interno" (`?volver=/app/ficha/`) |
| Todas | 403 | En lugar de la vista: `[403] SIN PERMISO` "Esta sección es para los profesionales de asesoría." + "Volver al inicio" |
| Todas | 404 (la cuenta ya no tiene ficha) | Aviso Información "Tu cuenta ya no tiene ficha de profesional. Si crees que es un error, habla con el Administrador." + "Volver al inicio" |
| Todas | 503 · red caída · no JSON | "El servicio no responde. Inténtalo de nuevo en unos minutos." · "Sin conexión. Revisa tu red y vuelve a intentarlo." · "Algo salió mal. Inténtalo de nuevo." Al cargar con "Reintentar"; al enviar, sin él y con los datos conservados |
| Todas | Sin JS | `<noscript>`: aviso Información "Esta sección necesita JavaScript. Actívalo en tu navegador y recarga la página." |

Permisos: el profesional nunca ve controles de ACTIVO ni de precios (CA-03); se le muestran como lectura en F5. Mientras se envía un formulario, el otro sigue usable (son independientes).

## Copy

| Elemento | Texto |
|---|---|
| Ruta, índice, título | Inicio / Ficha · `[E1] ASESORÍAS / FICHA` · FICHA PÚBLICA |
| Descripción | Lo que ven los artistas en el directorio de asesorías. Mantén tu presentación al día. |
| Ayudas | NOMBRE: "Es el de tu cuenta. Cámbialo en Mi perfil." (enlace a `/app/perfil`) · NOMBRE ARTÍSTICO "Opcional. Si lo tienes, se muestra primero." · PRESENTACIÓN "Opcional. Cuenta qué haces y cómo puedes ayudar. Máximo 600 caracteres." · ESPECIALIDADES (`<legend>`) "Elige de 1 a 5." · F4 "JPG, PNG o WebP, hasta 2 MB. Sin foto, se muestran tus iniciales." |
| Acciones | Guardar ficha · Elegir foto · Cambiar foto · Subir foto · Quitar foto · Añadir red · "Quitar red {n}" · Ver mi perfil público · Mis horarios |

## Accesibilidad

- `<h1>` del encabezado; cada panel `<section>` con `<h2>`; ESPECIALIDADES y cada fila de red, `<fieldset>` + `<legend>`.
- Orden de foco: encabezado → avisos → F1 → F2 → F3 → "Guardar ficha" → F4 → F5.
- Región `role="status"` estable de la isla: carga y resultados; al fallar un envío, el foco va al aviso. La vista previa de la foto se anuncia ("Foto elegida: retrato.jpg, 1,2 MB. Pulsa Subir foto para guardarla.").
- La foto en la vista previa lleva `alt="Tu foto actual"` / `alt="Vista previa de la foto elegida"`: aquí no hay nombre al lado.

## Pendientes

- **leader / dev-backend:** ¿`Profesional.id` es el `id` del usuario? Lo damos por hecho para usar `GET /perfil`; si no, proponemos `Perfil.id_profesional`.
- **leader:** destino FICHA (`id-card`, concepto nuevo de la [tabla de iconos](../fundamentos/iconografia-imagen.md#iconos)) para `profesional`, junto a HORARIOS; INICIO del profesional sin contenido propio en la etapa A.
