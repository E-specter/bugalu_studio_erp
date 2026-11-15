# Bugalú Studio — ERP

> Documento inicial del proyecto. Fuente de verdad hasta que se segmente en `docs/` (ver §7).
> Versión 0.2 · Estado: borrador base

---

## 1. Contexto

| Campo | Valor |
|---|---|
| Cliente | Bugalú Studio — estudio de producción y grabación musical |
| Producto | ERP web estandarizado para la operación del estudio |
| Alcance | Usuarios, catálogo y cotizaciones, reservas de sala, pagos, personal técnico, proyectos musicales, entregables de audio, feedback, cierre y reportes |
| Desarrollo | Agéntico con Claude Code, multiagente (ver §6) |

---

## 2. Stack tecnológico

| Capa | Tecnología |
|---|---|
| Base de datos | PostgreSQL gestionado en Supabase |
| Backend | Python · `uv` (gestor de dependencias y entornos) · FastAPI |
| Frontend | Astro · componentes propios en HTML, CSS y JavaScript nativo (sin frameworks UI) |
| Almacenamiento de archivos | Pendiente: AWS S3 o Supabase Storage (ver §12, D-01) |
| Diseño visual | Figma, conectado a Claude Code mediante el MCP oficial (ver §13) |
| Herramientas agénticas | MCP y skills de Claude Code (ver §14) |
| Documentación | Markdown en `docs/`, atómica por especificación |

---

## 3. Arquitectura

### 3.1 Backend — Hexagonal + Vertical Slicing

**Principios obligatorios**
- SOLID.
- Arquitectura hexagonal (puertos y adaptadores) en tres capas: `dominio`, `aplicacion`, `infraestructura`.
- Vertical slicing: cada caso de uso es una porción autocontenida dentro de su módulo.

**Regla de dependencias**
```
infraestructura  →  aplicacion  →  dominio
```
- `dominio`: entidades, objetos de valor, reglas de negocio y puertos (interfaces). Sin dependencias de FastAPI, Supabase ni librerías externas.
- `aplicacion`: casos de uso. Orquesta el dominio mediante puertos. Sin conocimiento de HTTP ni de la base de datos.
- `infraestructura`: adaptadores de entrada (routers FastAPI, esquemas Pydantic) y de salida (repositorios Supabase, pasarela de pagos, correo, almacenamiento).

**Estructura**
```
backend/
├── pyproject.toml
├── src/bugalu/
│   ├── main.py                     # composición de la app y registro de routers
│   ├── compartido/                 # kernel compartido: errores, tipos base, eventos, configuración
│   └── modulos/
│       └── reservas/               # un módulo por contexto (ver §3.3)
│           ├── dominio/
│           │   ├── reserva.py
│           │   ├── estado_reserva.py
│           │   ├── reglas.py       # buffer técnico, solapamientos
│           │   └── puertos.py      # RepositorioReservas, ServicioNotificaciones
│           ├── aplicacion/
│           │   ├── registrar_reserva/
│           │   │   ├── comando.py
│           │   │   └── caso_de_uso.py
│           │   └── cambiar_estado_reserva/
│           └── infraestructura/
│               ├── entrada/http/   # router.py, esquemas.py
│               └── salida/         # repositorio_supabase.py
└── tests/                          # espejo de src/: unitarios, integración, api
```

### 3.2 Frontend — Arquitectura de Islas (Astro)

- HTML estático por defecto; JavaScript solo en las islas que requieren interactividad.
- Islas implementadas como componentes `.astro` con `<script>` que registra Web Components (`customElements.define`). Las directivas `client:*` no aplican: son para componentes de frameworks UI.
- HTML semántico (`<main>`, `<nav>`, `<section>`, `<form>`, `<button>`), accesibilidad (ARIA solo cuando el elemento nativo no basta) y manipulación del DOM mínima.
- CSS con tokens de diseño (variables CSS) centralizados.

**Estructura**
```
frontend/
├── astro.config.mjs
├── public/
└── src/
    ├── pages/            # rutas (nombre reservado por Astro)
    ├── layouts/          # nombre reservado por convención Astro
    ├── componentes/      # .astro estáticos, sin JS
    ├── islas/            # interactivos: calendario, reproductor, carga de archivos
    ├── servicios/        # cliente HTTP hacia la API
    └── estilos/          # tokens.css, base.css
```

