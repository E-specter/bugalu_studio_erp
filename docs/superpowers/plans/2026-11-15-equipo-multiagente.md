# Equipo multiagente · Plan de implementación

> **Ejecución:** ciclo de bajo consumo del diseño (spec §5.3). `leader` implementa las tareas 1–4 porque caen en su alcance (`docs/`, `.claude/`, `CLAUDE.md`, `.mcp.json`, `scripts/`). La tarea 5 es la compuerta de cierre: `dev-audit` con `model: "opus"`. Los pasos usan casillas (`- [ ]`).

**Goal:** Dejar operativo el equipo de seis roles (modelo, effort, maxTurns y skills en el frontmatter), con su documentación atómica, el validador que impide la desincronización y D-13/D-14 cerradas.

**Architecture:** `docs/04-agentes/equipo.md` es la fuente única de la configuración; `.claude/agents/*.md` la refleja y `scripts/validar_docs.py` comprueba que coincidan. El diseño visual pasa a depender del brief (`docs/07-diseno/`) en lugar de Figma.

**Tech Stack:** Markdown + frontmatter · Python 3 stdlib · subagentes de Claude Code · JSON (`.mcp.json`).

**Spec:** `docs/superpowers/specs/2026-11-15-equipo-multiagente-design.md` (aprobada el 2026-11-15).

## Global Constraints

- Archivos de `docs/`: frontmatter `id/titulo/estado/depende_de`, ≤150 líneas, nombres en ASCII `kebab-case`, se enlaza en vez de copiar.
- Cuerpo de cada `.claude/agents/<rol>.md` en ≤15 líneas, con enlace a `docs/04-agentes/<rol>.md`.
- Ningún agente lleva el campo `memory`, y ninguno precarga `ponytail:ponytail` (lo inyecta el hook `SubagentStart`).
- `aplicar-brief` y `disenar-pantalla` **no** se declaran todavía (se agregan en la fase 2).
- Ninguna herramienta de escritura de Figma queda disponible para ningún subagente.
- Solo `leader` escribe en claude-mem: todo subagente bloquea `work_state_write` y `save_memory`.
- Commits en Conventional Commits en español, con las líneas de atribución de la sesión.

## Review Focus

1. **Nombres `plugin:skill` en `skills` que no cargan y fallan en silencio:** el agente arranca sin TDD ni verificación. Se cubre en Task 2, paso 4 (ejecución de prueba).
2. **Allow-list de Figma por herramienta que no surte efecto:** `disenador-ui` se queda sin Figma o recibe las de escritura. Task 2, paso 4.
3. **Enlaces rotos tras mover `componentes.md`:** Task 4, validador en verde.
4. **Desincronización por formato** (`maxTurns: 40` frente a `"40"`, `Sonnet` frente a `sonnet`, el orden de las skills): el validador normaliza mayúsculas, comillas y orden. Task 1, `test_agente_valores_normalizados`.
5. **`dev-audit` modifica el repo por Bash:** tras la auditoría, `git status --short` tiene que salir igual que antes. Task 5, paso 3.

---

### Task 1: Validador de consistencia de agentes

**Files:** Modify `scripts/validar_docs.py`, `scripts/test_validar_docs.py`.

**Interfaces:**
- Produces:
  - `leer_frontmatter(texto: str) -> dict | None` ahora devuelve `list[str]` para las claves cuyo valor es una lista YAML (`clave:` seguida de líneas `  - item`) o en línea (`[a, b]`). El resto sigue siendo `str`.
  - `validar_agentes(dir_agentes: Path, equipo: Path) -> list[str]`, que `main()` invoca cuando existen `.claude/agents/` y `docs/04-agentes/equipo.md`.
- Formato de `equipo.md`, sección `## Subagentes`: la tabla `| Agente | Modelo | Effort | maxTurns | Precarga | Bajo demanda | Rol |`. Las columnas 1–5 se leen por posición. "Precarga" contiene nombres entre backticks separados por coma, o `—`. El nombre del agente va entre backticks.

