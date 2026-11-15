---
id: pantalla-rf-01-acceso
titulo: Pantalla — Acceso de artistas
estado: borrador
depende_de: [RF-01, ADR-008, diseno-brief, patron-estructura-app, patron-formularios, patron-estados-sistema, patron-flujo-por-pasos, comp-campo, comp-boton, comp-aviso, comp-marco-registro]
---

# Acceso de artistas

| Campo | Valor |
|---|---|
| Requerimiento | [RF-01](../../03-requerimientos/RF-01.md): CA-01 a CA-04, CA-06, CA-12, CA-13 |
| Actores | Visitante y Artista/Cliente. El inicio de sesión vale para cualquier rol |
| Estructura | Acceso ([estructura de app](../patrones/estructura-app.md#acceso)); dentro de un flujo, Flujo |
| Ruta | `/acceso` (iniciar sesión) y `/acceso/registro` (crear cuenta). URL: `volver`, `aviso`, `error` |
| Isla | `<bugalu-acceso modo="iniciar\|registrar">` (nueva) y [`<bugalu-contrasena>`](../componentes/campo.md#medidor-de-robustez) |
| Origen Figma | `112:286` login-artista, `112:385` registro-artista (volcado local) |

## Recorrido

1. Llega desde la landing ("Ingresar a mi portal", `48:301`), desde un 401 de una isla ("Ir al acceso"), tras cerrar sesión o desde el paso de cuenta de un flujo.
2. **Iniciar sesión:** correo y contraseña contra Supabase Auth (`signInWithPassword`). Éxito: va a `volver` o, si no hay, a `/app/`.
3. **Sin cuenta:** "Crear cuenta de artista" lleva a `/acceso/registro` (conserva `volver`). Nombre, teléfono, nombre artístico, correo y contraseña con medidor → `signUp` con metadatos → destino con `?aviso=cuenta-creada`. Destino por defecto: `/app/perfil`, que recuerda confirmar el correo ([perfil](RF-01-perfil.md)).
4. **Google** (solo si está configurado, CA-04): `signInWithOAuth` con `redirectTo` al destino. Si vuelve con error: `/acceso?error=google`.
5. "¿Olvidaste tu contraseña?" lleva a [restablecer](RF-01-restablecer.md).
6. **Cerrar sesión** (CA-12): opción del menú de la [cabecera](../componentes/cabecera-app.md) en toda vista App. `signOut({ scope: 'local' })` borra la sesión del navegador aunque falle la red; luego `/acceso?aviso=sesion-cerrada` (personal y Administrador: `/acceso/interno?aviso=sesion-cerrada`).

`volver` solo acepta rutas propias: empieza por `/`, no por `//` y no contiene `\`. Si no, se ignora (evita redirecciones abiertas).

### Desde un flujo (reservar o agendar)

- El paso de cuenta de [registrar reserva](../../02-dominio/flujos/registrar-reserva.md) y [agendar asesoría](../../02-dominio/flujos/agendar-asesoria.md) (paso 3) **incrusta este formulario de registro** en un [panel](../componentes/panel.md) `C1 CREA TU CUENTA` dentro de la estructura Flujo, sin columnas de marca: el visitante no sale del flujo ([flujo por pasos](../patrones/flujo-por-pasos.md#reglas), regla 7). La spec de RF-04 o RF-15 fija el paso; campos, estados y copy son los de aquí.
- "¿Ya tienes cuenta? Inicia sesión" cambia el mismo paso a `?cuenta=iniciar`; "Crear cuenta de artista" vuelve a `?cuenta=registrar`.
- Al terminar, la isla va a la URL del paso siguiente (atributo `destino` que pone la página del flujo), con `?aviso=cuenta-creada` si se registró. Si al cargar el paso ya hay sesión, salta al siguiente.
- Lo elegido antes lo guarda el flujo. Si el flujo ya pidió nombre o correo, llegan prellenados (WCAG 3.3.7).

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Correo | Supabase Auth `email` | `type="email"`, `autocomplete="email"` |
| Contraseña | Supabase Auth `password` | Iniciar: `current-password`. Registrar: `new-password` + [medidor](../componentes/campo.md#medidor-de-robustez) |
| Nombre | Metadato `nombre` de `signUp` → `Perfil.nombre` | Texto, `autocomplete="name"` |
| Teléfono | Metadato `telefono` → `Perfil.telefono` | `type="tel"`, `autocomplete="tel"`; la isla quita espacios; 9 a 15 dígitos, `+` inicial opcional |
| Nombre artístico | Metadato `nombre_artistico` → `Perfil.nombre_artistico` | Texto, tal cual |
| Google disponible | Variable pública de entorno (p. ej. `PUBLIC_ACCESO_GOOGLE`), leída al construir | Si no está, el botón no se pinta |

En el registro los cinco datos son obligatorios (CA-01).

## Composición

| Región | Componente (variante) | Contenido |
|---|---|---|
| Marca (`<header>`) | Logotipo apilado (enlace a `/`, `medida-logo-acceso` en escritorio), título técnico, texto y dos [etiquetas](../componentes/etiqueta-tecnica.md) Neutra (decorativas: no son un [indicador](../componentes/indicador-estado.md) de estado del sistema) | Textos de la tabla Copy. Como en Figma (`112:288`, `112:316`): logotipo, título técnico y texto juntos arriba (`espacio-6` del logo al título); las etiquetas, al pie de la columna sobre una regla `borde-grosor-fino` |
| Visual (`<aside>`) | [Marco de registro](../componentes/marco-registro.md) Panel | Título y nota de la tabla Copy |
| Formulario (`<main>`) | [Etiqueta](../componentes/etiqueta-tecnica.md) Invertida (antetítulo), `<h1>`, [aviso](../componentes/aviso.md) de resultado, [campos](../componentes/campo.md), [botón](../componentes/boton.md) Primario grande a ancho completo | Ver orden abajo |
| Pie | Texto técnico (`fuente-familia-tecnica`, `fuente-tamano-micro`) y enlace | "SALA VIRTUAL BUGALÚ STUDIO © 2026" · "¿Eres del equipo? Acceso interno" ([acceso interno](RF-01-acceso-interno.md)) |

- **Iniciar:** correo → contraseña (con mostrar) → enlace "¿Olvidaste tu contraseña?" a la derecha → "Entrar al portal" → si hay Google: separador "O" y [botón](../componentes/boton.md) Secundario a ancho completo "Continuar con Google" → enlace a registro.
- **Registrar:** nombre → teléfono → nombre artístico → correo → contraseña con medidor → "Crear cuenta de artista" → Google (igual) → enlace a iniciar sesión. Una columna ([formularios](../patrones/formularios.md#accesos)).

Adaptabilidad: < `punto-quiebre-escritorio`, marca compacta (logotipo a `medida-logo-min` + título técnico) y formulario; la columna visual y el texto de marca no se muestran. El formulario sigue a la marca compacta sin hueco añadido: el alto sobrante de la ventana va a la columna del formulario, para que el pie quede abajo, nunca entre marca y formulario. Controles ≥ `medida-control-tactil`.

**Decisiones del brief frente a Figma:** sin "Confirmar contraseña" (`112:466`): mostrar + medidor bastan y no se pide dos veces un dato. Sin "Género / disciplina" (`112:457`): el RF no lo pide. Sin casilla de condiciones (`112:472`, ver Pendientes). Sin "Recordar sesión" (`112:373`). Google como botón solo de texto: los iconos son Lucide y no trae logotipos de marcas. Voz en tú: "Recuperar clave" pasa a "¿Olvidaste tu contraseña?".

## Estados

El formulario se pinta en el servidor; la isla lo envía. Errores de Supabase Auth por `code` (esta tabla vale también para [acceso interno](RF-01-acceso-interno.md) y [restablecer](RF-01-restablecer.md)):

| Situación | Forma | Texto |
|---|---|---|
| Enviando | Botón en Carga; Google deshabilitado | "Entrando…" / "Creando cuenta…" |
| Error de campo (al salir o al enviar) | Error bajo el campo; al enviar, aviso Error resumen con enlaces | "Revisa 2 campos" + un enlace por campo |
| `invalid_credentials` | Aviso Error, sin marcar campos; conserva el correo y vacía la contraseña | "Correo o contraseña incorrectos. Revísalos o recupera tu contraseña." (CA-03) |
| `user_already_exists` / `email_exists` | Error en el campo correo | "Ya hay una cuenta con este correo. Inicia sesión o recupera tu contraseña." |
| `weak_password` | Error en la contraseña | El del [medidor](../componentes/campo.md#medidor-de-robustez): qué condición falta |
| 429 / `over_*_rate_limit` | Aviso Error | "Demasiados intentos. Espera unos minutos y vuelve a intentarlo." |
| 5xx del servicio | Aviso Error; datos conservados | "El servicio de acceso no responde. Inténtalo de nuevo en unos minutos." |
| Red caída | Aviso Error; datos conservados | "Sin conexión. Revisa tu red y vuelve a intentarlo." |
| Otra respuesta (no JSON, desconocida) | Aviso Error | "Algo salió mal. Inténtalo de nuevo." |
| Cuenta creada sin sesión (el servicio exige confirmar) | Aviso Información; formulario oculto | "Cuenta creada. Verifica tu correo con el enlace que te enviamos y luego inicia sesión." |
| `?error=google` | Aviso Error arriba | "No pudimos entrar con Google. Inténtalo de nuevo o usa tu correo." |
| `?aviso=sesion-cerrada` | Aviso Información arriba | "Cerraste sesión." |
| Éxito | Navega al destino; el destino muestra `cuenta-creada` | "Cuenta creada. Ya puedes reservar." |
| Sin JS | `<noscript>`: oculta el formulario y muestra aviso Información | "El acceso necesita JavaScript. Actívalo en tu navegador y recarga la página." |

Claves `aviso` de RF-01 ([estados del sistema](../patrones/estados-sistema.md#éxito)): `sesion-cerrada`, `cuenta-creada`, `contrasena-cambiada`, `solicitud-enviada`, `solicitud-aprobada`, `solicitud-rechazada`, `usuario-actualizado`.

Permisos: pantalla pública. 401, 403 y 503 de la API no aplican aquí (solo Supabase Auth).

## Copy

| Elemento | Iniciar sesión | Registrar |
|---|---|---|
| `<title>` y `<h1>` | Iniciar sesión · INICIAR SESIÓN | Registro artístico · REGISTRO ARTÍSTICO |
| Antetítulo | ACCESO DE ARTISTAS | NUEVA CUENTA DE ARTISTA O BANDA |
| Marca | `[PORTAL_ARTISTAS]` "Escucha tus premezclas, aprueba versiones, pide ajustes a nuestros ingenieros y revisa el historial de tus sesiones." | `[ALTA_CREADORES]` "Regístrate para llevar tu proyecto musical en un solo lugar: reserva sesiones, revisa versiones y habla con el estudio." |
| Etiquetas de marca | ESTADO: LISTO · CONVERGE Y CREA | CONEXIÓN DIRECTA · CREADORES BIENVENIDOS |
| Visual | NUESTRAS SALAS DE SEGUIMIENTO: "Descarga tus versiones en WAV de alta resolución y en MP3 para escucharlas en el móvil." | REGISTRA TU PROYECTO: "Recibe tus premezclas y envía tus comentarios en el mismo lugar." |
| Acción principal | Entrar al portal | Crear cuenta de artista |
| Enlace al otro modo | ¿Aún no tienes cuenta? Crear cuenta de artista | ¿Ya tienes cuenta? Inicia sesión |

Etiquetas (con `//` del layout): CORREO, CONTRASEÑA, NOMBRE, TELÉFONO, NOMBRE ARTÍSTICO O PROYECTO. Ayudas: teléfono "Solo números; con + y código de país si no es de Perú."; nombre artístico "Tu nombre de artista o el de tu banda." (ejemplo "p. ej. Los Sónicos"). Errores: "Escribe tu correo." · "Escribe un correo válido, como nombre@dominio.com." · "Escribe tu nombre." · "Escribe entre 9 y 15 dígitos; puedes empezar con +." · "Escribe tu nombre artístico o el de tu proyecto." · "Escribe una contraseña."

## Accesibilidad

- "Saltar al contenido" primero; `<header>` (marca), `<main id="contenido">` (formulario), `<aside>` (visual, marcas `aria-hidden`). Un solo `<h1>`, igual al `<title>`; dentro de un flujo el bloque baja a `<h2>` (título del panel).
- Orden de foco = visual: logotipo → campos → "¿Olvidaste tu contraseña?" → principal → Google → enlace al otro modo → pie.
- La isla pone `novalidate` y aplica las mismas reglas (`required`, `type`, `minlength`) con los mensajes del brief. Al fallar el envío, el foco va al aviso (`tabindex="-1"`, sin rol vivo: el foco ya lo lee); el error de un campo se une con `aria-describedby`.
- Medidor y su anuncio: [ficha de campo](../componentes/campo.md#medidor-de-robustez). Enlaces de texto con objetivo ≥ 24 px (WCAG 2.5.8).

## Pendientes

- **dev-backend / dev-frontend:** los metadatos de `signUp` se llaman `nombre`, `telefono` y `nombre_artistico` (migración de RF-01 en curso). El disparador descarta en silencio un teléfono mal formado, así que la isla debe validarlo (sin espacios, 9 a 15 dígitos) antes de llamar a `signUp`.
- **Usuario:** ¿el registro pide aceptar condiciones (`112:472`)? El texto legal no se redacta aquí.
- **Usuario:** quien entra con Google no da teléfono ni nombre artístico; por ahora los completa en el [perfil](RF-01-perfil.md).
- **leader:** registrar `<bugalu-acceso>` en [frontend-islas](../../01-arquitectura/frontend-islas.md) (fuera del alcance de diseño).
