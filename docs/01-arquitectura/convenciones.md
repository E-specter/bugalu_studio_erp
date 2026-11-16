---
id: convenciones
titulo: Convenciones de código y control de versiones
estado: borrador
depende_de: []
---

# Convenciones

## Idioma y nomenclatura

- Todo identificador (código, base de datos, rutas, documentación) en español.
- Identificadores en ASCII: sin tildes ni `ñ` (`anio`, `contrasena`, `version_audio`). Contenido y datos en UTF-8, compatibles con caracteres internacionales.
- Nombres reservados por frameworks se conservan (`src/pages`, `public`, `main.py`).

| Ámbito | Formato | Ejemplo |
|---|---|---|
| Python: módulos, funciones, variables | `snake_case` | `registrar_reserva` |
| Python: clases | `PascalCase` | `RepositorioReservas` |
| JavaScript: variables, funciones | `camelCase` | `cargarDisponibilidad` |
| Web Components | `kebab-case` con prefijo | `<bugalu-calendario>` |
| PostgreSQL: tablas, columnas | `snake_case` singular | `sala_tecnica.tarifa_hora_grabacion` |
| PostgreSQL: claves foráneas | `id_<tabla>` | `reserva.id_sala` |
| Endpoints REST | `kebab-case` plural | `/api/v1/reservas` |
| Códigos de error de la API | `snake_case` | `perfil_no_encontrado` |
| Archivos de documentación | `kebab-case` | `reglas-negocio.md` |

## API

- Rutas en plural (`/api/v1/reservas`); excepción: recursos del propio usuario autenticado, en singular (`/api/v1/perfil`).
- Todo error, incluidos los propios de FastAPI (404, 405, 422), responde `{"error": {"codigo": "<snake_case>", "mensaje": "<texto para la persona>", "detalles": {…}}}`; `detalles` es opcional y solo lleva datos que la interfaz necesita (p. ej. las reservas afectadas de un 409, o `{"campo": "<nombre>"}` con el primer campo que falla en un 422). Montos y porcentajes viajan como texto decimal (`"25.00"`). Códigos comunes: `no_autenticado` (401), `sin_permiso` (403), `no_encontrado` (404), `metodo_no_permitido` (405), `conflicto` (409), `datos_invalidos` (422), `autenticacion_no_disponible` y `base_de_datos_no_disponible` (503).
- Fechas y horas: `timestamptz` en la base de datos; la API las envía en ISO 8601 con zona horaria; "día" y "semana" se interpretan en la hora de Lima (`America/Lima`); las semanas siguen ISO 8601 (`AAAA-Www`).

## Control de versiones

- Ramas: `feat/RF-04-registrar-reserva`, `fix/<id>-<descripcion>`, `docs/<tema>`.
- Commits: Conventional Commits en español (`feat(reservas): aplicar buffer técnico`).
- Toda rama referencia un RF o una tarea.

## Documentación

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
- Verificación: `python scripts/validar_docs.py docs`.