**Islas identificadas**

| Isla | Requerimiento |
|---|---|
| Calendario de salas | RF-03, RF-04 |
| Resumen y pago de reserva | RF-05 |
| Carga de entregables (drag-and-drop) | RF-09 |
| Reproductor con forma de onda y comentarios por timestamp | RF-10 |

### 3.3 Módulos del backend

| Módulo | Requerimientos |
|---|---|
| `identidad` | RF-01 |
| `catalogo` | RF-02 |
| `reservas` | RF-03, RF-04, RF-06 |
| `pagos` | RF-05, RF-11 |
| `personal` | RF-07 |
| `proyectos` | RF-08, RF-13 |
| `entregables` | RF-09, RF-10, RF-12 |
| `reportes` | RF-14 |
| `notificaciones` | Transversal (RF-06) |

### 3.4 Correspondencia con el análisis BCE del informe

| BCE (informe RUP) | Implementación |
|---|---|
| Boundary (`FrmCalendarioSalas`, `FrmReproductorFeedback`) | Islas del frontend + routers FastAPI |
| Control (`CtrlGestionReservas`, `CtrlVersionadoAudio`) | Casos de uso en `aplicacion/` |
| Entity (`Reserva`, `VersionAudio`) | Entidades en `dominio/` + tablas en PostgreSQL |

---

## 4. Convenciones

### 4.1 Idioma y nomenclatura
- Todo identificador (código, base de datos, rutas, documentación) en español.
- Identificadores en ASCII: sin tildes ni `ñ` (`anio`, `contrasena`, `version_audio`). Contenido y datos en UTF-8, compatibles con caracteres internacionales.
- Nombres reservados por frameworks se conservan (`src/pages`, `public`, `main.py`).

| Ámbito | Formato | Ejemplo |
|---|---|---|
| Python: módulos, funciones, variables | `snake_case` | `registrar_reserva` |
| Python: clases | `PascalCase` | `RepositorioReservas` |
| JavaScript: variables, funciones | `camelCase` | `cargarDisponibilidad` |
| Web Components | `kebab-case` con prefijo | `<bugalu-calendario>` |
| PostgreSQL: tablas, columnas | `snake_case` singular | `sala_tecnica.tarifa_hora` |
| Endpoints REST | `kebab-case` plural | `/api/v1/reservas` |
| Archivos de documentación | `kebab-case` | `reglas-negocio.md` |

### 4.2 Control de versiones
- Ramas: `feat/RF-04-registrar-reserva`, `fix/<id>-<descripcion>`, `docs/<tema>`.
- Commits: Conventional Commits en español (`feat(reservas): aplicar buffer técnico`).
- Toda rama referencia un RF o una tarea.

---

## 5. Dominio

### 5.1 Actores del sistema

| Actor | Tipo | Descripción |
|---|---|---|
| Artista / Cliente | Humano | Músico, banda o artista independiente que contrata servicios |
| Ingeniero de Audio | Humano (personal interno) | Ingeniero de grabación, operador de mezcla o asistente de cabina |
| Administrador | Humano | Gestiona operación, personal, estados y reportes |
| Pasarela de Pagos / Banco | Sistema externo | Procesa anticipo y liquidación |
| Almacenamiento Cloud | Sistema externo | Custodia multipistas, mezclas y másteres |

Actores de negocio sin rol definido en el sistema: Sello discográfico / Mánager, Músico de sesión (ver §12, D-10).

### 5.2 Salas técnicas

| Sala | Uso |
|---|---|
| Sala A | Grabación |
| Sala B | Mezcla / Masterización |
| Sala C | Cabina / Posproducción |

### 5.3 Servicios del catálogo
Grabación acústica · Mezcla · Masterización · Live sessions.

### 5.4 Reglas de negocio

