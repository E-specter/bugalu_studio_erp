# Fase 0 — Segmentación documental y andamiaje multiagente · Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convertir `PROYECTO.md` en el árbol atómico `docs/` (§7.2) y crear `CLAUDE.md`, `.claude/agents/*.md` y `.mcp.json` para que los cuatro roles puedan operar.

**Architecture:** Sin código de producción. Un validador en Python (solo librería estándar) es la "prueba" de cada tarea: comprueba frontmatter, ≤150 líneas, enlaces relativos resolubles y que cada ID (RF/RN/D) viva en un único archivo. Cada tarea mueve una sección de `PROYECTO.md` a sus archivos y deja el validador en verde.

**Tech Stack:** Markdown + YAML frontmatter · Python 3.12 stdlib (`scripts/validar_docs.py`) · JSON (`.mcp.json`).

**Spec:** `PROYECTO.md` v0.2 (§6, §7, §14, §15 fase 0). Copia de referencia congelada en `docs/superpowers/specs/PROYECTO-v0.2.md` (Task 1).

## Global Constraints

- Identificadores y nombres de archivo en español, ASCII, `kebab-case` (§4.1). Contenido en UTF-8 (tildes permitidas en el texto).
- Un concepto por archivo, máximo ~150 líneas; se enlaza, no se copia (§7.1).
- Frontmatter obligatorio: `id`, `titulo`, `estado` (`borrador | aprobado | implementado`), `depende_de` (lista) (§7.1).
- Estado inicial de todo archivo segmentado: `borrador`.
- `.mcp.json` versionado **sin credenciales**; Supabase limitado por `project_ref` y en solo lectura (§14.1).
- `dev_audit` sin herramientas de edición (§6.2).
- Commits: Conventional Commits en español (§4.2).
- Al final, `PROYECTO.md` pasa a ser un puntero hacia `docs/README.md`; el original queda congelado en `docs/superpowers/specs/`.

## Review Focus

1. **Contenido perdido en la segmentación:** cada RN-xx, RF-xx y D-xx de `PROYECTO.md` debe aparecer en exactamente un archivo de `docs/` (Task 1, `test_ids_huerfanos`).
2. **Enlaces rotos tras mover secciones:** cada "ver §12, D-01" se convierte en un enlace relativo que debe existir (Task 1, `test_enlace_roto`).
3. **Duplicación:** una misma tabla de reglas copiada en dos archivos. El validador marca un ID definido en más de un archivo (Task 1, `test_id_duplicado`).
4. **Secretos en `.mcp.json`:** un token pegado por error (Task 6, `test_mcp_sin_secretos`).
5. **Archivos de más de 150 líneas** al copiar tablas grandes; se parten (Task 1, `test_limite_lineas`).

---

### Task 1: Validador de documentación y spec congelada

**Files:**
- Create: `scripts/validar_docs.py`, `docs/superpowers/specs/PROYECTO-v0.2.md` (copia literal de `PROYECTO.md`)
- Test: `scripts/test_validar_docs.py`

**Interfaces:**
- Produces: `python scripts/validar_docs.py docs [--ids-desde <archivo>]` → exit 0 si no hay errores; si los hay, una línea `<ruta>: <error>` por cada uno y exit 1. Función `validar(raiz: Path, fuente_ids: Path | None) -> list[str]`.

- [x] **Step 1: Write the failing tests** (`unittest`, cada uno arma su árbol en `tempfile.TemporaryDirectory`)
  - `test_frontmatter_faltante`: archivo sin `---` → error que contiene `"frontmatter"`.
  - `test_estado_invalido`: `estado: listo` → error que contiene `"estado"`.
  - `test_limite_lineas`: 151 líneas → error que contiene `"150"`.
  - `test_enlace_roto`: `[x](no-existe.md)` → error que contiene `"no-existe.md"`.
  - `test_id_duplicado`: dos archivos con `id: RF-01` → error que contiene `"RF-01"`.
  - `test_ids_huerfanos`: fuente con `| RN-01 |` y `| RN-02 |`, docs que solo definen `RN-01` → error que contiene `"RN-02"`.
  - `test_arbol_valido`: árbol correcto → `[]`.