- [ ] **Step 1: Write failing tests** (en la misma clase y con el mismo estilo que los existentes)
  - `test_frontmatter_lista_yaml`: `skills:\n  - superpowers:test-driven-development\n  - design:design-system` → `["superpowers:test-driven-development", "design:design-system"]`.
  - `test_agente_coincide`: fila y frontmatter iguales → `[]`.
  - `test_agente_modelo_distinto`: fila `opus`, frontmatter `sonnet` → error que contiene `"model"` y el nombre del agente.
  - `test_agente_skills_distintas`: una skill de más en el frontmatter → error que contiene `"skills"`.
  - `test_agente_sin_fila` y `test_fila_sin_agente` → errores que contienen el nombre del agente.
  - `test_agente_valores_normalizados`: `Sonnet`, `"40"` y skills en otro orden → `[]`.
- [ ] **Step 2: Run** `python -m unittest scripts/test_validar_docs.py -v`. Expected: FAIL (`ImportError` de `validar_agentes`).
- [ ] **Step 3: Implement.** La fila `leader` se ignora porque no tiene archivo. Precarga `—` equivale a `[]`. La comparación se hace en minúsculas, sin comillas, y las skills como conjunto.
- [ ] **Step 4: Run** tests → PASS (15 pruebas).
- [ ] **Step 5: Commit** `feat(docs): validar que los agentes coincidan con equipo.md`.

### Task 2: Equipo — documentación y agentes

**Files:**
- Create: `docs/04-agentes/{equipo,skills-por-fase,disenador-ui,documentador}.md`, `.claude/agents/{disenador-ui,documentador}.md`
- Modify: `docs/04-agentes/{leader,dev-backend,dev-frontend,dev-audit}.md`, `.claude/agents/{dev-backend,dev-frontend,dev-audit}.md`

**Interfaces:**
- Consumes: el formato de `equipo.md` y `validar_agentes` de la Task 1.

- [ ] **Step 1: `equipo.md`.** La tabla de spec §5.1 con el formato de la Task 1. Bajo `## Sesión principal` va `leader`, que tiene fila pero no archivo. Debajo, las compuertas Opus de spec §5.3 y la regla de claude-mem de §5.4.
- [ ] **Step 2: Frontmatter de los cinco agentes** (valores exactos):

  | Agente | model | effort | maxTurns | skills | Herramientas |
  |---|---|---|---|---|---|
  | `disenador-ui` | opus | high | 80 | `design:design-system` | `tools`: Read, Grep, Glob, Write, Edit, Bash, Skill y `mcp__plugin_figma_figma__{create_session,get_metadata,get_design_context,get_screenshot,get_variable_defs,search_design_system,get_libraries,download_assets,whoami}` |
  | `dev-frontend` | sonnet | medium | 40 | `superpowers:verification-before-completion` | `disallowedTools`: Figma*, Supabase*, claude-mem† |
  | `dev-backend` | sonnet | medium | 40 | `superpowers:test-driven-development`, `superpowers:verification-before-completion` | `disallowedTools`: Figma*, Playwright*, `mcp__claude_ai_Supabase__*`, claude-mem† |
  | `dev-audit` | sonnet | high | 25 | `ponytail:ponytail-review`, `superpowers:verification-before-completion` | `disallowedTools`: Edit, Write, NotebookEdit, Figma*, `mcp__claude_ai_Supabase__*`, claude-mem† |
  | `documentador` | haiku | low | 15 | — | `disallowedTools`: `mcp__*` |

  Figma\* = `mcp__plugin_figma_figma__*`, `mcp__figma__*` · Supabase\* = `mcp__supabase__*`, `mcp__claude_ai_Supabase__*` · Playwright\* = `mcp__playwright__*`, `mcp__plugin_playwright_playwright__*` · claude-mem† = `mcp__plugin_claude-mem_mcp-search__work_state_write`, `mcp__plugin_claude-mem_mcp-search__save_memory`.

  Cuerpo de cada agente: el rol en una línea, su alcance de escritura y un enlace a su doc. `disenador-ui` lleva además: "no escribas código; en la fase 2, empieza con `whoami` y planifica las llamadas (spec §5.7)".
