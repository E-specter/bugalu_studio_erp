# Equipo multiagente de Bugalú ERP — Diseño

> Estado: borrador para aprobación · 2026-11-15 · Trabajo 1 de 2. Este trabajo cierra D-13 y D-14; el trabajo 2 cierra D-01..D-04.

## 1. Intención

Bugalú ERP se presenta como **piloto** ante el cliente: la UX/UI y la calidad del código (reutilizable, por componentes, legible, optimizado) pesan más que la velocidad. Al mismo tiempo, el usuario tiene un límite de uso menor al plan de 100 USD y lo comparte con otros proyectos. El equipo de agentes tiene que dar **eficacia un poco por encima de eficiencia**: gastar Opus donde se decide y se revisa, y recortar donde el trabajo se repite.

## 2. Objetivos, no-objetivos y anti-objetivos

**Objetivos**
- Seis roles con nombre, modelo, effort, tope de turnos y skills declaradas en el frontmatter.
- Extraer el estilo de Figma **una sola vez** a un brief técnico atómico y a skills de diseño. A partir de ahí, todo diseño nuevo se compone desde ese brief.
- Usar superpowers, claude-mem, ponytail y find-skills con un ciclo de bajo consumo de tokens.
- Documentación atómica: un concepto por archivo, ≤150 líneas, sin duplicación entre `docs/`, skills y agentes.

**No-objetivos**
- Implementar código de producción (empieza en las fases 3–4).
- Cerrar D-01..D-04 (trabajo 2).

**Anti-objetivos** (aunque "funcione", sería un fracaso)
- Que algún agente escriba en Figma.
- Precargar skills grandes (`figma-use`, `figma-generate-design`, `subagent-driven-development`) en cada ejecución.
- Usar Opus en todo.
- Un brief que sea una galería de pantallas en vez de un sistema (reglas, tokens, componentes, relaciones).
- Copiar contenido de `docs/` dentro de skills o agentes en lugar de enlazarlo.
- Pantallas nuevas con piezas que no estén en el catálogo.

## 3. Restricciones

- Arquitectura y convenciones vigentes en `docs/01-arquitectura/` (hexagonal, islas, español ASCII).
- Separación de alcances de escritura por rol ([docs/04-agentes/](../../04-agentes/leader.md)).
- Frontmatter de agentes (verificado en code.claude.com/docs/en/sub-agents.md, 2026-11-14):
  - `skills` inyecta el **contenido completo** de cada skill listada en cada ejecución. Sin `skills`, el agente igual puede invocarlas bajo demanda con la herramienta Skill.
  - `model` acepta `opus`, `sonnet`, `haiku`, `fable`, `inherit` o un ID. El parámetro `model` de cada llamada tiene prioridad.
  - `effort` acepta de `low` a `max`. `maxTurns` limita los turnos y, al llegar al límite, devuelve un resultado parcial.
  - `memory` activa Read, Write y Edit automáticamente: **no se usa**.
- Ponytail ya inyecta sus reglas en cada subagente mediante su hook `SubagentStart` cuando el modo está activo (`full`). **No se precarga.**
- Tamaños medidos de SKILL.md: `figma-use` 34.6K caracteres, `figma-generate-design` 39.6K, `subagent-driven-development` 32.6K, `executing-plans` 20.4K, `test-driven-development` 9.6K, `design-system` 5.8K, `ponytail-review` 5.1K, `figma-design-to-code` 4.1K, `accessibility-review` 4.4K, `verification-before-completion` 3.6K.

## 4. Enfoques considerados

| Enfoque | Trade-off | Resultado |
|---|---|---|
| **A. Por capa + diseñador + documentador** | Más archivos de agente, pero cada uno precarga solo lo suyo y respeta los alcances | **Elegido por el usuario** |
| B. Mínimo (dev generalista) | Menos mantenimiento; un agente carga dos stacks y rompe la separación de alcances | Descartado: menos eficacia |
| C. Un agente por módulo | Repite skills en muchos agentes y reparte la coherencia visual | Descartado |

## 5. Diseño decidido

### 5.1 Equipo