- [x] **Step 2: Run** `python -m unittest scripts/test_validar_docs.py -v`. Expected: FAIL (`ModuleNotFoundError`).
- [x] **Step 3: Implement `validar()`** solo con stdlib (`re`, `pathlib`). Frontmatter parseado a mano (`clave: valor` y listas `[a, b]`), sin PyYAML. Un ID se considera "definido" si aparece en el `id:` del frontmatter o como primera celda de una fila de tabla (`^\| (RN|RF|D)-\d+ \|`). `docs/README.md` y `docs/superpowers/**` quedan exentos del frontmatter y del recuento de IDs.
- [x] **Step 4: Run** tests → PASS.
- [x] **Step 5: Commit** `feat(docs): validador de documentación atómica`.

### Task 2: `00-proyecto` y `01-arquitectura`

**Files:** Create `docs/00-proyecto/{vision,alcance,glosario}.md`, `docs/00-proyecto/decisiones/README.md` (tabla D-01…D-14 como abiertas + plantilla de ADR), `docs/01-arquitectura/{stack,backend-hexagonal,frontend-islas,modelo-datos,convenciones}.md`.

**Origen:** §1 → `vision`/`alcance` · §5.2 + §5.3 + términos de §5.1 → `glosario` · §12 → `decisiones/README.md` · §2 → `stack` · §3.1 + §3.3 + §3.4 → `backend-hexagonal` · §3.2 → `frontend-islas` · §11 → `modelo-datos` · §4 → `convenciones`.

- [x] **Step 1:** Crear los archivos con frontmatter (los que no son RF llevan `id` en kebab-case, p. ej. `id: arq-backend-hexagonal`), copiando el contenido literal y cambiando cada "ver §n" por un enlace relativo.
- [x] **Step 2: Run** `python scripts/validar_docs.py docs`. Expected: exit 0.
- [x] **Step 3: Commit** `docs(arquitectura): segmentar visión, stack, arquitectura y modelo de datos`.

### Task 3: `02-dominio` y `03-requerimientos`

**Files:** Create `docs/02-dominio/{actores-roles,reglas-negocio,estados-reserva}.md`, `docs/02-dominio/flujos/{registrar-reserva,versionado-feedback}.md`, `docs/03-requerimientos/RF-01.md` … `RF-14.md`.

**Origen:** §5.1 → `actores-roles` · §5.4 → `reglas-negocio` (única tabla RN) · §5.5 → `estados-reserva` (con la nota "transiciones inferidas, validar") · §5.6 + §10.1 → `flujos/` · §10 → un RF por archivo.

- [x] **Step 1:** Cada `RF-xx.md` lleva `id: RF-xx` y un `depende_de` con los RN que cita §10.1 (RF-04: `[RN-01, RN-02, RF-03]`, igual que en §7.1). Cuerpo: requerimiento, CUS, actores, módulo (§3.3) y enlaces a reglas y flujos, más `## Criterios de aceptación` con la línea `Pendiente (fase 7).`
- [x] **Step 2: Run** `python scripts/validar_docs.py docs --ids-desde docs/superpowers/specs/PROYECTO-v0.2.md`. Expected: exit 0, sin RN ni RF huérfanos (los D-xx ya quedaron en la Task 2).
- [x] **Step 3: Commit** `docs(dominio): segmentar reglas, estados, flujos y RF-01..RF-14`.

### Task 4: `04-agentes`, `05-protocolos`, `06-operacion`, `07-diseno`

**Files:** Create `docs/04-agentes/{leader,dev-backend,dev-frontend,dev-audit}.md`, `docs/05-protocolos/{cambios,implementacion,pruebas,integracion}.md`, `docs/06-operacion/{montaje-local,entornos,despliegue,herramientas-mcp}.md`, `docs/07-diseno/{brief,figma,tokens,componentes}.md`, `docs/07-diseno/pantallas/.gitkeep`.

**Origen:** fila del rol en §6.1 + §6.3 + §6.6 + fila de §14.2 → cada `04-agentes/<rol>.md` · §8 + §6.4/6.5 → `05-protocolos` (los formatos TAREA/ENTREGA viven **solo** en `implementacion.md`) · §9 → `entornos` · §14 → `herramientas-mcp` · §13.1–13.2 → `brief` (secciones de §13.2 como encabezados con `Pendiente (fase 2).`) · §13.3–13.4 → `figma` · §13.5 → `tokens` · tabla de nombres de §13.3 → `componentes`. `montaje-local` y `despliegue` quedan como esqueleto con `Pendiente (fases 3–4).` / `Pendiente (D-08).`