- [ ] **Step 3: Docs de rol.**
  - `disenador-ui.md`: alcance y flujo (spec §5.2) y presupuesto de Figma (§5.7).
  - `documentador.md`: alcance mecánico; si encuentra un problema de contenido, lo reporta.
  - `skills-por-fase.md`: fases 1–7 por rol, con lo que precarga y lo que carga bajo demanda (spec §5.1 y §5.4). Se agrega la regla de find-skills.
  - Ajustes: `dev-audit.md` (criterio 7 → brief y spec de pantalla; compuertas Opus), `dev-frontend.md` (sin Figma; implementa desde el brief y la spec de pantalla), `leader.md` (delega lo mecánico en `documentador`; único que escribe en claude-mem) y las tablas MCP de los cuatro.
- [ ] **Step 4: Ejecuciones de prueba** (con `model: "haiku"` para abaratar).
  - `dev-audit`: "Enumera solo los nombres de las skills cuyo contenido tienes precargado." Expected: aparecen `ponytail-review` y `verification-before-completion`.
  - `disenador-ui`: "Enumera solo tus herramientas cuyo nombre empiece por `mcp__plugin_figma_figma__`." Expected: las 9 de la allow-list y ninguna de escritura.
  - Si alguna falla, se aplica la alternativa de spec §6 y se anota en `equipo.md`.
- [ ] **Step 5: Run** `python scripts/validar_docs.py docs --ids-desde docs/superpowers/specs/PROYECTO-v0.2.md`. Expected: `docs OK`.
- [ ] **Step 6: Commit** `feat(agentes): equipo de seis roles con modelos, topes y skills precargadas`.

### Task 3: Protocolos, herramientas y punto de entrada

**Files:** Modify `docs/05-protocolos/implementacion.md`, `docs/06-operacion/herramientas-mcp.md`, `.mcp.json`, `CLAUDE.md`, y todo archivo de `docs/` o `.claude/` que mencione Figma (excepto `07-diseno/`, `00-proyecto/decisiones/` y `superpowers/`). Create `CHANGELOG.md`.

- [ ] **Step 1: `implementacion.md`.** Se agrega la sección `## Ciclo de bajo consumo`, con el contenido de spec §5.3: no cargar `subagent-driven-development` ni `executing-plans`, `dev-audit` como único revisor, compuertas Opus, y en la cabecera de cada plan un enlace a esta sección.
- [ ] **Step 2: `herramientas-mcp.md`.**
  - Figma: solo `disenador-ui`, solo lectura y solo en la fase 2.
  - La matriz MCP pasa a seis roles.
  - Skills propias: salen `implementar-pantalla-figma` y `sincronizar-tokens`; entran `aplicar-brief`, `disenar-pantalla` y `crear-componente` (spec §5.1).
  - Nota de servidores: una entrada por servidor.
- [ ] **Step 3: `.mcp.json`.** Solo queda `supabase`, apuntando al **stack local** del CLI: `{"type": "http", "url": "http://localhost:54321/mcp"}`. Supabase no tiene suscripción y todo es local (decisión del usuario, 2026-11-15); el MCP local ofrece menos herramientas y no usa OAuth. Se elimina `SUPABASE_PROJECT_REF`. Figma, Playwright y Context7 vienen de los plugins de usuario. En `herramientas-mcp.md` y `06-operacion/entornos.md` se documenta: requiere Docker Desktop en marcha y `supabase start`; sigue vigente la regla de "solo migraciones, nunca DDL por MCP", porque el modo de solo lectura no está verificado en el MCP local.
- [ ] **Step 4: Referencias a Figma.** Correr `grep -rln -i figma docs .claude CLAUDE.md`. Cada aparición fuera de las excepciones pasa a apuntar al brief o a la spec de pantalla.
- [ ] **Step 5: `CLAUDE.md`** (≤25 líneas): los seis roles en una línea cada uno, con enlace a `equipo.md`; el ciclo de bajo consumo; "solo leader escribe en claude-mem"; ponytail `full` por hook. Crear `CHANGELOG.md` con una entrada `## 2026-11-15` (fase 0 + equipo).
- [ ] **Step 6: Run** el validador. Expected: `docs OK`. Además, `claude mcp list` muestra un único `supabase` de proyecto, con URL `localhost:54321` (puede aparecer desconectado si el stack local no está arrancado).
- [ ] **Step 7: Commit** `docs(protocolos): ciclo de bajo consumo, herramientas por rol y punto de entrada`.