| ID | Regla |
|---|---|
| RN-01 | Dos reservas de la misma sala no pueden solaparse. |
| RN-02 | Toda reserva genera un buffer técnico automático de 30 min posterior a su fin (desinfección y calibración). El buffer bloquea la sala. |
| RN-03 | Una reserva pasa a `Confirmada` solo tras validar el anticipo del 50%. |
| RN-04 | El anticipo se paga por pasarela digital o mediante comprobante bancario validado por el Administrador. |
| RN-05 | La liquidación (50% restante) se habilita tras la aprobación de la versión de mezcla o máster por el cliente. |
| RN-06 | La descarga del máster se habilita solo tras la liquidación. |
| RN-07 | El enlace de descarga es cifrado, autenticado y caduca a los 7 días calendario. |
| RN-08 | Nomenclatura de entregables incremental y automática: `PRJ<nn>_<Track>_v<mayor>.<menor>.wav` (ej. `PRJ01_Track_v1.0.wav`). |
| RN-09 | Solo se aceptan entregables WAV sin pérdida. |
| RN-10 | Cada proyecto tiene un límite de rondas de corrección pactadas; cada observación consume del saldo según la ronda vigente. |
| RN-11 | El personal técnico se asigna según la especialidad del proyecto, solo a sesiones `Confirmada`. |

### 5.5 Estados de reserva

```
Pre-reservada ──(anticipo validado)──► Confirmada ──► En curso ──► Finalizada
      │                                    │
      └────────────► Cancelada ◄───────────┘
```
Cada cambio de estado notifica por correo al artista y al personal asignado (RF-06).
Transiciones inferidas del informe; validar en `docs/02-dominio/estados-reserva.md`.

### 5.6 Ciclo de servicio

1. **Contratación:** catálogo → cotización → reserva (`Pre-reservada`) → anticipo 50% → `Confirmada`.
2. **Producción:** asignación de personal → calibración en buffer → sesión → respaldo de multipistas.
3. **Posproducción y cierre:** carga de versión → auditoría del cliente con observaciones por timestamp → aprobación → liquidación 50% → descarga del máster (7 días) → evaluación de satisfacción.

---

## 6. Modelo de desarrollo multiagente

### 6.1 Roles

| Rol | Identificador | Responsabilidad | Alcance de escritura |
|---|---|---|---|
| Orquestador | `leader` | Interpreta solicitudes, consulta `docs/`, descompone en tareas, asigna, integra resultados, mantiene la arquitectura, el índice documental y el brief de diseño | `docs/`, `CLAUDE.md`, `.claude/`, `.mcp.json` |
| Backend | `dev_backend` | Dominio, casos de uso, adaptadores, API, migraciones y políticas RLS | `backend/`, `supabase/`, `docs/` del módulo |
| Frontend | `dev_frontend` | Páginas, layouts, componentes, islas, estilos y consumo de API; implementa desde Figma vía MCP | `frontend/`, `docs/` del módulo |
| Auditor | `dev_audit` | Verifica cumplimiento de especificación, arquitectura, convenciones, seguridad, pruebas y fidelidad visual. Emite dictamen | Solo lectura; escribe únicamente informes de auditoría |

**Restricciones**
- `leader` no implementa código de producción; delega.
- Ningún desarrollador modifica fuera de su alcance. Los cambios que cruzan capas se dividen en tareas por rol.
- `dev_audit` no corrige: reporta. La corrección vuelve al desarrollador responsable.
- Contratos de API (OpenAPI) los define `dev_backend` y los aprueba `leader` antes de que `dev_frontend` los consuma.
- Ningún agente escribe en el lienzo de Figma sin aprobación explícita del usuario. Figma se consume en lectura.

### 6.2 Implementación en Claude Code
- Sesión principal = `leader`.
- Subagentes definidos en `.claude/agents/<rol>.md` (frontmatter: `name`, `description`, `tools`). `dev_audit` sin herramientas de edición.
- `CLAUDE.md` en la raíz: punto de entrada mínimo que remite a `docs/README.md`.
- `.mcp.json` en la raíz (alcance de proyecto): servidores MCP compartidos, versionado sin credenciales.
- `.claude/skills/<nombre>/SKILL.md`: procedimientos repetibles del proyecto (ver §14.3).
- El campo `tools` de cada subagente limita qué MCP puede usar (matriz en §14.2).
- Especificación completa de cada rol en `docs/04-agentes/<rol>.md`.

### 6.3 Flujo de trabajo

```
1. leader       → lee RF y specs relacionadas, crea tarea
2. dev_backend  → implementa + pruebas + actualiza docs del módulo
   dev_frontend → implementa sobre contrato aprobado + pruebas
3. dev_audit    → revisa contra spec y criterios → APROBADO | RECHAZADO
4. leader       → integra, actualiza changelog e índice documental
```
Rechazo en paso 3 → vuelve al paso 2 con el informe de auditoría.