| Agente | Rol | Modelo · effort · maxTurns | Precarga (`skills`) | Bajo demanda |
|---|---|---|---|---|
| `leader` (sesión principal) | Orquesta, decide, planifica, escribe ADR y docs semánticos | Opus · high · — | — | `superpowers:brainstorming`, `superpowers:writing-plans`, `find-skills`, `claude-mem:mem-search` |
| `disenador-ui` | Fase 2: extracción única Figma → brief + skills de diseño. Después: especificaciones de pantalla y revisión visual contra el brief | Opus · high · 80 | `design:design-system`, `aplicar-brief` (cuando exista) | `figma:figma-design-to-code` (solo extracción), `impeccable`, `design:ux-copy`, `design:accessibility-review`, `design:design-critique` |
| `dev-frontend` | Componentes reutilizables, islas, páginas, `tokens.css` | Sonnet · medium · 40 | `aplicar-brief`, `superpowers:verification-before-completion` | `frontend-design`, skill externa de Astro (si se aprueba) |
| `dev-backend` | Slices hexagonales, API, migraciones, RLS | Sonnet · medium · 40 | `superpowers:test-driven-development`, `superpowers:verification-before-completion` | `superpowers:systematic-debugging`, skills externas de FastAPI/Supabase (si se aprueban) |
| `dev-audit` | Único revisor; dictamen APROBADO/RECHAZADO | Sonnet · high · 25 (Opus en compuertas, §5.3) | `ponytail:ponytail-review`, `superpowers:verification-before-completion` | `design:accessibility-review`, `security-review` |
| `documentador` | Mecánico: índice, `estado` del frontmatter, changelog, validador, enlaces | Haiku · low · 15 | — | — |

**Herramientas y alcances**
- `disenador-ui` escribe en `docs/07-diseno/` y `.claude/skills/{aplicar-brief,disenar-pantalla}/`. Solo usa las herramientas de **lectura** de Figma (`create_session`, `get_metadata`, `get_design_context`, `get_screenshot`, `get_variable_defs`, `search_design_system`, `get_libraries`, `download_assets`); todas las de escritura quedan prohibidas. No escribe código.
- `dev-frontend` y `dev-audit` pierden el acceso a Figma: comparan contra el brief, no contra frames.
- `documentador` escribe solo en `docs/` y `CHANGELOG.md`, sin MCP. No cambia el contenido semántico: si detecta un problema de contenido, lo reporta.
- `dev-audit` sigue sin Edit ni Write. `leader` guarda sus informes.

### 5.2 Flujo de diseño (sustituye a §13.4 de la spec v0.2)

1. **Extracción** (fase 2, una sola vez, `disenador-ui` en Opus): lee las páginas de Figma `references`, `brief`, `landing-page`, `blueprint-funcional`, `login` y `erp` del archivo `GxpFTDX6L0uFwg6xlulhXF`, y escribe el brief atómico (§5.5) con decisiones artísticas, reglas de composición, tokens, componentes (anatomía, variantes, estados, relaciones) y patrones. Registra también qué RF no tienen pantalla.
2. **Revisión del brief:** `dev-audit` en Opus revisa la coherencia interna del brief y el usuario lo aprueba. Desde ese momento `figma.md` queda `estado: implementado` y congelado como registro de origen.
3. **Skills de diseño** (`disenador-ui`): `aplicar-brief` (referencia corta y precargable, ≤3.000 caracteres, solo reglas y enlaces) y `disenar-pantalla` (procedimiento: RF → composición con componentes del catálogo → estados → copy → accesibilidad).
4. **Diseño nuevo:** cada pantalla es `docs/07-diseno/pantallas/RF-xx-<pantalla>.md`, compuesta solo con componentes del catálogo. Si falta un componente, primero se amplía el catálogo y después la pantalla.
5. **Implementación:** `dev-frontend` implementa. `dev-audit` compara la captura de Playwright con la spec y el brief. `disenador-ui` hace revisión visual solo en pantallas nuevas o componentes nuevos.

### 5.3 Ciclo superpowers de bajo consumo