### Task 4: Diseño basado en brief y decisiones D-13/D-14

**Files:**
- Create: `docs/00-proyecto/decisiones/{ADR-001-figma-fuente-extraccion,ADR-002-code-connect-descartado}.md`
- Move: `docs/07-diseno/componentes.md` → `docs/07-diseno/componentes/README.md`
- Modify: `docs/07-diseno/{figma,brief}.md`, `docs/00-proyecto/decisiones/README.md`, `docs/README.md`

- [ ] **Step 1: ADR-001** (`depende_de: [D-13]`, con la plantilla de `decisiones/README.md`):
  - Figma se usa como fuente de extracción única.
  - Archivo `GxpFTDX6L0uFwg6xlulhXF`.
  - Las páginas de §5.2.
  - Plan y asiento: el usuario reconectó Figma el 2026-11-15 con su cuenta Pro de asiento Full y es dueño del proyecto (límite ~200 llamadas/día). Se confirma con una llamada a `whoami` antes de escribir el ADR y se anota lo que devuelva.
- [ ] **Step 1b: ADR-002** (`depende_de: [D-14]`): Code Connect se descarta porque Figma no se usa después de la extracción.
- [ ] **Step 1c: Filas D-13 y D-14** de `decisiones/README.md`: columna ADR → enlace.
- [ ] **Step 2: `git mv`** de `componentes.md`. Reescribir `figma.md` como registro de origen: archivo, mapa real de páginas, volcado en `.claude/cache/` y estado `borrador` hasta que termine la extracción. `brief.md` queda como índice cuyas secciones apuntan a `fundamentos/<tema>.md` "(fase 2)", en texto plano, porque esos archivos todavía no existen.
- [ ] **Step 3: `docs/README.md`.**
  - Hoja de ruta: la fase 1 cubre solo D-01..D-04 (D-13/D-14 cerradas). La fase 2 es la extracción por `disenador-ui`. La fase 4 toma los tokens del brief.
  - Rutas de lectura de `disenador-ui` y `documentador`.
  - Enlaces a `equipo.md` y `skills-por-fase.md`.
- [ ] **Step 4: Run** el validador con `--ids-desde`. Expected: `docs OK`, sin enlaces rotos a `componentes.md`.
- [ ] **Step 5: Commit** `docs(diseno): brief como fuente; ADR-001 y ADR-002 cierran D-13 y D-14`.

### Task 5: Compuerta de cierre (dev-audit en Opus)

- [ ] **Step 1:** Anotar `git status --short` y el hash de `HEAD`.
- [ ] **Step 2:** Lanzar `dev-audit` con `model: "opus"`. Prompt: auditar el rango `5afb269..HEAD` contra la spec y este plan, con los criterios de `docs/04-agentes/dev-audit.md`, y devolver el informe.
- [ ] **Step 3:** Expected: el informe dice **APROBADO**, y `git status --short` y `HEAD` no cambiaron. Si dice RECHAZADO, se corrige (lo hace `leader`, porque es su alcance) y se vuelve a auditar solo lo que se corrigió.
- [ ] **Step 4:** Guardar el informe en `docs/superpowers/auditorias/2026-11-15-equipo.md`, marcar la spec como `Estado: aprobado e implementado`, cerrar la lista `trabajo-1-equipo-multiagente` de claude-mem y abrir `trabajo-2-decisiones` (D-01..D-04).
- [ ] **Step 5: Commit** `docs: auditoría de cierre del equipo multiagente`.