### 6.4 Formato de tarea (leader → dev)

```markdown
## TAREA-<nnn>: <título>
- Rol: dev_backend | dev_frontend
- Requerimiento: RF-xx
- Specs: docs/...md (lista explícita)
- Objetivo: <una frase>
- Criterios de aceptación: <lista verificable>
- Archivos permitidos: <rutas>
- Fuera de alcance: <lista>
```

### 6.5 Formato de entrega (dev → audit)

```markdown
## ENTREGA TAREA-<nnn>
- Archivos modificados: <lista>
- Pruebas añadidas y resultado: <comando + salida resumida>
- Documentación actualizada: <rutas>
- Desviaciones de la spec: <ninguna | detalle>
```

### 6.6 Criterios de auditoría
1. Cumple criterios de aceptación de la tarea.
2. Respeta la regla de dependencias hexagonal (dominio sin imports de infraestructura).
3. Respeta convenciones (§4).
4. Pruebas presentes y en verde.
5. Seguridad: validación de entradas, autorización por rol, secretos fuera del código.
6. Documentación actualizada.
7. Frontend: usa exclusivamente tokens y componentes existentes; captura de Playwright coincide con el frame de Figma referenciado.

---

## 7. Documentación

### 7.1 Principios
- `docs/` es la fuente de verdad. El código implementa lo documentado; si difieren, se corrige uno de los dos en la misma tarea.
- Atómica: un concepto por archivo, máximo ~150 líneas.
- Sin duplicación: se enlaza, no se copia.
- Cada archivo inicia con frontmatter:
  ```yaml
  ---
  id: RF-04
  titulo: Registrar reserva de sala técnica
  estado: borrador | aprobado | implementado
  depende_de: [RN-01, RN-02, RF-03]
  ---
  ```
- Los agentes leen `docs/README.md` y cargan solo los archivos que la tarea referencia.

### 7.2 Estructura

```
docs/
├── README.md                    # índice maestro y ruta de lectura por rol
├── 00-proyecto/
│   ├── vision.md
│   ├── alcance.md
│   ├── glosario.md
│   └── decisiones/              # ADR-001-almacenamiento.md, ...
├── 01-arquitectura/
│   ├── stack.md
│   ├── backend-hexagonal.md
│   ├── frontend-islas.md
│   ├── modelo-datos.md
│   └── convenciones.md
├── 02-dominio/
│   ├── actores-roles.md
│   ├── reglas-negocio.md
│   ├── estados-reserva.md
│   └── flujos/                  # registrar-reserva.md, versionado-feedback.md
├── 03-requerimientos/
│   └── RF-01.md … RF-14.md
├── 04-agentes/
│   ├── leader.md
│   ├── dev-backend.md
│   ├── dev-frontend.md
│   └── dev-audit.md
├── 05-protocolos/
│   ├── cambios.md
│   ├── implementacion.md
│   ├── pruebas.md
│   └── integracion.md
├── 06-operacion/
│   ├── montaje-local.md
│   ├── entornos.md
│   ├── despliegue.md
│   └── herramientas-mcp.md      # instalación y alcance de MCP y skills
└── 07-diseno/
    ├── brief.md                 # documento rector del diseño visual
    ├── figma.md                 # archivo, páginas, convenciones de nombres
    ├── tokens.md                # correspondencia variables Figma ↔ CSS
    ├── componentes.md           # catálogo: nombre Figma ↔ componente/isla
    └── pantallas/               # una spec por pantalla con enlace al frame
```

---

## 8. Protocolos (resumen; detalle en `docs/05-protocolos/`)

| Protocolo | Contenido mínimo |
|---|---|
| Cambios | Solicitud → impacto en specs → ADR si altera arquitectura → aprobación de `leader` |
| Implementación | Spec aprobada → tarea → rama → código + pruebas + docs → entrega |
| Pruebas | Unitarias (dominio), integración (adaptadores), API (endpoints), E2E (flujos críticos). Herramientas propuestas: `pytest`, `ruff`, `mypy`; `astro check`, Playwright |
| Integración | Auditoría aprobada → pruebas en verde → merge a rama principal → changelog |

---

## 9. Entornos