- `leader` usa `brainstorming` solo cuando hay preguntas abiertas (decisiones, features nuevas), y `writing-plans` para un plan por fase o por RF.
- La ejecución **no** carga `subagent-driven-development` ni `executing-plans` (~13K tokens entre las dos). El ciclo queda escrito en `docs/05-protocolos/implementacion.md`: tarea → implementador (`dev-backend` o `dev-frontend`) → `dev-audit` como único revisor → `leader` integra. Los planes llevan en su cabecera un enlace a ese protocolo en lugar del sub-skill.
- **Compuertas Opus** (el `leader` pasa `model: "opus"` a `dev-audit`): cierre de cada fase, la revisión del brief, y toda tarea de los módulos `identidad` y `pagos` o que incluya una migración con RLS.
- La TDD y la verificación las precargan los implementadores; `systematic-debugging` se carga solo ante un fallo.

### 5.4 claude-mem, ponytail y find-skills

- **claude-mem** es la única memoria del proyecto.
  - Lista de trabajo (`work_state_write`): una lista por fase (`fase-2-diseno`) o por RF (`RF-04`), con un elemento por `TAREA-nnn`. **Solo `leader` escribe** en ella; los subagentes reportan en su ENTREGA.
  - `save_memory`: lecciones, trampas y preferencias. Nunca decisiones (van en ADR) ni hechos que el código ya registra.
  - `mem-search`: al retomar trabajo de otra sesión.
- **Ponytail** en `full`: se inyecta solo en los subagentes por hook. `dev-audit` precarga además `ponytail-review`.
- **find-skills:** `leader` lo ejecuta **una vez al inicio de cada fase**, solo para los huecos que la tabla `skills-por-fase` no cubre. Las candidatas se registran en `herramientas-mcp.md` y se instalan solo con aprobación del usuario.

**Skills que aún no existen.** `aplicar-brief` y `disenar-pantalla` las crea `disenador-ui` en la fase 2, y esa misma tarea las añade al frontmatter y a `equipo.md`. Hasta entonces no figuran en ninguno de los dos.

**`crear-componente`** es el procedimiento de `dev-frontend`: componente `.astro` con tokens, variantes, estados, prueba y enlace a su ficha del catálogo. Lo escribe `leader` en la fase 5, como el resto de skills propias, porque `.claude/` es su alcance. La única excepción son las dos skills de diseño, que escribe `disenador-ui`.

### 5.5 Documentación atómica

- `docs/04-agentes/equipo.md`: **fuente única** de la tabla §5.1 (modelo, effort, maxTurns, precarga, bajo demanda), escrita como tabla Markdown con una fila por agente y columnas fijas para que el validador pueda leerla.
- `docs/04-agentes/skills-por-fase.md`: fase × rol → skills.
- `docs/04-agentes/<rol>.md`: responsabilidad, alcance y reglas, sin repetir la tabla.
- `.claude/agents/<rol>.md`: frontmatter más ≤15 líneas que enlazan a su doc.
- El validador comprueba que el frontmatter de cada agente coincida con `equipo.md` (modelo, effort, maxTurns, skills) para evitar que se desincronicen. **Entra en este trabajo**: el parser de frontmatter de `scripts/validar_docs.py` se amplía para leer listas YAML y nombres `plugin:skill` (con `:`), recorre `.claude/agents/` y agrega sus pruebas.
- Estructura de `07-diseno/`:
  ```
  07-diseno/
  ├── brief.md            # índice + principios + decisiones artísticas (≤150 líneas)
  ├── figma.md            # origen de la extracción: archivo, mapa de páginas, fecha (congelado)
  ├── fundamentos/        # color, tipografia, espaciado-reticula, forma-elevacion, movimiento, iconografia-imagen
  ├── tokens.md           # tabla token → valor → uso; origen de tokens.css
  ├── componentes/        # README.md (catálogo) + <componente>.md: anatomía, variantes, estados, tokens, relaciones, a11y
  ├── patrones/           # composiciones recurrentes (cabecera, tarjeta de proyecto, línea de versiones…)
  └── pantallas/          # RF-xx-<pantalla>.md
  ```
- Las skills enlazan a estos archivos y nunca copian su contenido.
- Ruta de lectura por rol en `docs/README.md`, incluidos los dos roles nuevos.

### 5.6 Cambios en documentos existentes

