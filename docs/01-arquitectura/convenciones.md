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
| PostgreSQL: tablas, columnas | `snake_case` singular | `sala_tecnica.tarifa_hora` |
| Endpoints REST | `kebab-case` plural | `/api/v1/reservas` |
| Archivos de documentación | `kebab-case` | `reglas-negocio.md` |

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