| Entorno | Base de datos | Ejecución |
|---|---|---|
| Desarrollo | Supabase local (CLI) | `uv run fastapi dev` · `npm run dev` |
| Pruebas | Proyecto Supabase independiente | Despliegue automático desde rama de integración |
| Producción | Proyecto Supabase de producción | Despliegue controlado tras aprobación |

Hosting de backend y frontend: pendiente (ver §12, D-08). Detalle en `docs/06-operacion/`.

---

## 10. Requerimientos funcionales

| Código | Requerimiento | Caso de uso (CUS) | Actores |
|---|---|---|---|
| RF-01 | Registro, autenticación segura y gestión de perfiles con privilegios diferenciados (cliente/artista, personal interno de cabina, administrador). | CUS-01 Autenticar usuario y gestionar perfil | Artista/Cliente, Administrador, Ingeniero de Audio |
| RF-02 | Exploración del catálogo de servicios técnicos (grabación acústica, mezcla, masterización, live sessions) y solicitud de cotizaciones formales detalladas. | CUS-02 Solicitar y generar cotización técnica | Artista/Cliente, Administrador |
| RF-03 | Disponibilidad en tiempo real de turnos por sala (A, B, C) en calendario dinámico. | CUS-03 Consultar disponibilidad de salas | Artista/Cliente, Ingeniero de Audio, Administrador |
| RF-04 | Reserva de bloques horarios con bloqueo de solapamientos y buffer técnico automático de 30 min. | CUS-04 Registrar reserva de sala técnica | Artista/Cliente, Administrador |
| RF-05 | Registro del anticipo (50%) por pasarela digital o comprobante bancario para confirmar la reserva. | CUS-05 Procesar pago de anticipo | Artista/Cliente, Pasarela de Pagos/Banco, Administrador |
| RF-06 | Actualización del estado de la reserva (Pre-reservada, Confirmada, En curso, Finalizada, Cancelada) con notificación por correo al artista y al personal asignado. | CUS-06 Gestionar estado de reserva y notificaciones | Administrador, Artista/Cliente |
| RF-07 | Asignación de ingenieros de grabación, operadores de mezcla y asistentes de cabina a sesiones confirmadas según especialidad. | CUS-07 Asignar personal técnico a sala | Administrador, Ingeniero de Audio |
| RF-08 | Ficha centralizada del proyecto musical: género, tomas pactadas, fechas límite y avance por fase. | CUS-08 Administrar ficha de proyecto musical | Administrador, Ingeniero de Audio, Artista/Cliente |
| RF-09 | Carga de archivos pesados (multipistas/stems WAV alta resolución) con nomenclatura incremental automática. | CUS-09 Cargar y versionar entregables de audio | Ingeniero de Audio, Almacenamiento Cloud |
| RF-10 | Reproductor integrado para auditar la mezcla en curso y registrar observaciones ancladas a timestamps. | CUS-10 Auditar audio y registrar observaciones técnicas | Artista/Cliente, Ingeniero de Audio |
| RF-11 | Liquidación final (50% restante) tras aprobación de la mezcla o máster por el cliente. | CUS-11 Liquidar saldo final de proyecto | Artista/Cliente, Pasarela de Pagos/Banco, Administrador |
| RF-12 | Enlace cifrado, autenticado y con caducidad de 7 días para descarga del máster aprobado tras la liquidación. | CUS-12 Descargar máster digital definitivo | Artista/Cliente, Almacenamiento Cloud |
| RF-13 | Evaluación de satisfacción y registro de conformidad técnica al cierre del proyecto. | CUS-13 Evaluar calidad y cierre de servicio | Artista/Cliente, Administrador |
| RF-14 | Reportes mensuales de ocupación y rendimiento: horas efectivas por sala, proyectos entregados, tiempos de entrega. | CUS-14 Generar reportes de operatividad y gestión | Administrador |

### 10.1 Flujos críticos

**CUS-04 Registrar reserva**
1. Cliente selecciona sala, fecha y horario en el calendario.
2. Caso de uso verifica operatividad de la sala y ausencia de solapamientos (RN-01).
3. Crea reserva `Pre-reservada` con buffer de 30 min (RN-02) y calcula el anticipo del 50%.
4. Cliente confirma; el módulo `pagos` procesa el cobro con la pasarela.
5. Con autorización (`codigo_autorizacion`), registra `comprobante_pago` y cambia la reserva a `Confirmada` (RN-03).
6. Devuelve folio de reserva al cliente.