- `04-agentes`: crear `disenador-ui.md`, `documentador.md`, `equipo.md` y `skills-por-fase.md`. Ajustar `dev-audit.md` (criterio 7: contra el brief y la spec de pantalla, no contra Figma), `dev-frontend.md` (sin Figma) y `leader.md` (delega lo mecánico a `documentador`).
- `05-protocolos/implementacion.md`: ciclo §5.3 y compuertas Opus.
- `06-operacion/herramientas-mcp.md`: Figma solo en la fase 2 y solo para `disenador-ui`; matriz MCP actualizada; skills propias actualizadas: salen `implementar-pantalla-figma` y `sincronizar-tokens` y entran `aplicar-brief`, `disenar-pantalla` y `crear-componente`.
- `07-diseno/*`: aplicar la estructura de §5.5. Sus contenidos se rellenan en la fase 2, no en este trabajo. En concreto:
  - `figma.md` se reescribe como registro de origen con las páginas reales (`references`, `brief`, `landing-page`, `blueprint-funcional`, `login`, `erp`); la organización planificada `00 Portada…05 Prototipos` se elimina.
  - `componentes.md` pasa a `componentes/README.md` (con `git mv`, conservando el contenido).
  - `brief.md` conserva sus encabezados como índice y cada sección apunta a su archivo de `fundamentos/`, en estado "Pendiente (fase 2)". `tokens.md` se conserva.
  - Las carpetas `fundamentos/` y `patrones/` se crean en la fase 2, cuando tengan contenido.
- **Toda referencia a Figma** fuera de `figma.md`, los ADR y `herramientas-mcp.md` se reescribe para apuntar al brief o a la spec de pantalla (localizarlas con grep en `docs/` y `.claude/`).
- `docs/README.md`: hoja de ruta (fase 2 = extracción por `disenador-ui`; fase 4 = tokens desde el brief) y rutas de lectura.
- `00-proyecto/decisiones`: ADR-001 cierra D-13 (Figma como fuente de extracción única; file key) y ADR-002 cierra D-14 (Code Connect descartado: no habrá Figma después de la extracción).
- `.claude/agents/`: los tres agentes existentes se actualizan y se crean `disenador-ui.md` y `documentador.md`.

### 5.7 Presupuesto de llamadas a Figma

Con plan Starter, o con asiento View o Collab, el MCP de Figma admite muy pocas llamadas al mes: la documentación oficial dice 6 en una página y 20 en otra. Con asiento Dev o Full en Professional u Organization, unas 200 al día. El límite depende del **equipo donde vive el archivo**, no de la cuenta.

**Situación (usuario, 2026-11-15):** la cuenta del usuario tiene plan Pro, pero el archivo está en un equipo sin suscripción (solo View), así que hoy aplica el límite de Starter. En esta sesión ya se gastaron unas 4 llamadas.

**Decisión:** antes de la fase 2, el usuario **mueve el archivo a su equipo Pro**, donde tiene asiento Full. Al moverlo se conserva el file key; si en vez de moverlo se duplica, hay que actualizar el key en el ADR-001. `disenador-ui` empieza la fase 2 con una llamada a `whoami` para confirmar el plan y el asiento. Esto queda registrado en el ADR-001 (D-13).

En cualquier caso, la extracción:
- reutiliza el volcado de estructura ya descargado el 2026-11-15 (todas las pantallas, antes del reordenamiento de páginas), que no gasta llamadas;
- se planifica llamada por llamada antes de empezar (qué nodo, qué herramienta, para qué dato) y registra el saldo en la lista de trabajo de claude-mem;
- si el saldo no alcanza, prioriza `get_variable_defs` y `get_design_context` de un marco representativo por tipo (guía de estilo, pantalla del portal, pantalla interna, móvil), y pide al usuario exportaciones manuales para el resto.

## 6. Lo que queda al constructor

- Confirmar con una ejecución de prueba que `skills` acepta nombres de plugin (`superpowers:test-driven-development`). Si no los acepta, la alternativa es la primera línea del cuerpo del agente: "Invoca la skill X antes de empezar".
- Confirmar que `tools` acepta nombres de herramientas MCP individuales para la allow-list de Figma de `disenador-ui`. Si no, usar `mcp__plugin_figma_figma__*` y bloquear en `disallowedTools` las herramientas de escritura.
- Quitar duplicados de MCP entre `.mcp.json` y los plugins de usuario (Figma, Playwright, Context7), con la regla de una sola entrada por servidor.
- Crear `CHANGELOG.md`, que exige el protocolo de integración.
- Los valores de `maxTurns` son iniciales; se ajustan con el uso real.