- [x] **Step 1:** Crear los archivos.
- [x] **Step 2: Run** `python scripts/validar_docs.py docs --ids-desde docs/superpowers/specs/PROYECTO-v0.2.md`. Expected: exit 0.
- [x] **Step 3: Commit** `docs(agentes): segmentar roles, protocolos, operación y diseño`.

### Task 5: Índice maestro, `CLAUDE.md` y `PROYECTO.md` como puntero

**Files:** Create `docs/README.md`, `CLAUDE.md`. Modify `PROYECTO.md` (se reemplaza por ≤5 líneas que apuntan a `docs/README.md` y a la copia congelada).

- [x] **Step 1:** `docs/README.md`: tabla con todos los archivos de `docs/` y una ruta de lectura por rol (`leader` → índice completo; `dev_backend` → `backend-hexagonal`, `modelo-datos`, `convenciones` + RF de la tarea; `dev_frontend` → `frontend-islas`, `convenciones`, `07-diseno/*` + RF; `dev_audit` → `05-protocolos/*` + `04-agentes/dev-audit`).
- [x] **Step 2:** `CLAUDE.md` de ≤20 líneas: la sesión principal es `leader`; "lee `docs/README.md` primero"; restricciones de §6.1 en viñetas; comando del validador.
- [x] **Step 3: Run** `python scripts/validar_docs.py docs --ids-desde docs/superpowers/specs/PROYECTO-v0.2.md`. Expected: exit 0. Además, todo enlace de `CLAUDE.md` existe.
- [x] **Step 4: Commit** `docs: índice maestro y CLAUDE.md; PROYECTO.md pasa a puntero`.

### Task 6: Subagentes y `.mcp.json`

**Files:** Create `.claude/agents/{dev-backend,dev-frontend,dev-audit}.md`, `.mcp.json`. Modify `scripts/validar_docs.py`, `scripts/test_validar_docs.py`.

**Interfaces:**
- Consumes: `docs/04-agentes/<rol>.md` (Task 4); cada subagente lo enlaza en vez de copiarlo.
- Produces: `validar_mcp(ruta: Path) -> list[str]`, que `main` invoca si existe `.mcp.json` en el directorio actual.

- [x] **Step 1: Write failing test** `test_mcp_sin_secretos`: un `.mcp.json` con `"Authorization": "Bearer abc"` → error; con `"${SUPABASE_TOKEN}"` → `[]`.
- [x] **Step 2: Implement `validar_mcp`**: rechaza cualquier valor de texto cuya clave coincida con `/token|key|secret|password|authorization/i` y no contenga `${`.
- [x] **Step 3:** Agentes (frontmatter `name`, `description`, `tools`): `dev-backend` y `dev-frontend` con lectura, edición y Bash más los MCP de su columna en §14.2; `dev-audit` con `tools: Read, Grep, Glob, Bash` más MCP de lectura, **sin** `Edit`/`Write`. El cuerpo enlaza `docs/04-agentes/<rol>.md` y repite solo el "alcance de escritura" de §6.1. `leader` no lleva archivo: es la sesión principal.
- [x] **Step 4:** `.mcp.json` con `figma` (http `https://mcp.figma.com/mcp`), `supabase` (http `https://mcp.supabase.com/mcp?project_ref=${SUPABASE_PROJECT_REF}&read_only=true`), `playwright` (`npx @playwright/mcp@latest`) y `context7` (http `https://mcp.context7.com/mcp`). GitHub se omite (opcional en §14.1; ya se usa `gh`).
- [x] **Step 5: Run** `python -m unittest scripts/test_validar_docs.py -v` y el validador. Expected: PASS / exit 0.
- [x] **Step 6: Commit** `chore(agentes): subagentes por rol y .mcp.json sin credenciales`.

---

## Fuera de alcance (fases siguientes)

- Cerrar D-01…D-04 y D-13 (fase 1, requiere al usuario).
- Skills propias de §14.3 (fase 5).
- Instalar skills externas. Candidatas verificadas el 2026-11-14 en skills.sh: `supabase/agent-skills@supabase-postgres-best-practices` (486K instalaciones), `supabase/agent-skills@supabase` (366K), `fastapi/fastapi@fastapi` (oficial, 15.5K) y `astrolicious/agent-skills@astro` (19.6K). Se instalan con aprobación del usuario y se registran en `06-operacion/herramientas-mcp.md`.