**CUS-09/10 Versionado y feedback**
1. Ingeniero carga WAV; se valida formato sin pérdida (RN-09).
2. Se genera nomenclatura incremental (RN-08), se sube por multipart al almacenamiento y se crea `version_audio` en estado `En revision`.
3. Cliente reproduce la versión con forma de onda.
4. Al pausar en un instante, registra observación; se valida el saldo de rondas (RN-10) y se crea `observacion_tecnica` con timestamp.

---

## 11. Modelo de datos inicial

| Tabla | Campos clave | Relaciones |
|---|---|---|
| `usuario` | `id`, `correo` (único), `rol`, `especialidad` | — |
| `sala_tecnica` | `id`, `nombre`, `tipo`, `tarifa_hora`, `estado_operativo` | — |
| `reserva` | `id`, `inicio`, `fin`, `fin_buffer`, `estado`, `folio` | `id_cliente` → usuario · `id_sala` → sala_tecnica · `id_ingeniero` → usuario |
| `proyecto_musical` | `id`, `codigo` (PRJnn), `genero`, `tomas_pactadas`, `fecha_entrega`, `fase`, `rondas_pactadas`, `rondas_consumidas` | `id_cliente` → usuario |
| `version_audio` | `id`, `nombre_archivo`, `numero_version`, `ruta_almacenamiento`, `tamano_bytes`, `formato`, `estado_revision` | `id_proyecto` → proyecto_musical · `id_ingeniero` → usuario |
| `observacion_tecnica` | `id`, `marca_tiempo_ms`, `categoria`, `texto`, `ronda` | `id_version` → version_audio |
| `comprobante_pago` | `id`, `tipo` (anticipo/liquidacion), `monto`, `metodo`, `codigo_operacion`, `estado` | `id_reserva` → reserva (opcional) · `id_proyecto` → proyecto_musical (opcional) |
| `cotizacion` | `id`, `subtotal`, `descuento`, `total`, `fecha_vigencia`, `estado` | `id_cliente` → usuario |

**Entidades faltantes para cubrir los RF**

| Tabla propuesta | Requerimiento |
|---|---|
| `servicio` (catálogo) y `detalle_cotizacion` | RF-02 |
| `asignacion_sesion` (reserva × personal × función) | RF-07 — una reserva admite varios técnicos |
| `evaluacion_servicio` | RF-13 |
| `notificacion` (registro de envíos) | RF-06 |

---

## 12. Decisiones abiertas

| ID | Decisión | Opciones / contexto |
|---|---|---|
| D-01 | Almacenamiento de audio | El informe indica AWS S3; Supabase Storage es compatible con S3 y unifica el stack |
| D-02 | Pasarela de pagos | Sin definir |
| D-03 | Autenticación | Supabase Auth (sin `password_hash` propio) vs. autenticación propia en FastAPI (el informe asume `passwordHash`) |
| D-04 | Tipo de clave primaria | UUID (alineado con Supabase Auth) vs. entero (informe) |
| D-05 | Límite por defecto de rondas de corrección | Sin definir |
| D-06 | Caducidad de una reserva `Pre-reservada` sin pago | Sin definir |
| D-07 | Proveedor de correo transaccional | Sin definir |
| D-08 | Hosting de backend y frontend | Sin definir |
| D-09 | Moneda, impuestos y facturación electrónica | El informe menciona "comprobante fiscal"; alcance sin definir |
| D-10 | Sello/Mánager y Músico de sesión | ¿Roles del sistema o fuera de alcance v1? |
| D-11 | Políticas de cancelación y reembolso del anticipo | Sin definir |
| D-12 | Asignación de personal | El informe usa `idIngeniero` único en `reserva`; RF-07 exige varios roles por sesión |
| D-13 | Archivo y plan de Figma | URL del archivo maestro, plan y asiento (determinan límites de uso del MCP) |
| D-14 | Code Connect de Figma | Vincular componentes de Figma con el código; aporta precisión pero exige mantenimiento |

Cada decisión cerrada se registra como ADR en `docs/00-proyecto/decisiones/`.

---

## 13. Diseño visual (brief y Figma)

### 13.1 Principios
- Figma es la fuente de verdad visual; `docs/07-diseno/` es la fuente de verdad escrita. Ambos se referencian mutuamente.
- Ningún valor visual (color, tamaño, espaciado, radio, sombra) se escribe a mano en el código: todo proviene de tokens.
- Cada pantalla implementada referencia el enlace de su frame en Figma y el RF que cubre.
- Insumo de identidad existente: *Taller de marca Bugalú* (Alesin Branding Studio, 2026).

### 13.2 Contenido del brief (`docs/07-diseno/brief.md`)

| Sección | Contenido |
|---|---|
| Identidad | Logotipo y variantes, paleta, tipografías, iconografía, uso de fotografía |
| Tono visual | Atributos de marca y referencias de estilo |
| Audiencias | Artista/Cliente (experiencia pública), personal interno y Administrador (panel operativo) |
| Principios UX | Jerarquía, densidad por perfil, retroalimentación de estados, prevención de errores |
| Accesibilidad | WCAG 2.2 AA: contraste, foco visible, navegación por teclado, textos alternativos |
| Adaptabilidad | Puntos de quiebre y comportamiento por dispositivo (cabina: escritorio; cliente: móvil y escritorio) |
| Movimiento | Duraciones y curvas; respeto de `prefers-reduced-motion` |
| Inventario de pantallas | Lista por RF con prioridad y estado de diseño |

### 13.3 Organización del archivo Figma

| Página | Contenido |
|---|---|
| `00 Portada` | Brief resumido, estado y enlaces a `docs/07-diseno/` |
| `01 Fundamentos` | Variables: color, tipografía, espaciado, radios, sombras, puntos de quiebre |
| `02 Componentes` | Botones, campos, tarjetas, modales, tablas, estados de reserva |
| `03 Patrones` | Calendario de salas, reproductor con forma de onda, carga de archivos, resumen de pago |
| `04 Pantallas` | Un grupo por módulo (§3.3); frames nombrados `RF-xx / <pantalla> / <estado>` |
| `05 Prototipos` | Flujos navegables de CUS-04 y CUS-09/10 |

**Convenciones de nombres** (alineadas con §4.1):

| Figma | Código |
|---|---|
| Variable `color/fondo/primario` | `--color-fondo-primario` en `estilos/tokens.css` |
| Variable `espacio/4` | `--espacio-4` |
| Componente `bugalu-calendario` | Isla `<bugalu-calendario>` en `islas/` |
| Componente `boton/primario` | `componentes/Boton.astro` con variante `primario` |

### 13.4 Flujo diseño → código

```
1. usuario/leader → diseña o aprueba el frame en Figma y registra la spec en docs/07-diseno/pantallas/
2. leader         → crea la tarea con enlace al frame y RF asociado
3. dev_frontend   → obtiene contexto del frame vía Figma MCP (estructura, variables, captura)
                  → traduce a Astro + HTML/CSS/JS nativo usando tokens y componentes existentes
4. dev_audit      → compara captura de Playwright con la captura del frame; valida tokens y accesibilidad
5. leader         → integra y marca la pantalla como implementada en el inventario
```

**Regla de traducción:** el Figma MCP entrega por defecto código de referencia en React + Tailwind. Ese código es solo referencia estructural; nunca se copia. La implementación se hace en Astro, CSS con variables y Web Components según §3.2.

### 13.5 Sincronización de tokens
- Las variables de Figma son el origen; `estilos/tokens.css` es su reflejo.
- Todo cambio de variable en Figma genera una tarea de actualización de tokens antes de cualquier cambio de pantalla.
- `docs/07-diseno/tokens.md` mantiene la tabla de correspondencia.

---

## 14. Herramientas del agente: MCP y skills

### 14.1 Servidores MCP recomendados

| MCP | Uso | Instalación | Restricciones |
|---|---|---|---|
| Figma (oficial, remoto) | Leer frames, componentes, variables y capturas; generar reglas del sistema de diseño | Recomendado: `claude plugin install figma@claude-plugins-official` (incluye skills). Manual: `claude mcp add --transport http figma https://mcp.figma.com/mcp` y autenticar con `/mcp` | Solo lectura salvo aprobación del usuario |
| Supabase (oficial, remoto) | Inspeccionar esquema, ejecutar SQL, revisar logs, ejecutar asesores de seguridad y rendimiento, generar tipos | `https://mcp.supabase.com/mcp` limitado por `project_ref` y en modo solo lectura | Solo proyecto de desarrollo. Nunca producción. Los cambios de esquema van como migraciones versionadas en `supabase/`, no por MCP |
| Playwright (Microsoft) | Navegar la app local, capturas, pruebas E2E, verificación visual y de accesibilidad | `claude mcp add playwright -- npx @playwright/mcp@latest` | Solo entornos de desarrollo y pruebas |
| Context7 (opcional) | Documentación actualizada de Astro, FastAPI, Supabase y `uv` | `claude mcp add --transport http context7 https://mcp.context7.com/mcp` | Consulta; no reemplaza `docs/` |
| GitHub (opcional) | Issues, PR y revisiones, si el repositorio se aloja en GitHub | MCP oficial de GitHub o CLI `gh` | Sin merge automático; el merge lo autoriza `leader` |

**Configuración**
- Servidores compartidos en `.mcp.json` (alcance proyecto). Credenciales vía OAuth o variables de entorno; nunca en el repositorio.
- Verificación: `claude mcp list` y `/mcp` dentro de la sesión.
- Detalle operativo en `docs/06-operacion/herramientas-mcp.md`.

### 14.2 Matriz MCP por rol

| MCP | leader | dev_backend | dev_frontend | dev_audit |
|---|---|---|---|---|
| Figma | Lectura | — | Lectura | Lectura |
| Supabase | Lectura | Lectura (desarrollo) | — | Lectura (asesores) |
| Playwright | — | — | Sí | Sí |
| Context7 | Sí | Sí | Sí | Sí |
| GitHub | Sí | Lectura | Lectura | Lectura + comentarios |

### 14.3 Skills

**Externas**

| Skill | Origen | Uso | Rol |
|---|---|---|---|
| Skills de Figma (implementar diseño, reglas del sistema de diseño, Code Connect) | Plugin oficial de Figma | Flujo diseño → código y generación de reglas a partir del archivo | dev_frontend, leader |
| `frontend-design` | Plugin oficial de Anthropic | Criterio visual y de composición en interfaces | dev_frontend |

**Propias del proyecto** (`.claude/skills/`, en español, cada una remite a sus specs en `docs/`)

| Skill | Procedimiento | Rol |
|---|---|---|
| `crear-slice-backend` | Genera la estructura `dominio/aplicacion/infraestructura` de un caso de uso con pruebas base | dev_backend |
| `crear-migracion` | Crea migración SQL versionada, políticas RLS y actualiza `modelo-datos.md` | dev_backend |
| `crear-isla` | Genera isla `.astro` con Web Component, tokens y prueba | dev_frontend |
| `implementar-pantalla-figma` | Ejecuta §13.4 pasos 3–4 desde un enlace de frame | dev_frontend |
| `sincronizar-tokens` | Lee variables de Figma y actualiza `tokens.css` y `tokens.md` | dev_frontend |
| `auditar-entrega` | Aplica los criterios de §6.6 y emite el informe en formato estándar | dev_audit |
| `crear-tarea` | Redacta la tarea en formato §6.4 a partir de un RF | leader |

Regla: si un procedimiento se repite dos veces, se convierte en skill.

---

## 15. Hoja de ruta inicial

| Fase | Entregable | Rol |
|---|---|---|
| 0 | Segmentar este documento en `docs/`, crear `CLAUDE.md`, `.claude/agents/` y `.mcp.json` | leader |
| 1 | Cerrar decisiones D-01 a D-04 y D-13 (ADR); conectar Figma, Supabase y Playwright MCP | leader + usuario |
| 2 | Brief de diseño, fundamentos y componentes base en Figma | usuario + leader |
| 3 | Esqueleto backend (`uv`, FastAPI, `compartido/`, módulo de ejemplo) y Supabase local con migraciones base | dev_backend |
| 4 | Esqueleto frontend (Astro, layouts, tokens sincronizados desde Figma, cliente API) | dev_frontend |
| 5 | Skills propias del proyecto (§14.3) | leader |
| 6 | Auditoría del esqueleto contra §3, §4 y §13 | dev_audit |
| 7 | Implementación por RF en orden de dependencia: RF-01 → RF-03/04 → RF-05/06 → RF-07/08 → RF-09/10 → RF-11/12 → RF-13 → RF-02 → RF-14 | todos |