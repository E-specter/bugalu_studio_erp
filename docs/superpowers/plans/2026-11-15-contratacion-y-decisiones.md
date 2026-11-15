# Contratación, pagos y D-01..D-04 · Plan de implementación

> **Ejecución:** ciclo de bajo consumo ([implementacion](../../05-protocolos/implementacion.md#ciclo-de-bajo-consumo)). `leader` implementa las tareas 1–3 (contenido semántico de `docs/`, su alcance); `documentador` la tarea 4 (mecánica); la tarea 5 es la compuerta de cierre de fase: `dev-audit` con `model: "opus"`. Los pasos usan casillas (`- [ ]`).

**Goal:** Cerrar D-01..D-04 con ADR-003..006 y reescribir el dominio de contratación (franjas, reserva de sala, asesoría, cuotas, validación manual de pagos) en reglas, estados, flujos, modelo y RF.

**Architecture:** Solo documentación. Las reglas viven en `reglas-negocio.md` (única definición de cada RN); RF, flujos y modelo enlazan a ellas. Infraestructura: Supabase de punta a punta.

**Tech Stack:** Markdown + frontmatter · `scripts/validar_docs.py`.

**Spec:** `docs/superpowers/specs/2026-11-15-contratacion-y-decisiones-design.md` (aprobada el 2026-11-15, commit `339e78f`). El contenido (tablas de ADR, RN-01..RN-16, estados, tablas del modelo, cambios de RF, decisiones de la §7) se copia de ahí; este plan no lo repite.

## Global Constraints

- Archivos de `docs/`: frontmatter `id/titulo/estado/depende_de`, ≤150 líneas, nombres ASCII `kebab-case`; se enlaza en vez de copiar.
- Cada `RN-nn` / `RF-nn` / `D-nn` se define (fila `| RN-nn |` o frontmatter `id`) en **un solo** archivo.
- ADR con la plantilla de [decisiones](../../00-proyecto/decisiones/README.md#plantilla-de-adr), `estado: aprobado`.
- Moneda PEN. Métodos de pago: `transferencia`, `yape`, `plin`, `tarjeta`. Tramos en múltiplos de 30 min (mínimo 30 min) para sala y asesoría.
- Verificación de cada tarea: `python scripts/validar_docs.py docs --ids-desde docs/superpowers/specs/PROYECTO-v0.2.md` → `OK` (sin errores) y `python -m unittest scripts/test_validar_docs.py` → `OK`.
- Commits Conventional Commits en español con las líneas de atribución de la sesión.

## Review Focus

1. **Restos del flujo viejo** ("Pasarela de Pagos" como actor integrado, "50% restante tras aprobación" como liquidación del proyecto, calendario libre de salas): el lector creería que siguen vigentes. Task 3, paso 4 (grep).
2. **Un RN definido dos veces** (p. ej. tabla `| RN-12 |` copiada en un flujo): el validador lo marca; Task 2, paso 4.
3. **Anclas rotas** al reescribir encabezados (`#módulos-del-backend`, `#brecha-detectada`): Task 3, paso 4 (validador).
4. **Incoherencia de cifras entre archivos** (30 min, múltiplos de 30, 50/50, ensayo con servicio previo `Confirmada`): Task 3, paso 4 (grep cruzado).
5. **D-06/D-11 presentadas como cerradas**: deben seguir abiertas, con la cancelación manual del Administrador como regla v1. Task 2, paso 4.

---

### Task 1: ADR-003..006 y decisiones de infraestructura

**Files:**
- Create: `docs/00-proyecto/decisiones/ADR-003-almacenamiento-supabase-storage.md`, `ADR-004-pagos-validacion-manual.md`, `ADR-005-supabase-auth.md`, `ADR-006-claves-uuid.md`
- Modify: `docs/00-proyecto/decisiones/README.md` (filas D-01..D-04 → **Cerrada** + enlace; D-09 → contexto "Moneda PEN decidida (spec 2026-11-15); impuestos y facturación abiertos")
- Modify: `docs/01-arquitectura/stack.md` (fila almacenamiento → Supabase Storage [ADR-003]; añadir filas Autenticación [ADR-005] y Pagos [ADR-004])
- Modify: `docs/02-dominio/actores-roles.md` (+ Visitante, + Profesional artístico; "Pasarela de Pagos / Banco" → "Banco / billetera (sin integración, ADR-004)"; Almacenamiento Cloud = Supabase Storage)

**Interfaces:**
- Produces: rutas de los 4 ADR (enlazadas por tareas 2–3); actores `Visitante` y `Profesional artístico`.

- [ ] **Step 1:** Escribir los 4 ADR desde la tabla §5 y los enfoques §4 de la spec (Contexto · Opciones consideradas · Decisión (usuario, 2026-11-15) · Consecuencias). `depende_de: [D-01]` … `[D-04]`.
- [ ] **Step 2:** Actualizar `decisiones/README.md`, `stack.md` y `actores-roles.md` como indica **Files**.
- [ ] **Step 3:** Validador → `OK`.
- [ ] **Step 4:** Commit `docs(decisiones): ADR-003..006 cierran D-01..D-04`.

### Task 2: Dominio — reglas, estados, glosario y flujos

**Files:**
- Modify: `docs/02-dominio/reglas-negocio.md` (RN-01..RN-16 de la spec §6.1; nota final: D-06 y D-11 abiertas, en v1 el Administrador cancela a mano)
- Modify: `docs/02-dominio/estados-reserva.md` (renombrar título a "Estados de reserva, asesoría y pago"; mantener `id: estados-reserva`; + diagramas/tablas de asesoría y comprobante de §6.2; cancelación manual v1)
- Modify: `docs/00-proyecto/glosario.md` (redefinir Anticipo y Liquidación; + Franja, Tramo, Cuota, Asesoría, Simulación de precio, Cotización a medida, Visitante)
- Modify: `docs/02-dominio/flujos/registrar-reserva.md` (franja → tramo → cuenta → `Pre-reservada` → captura → validación → `Confirmada` → saldo al terminar)
- Modify: `docs/02-dominio/flujos/ciclo-servicio.md` (diagrama §6 de la spec)
- Create: `docs/02-dominio/flujos/agendar-asesoria.md` (`id: flujo-agendar-asesoria`, `depende_de: [RF-15, RN-14, RN-16]`)

**Interfaces:**
- Consumes: actores de Task 1.
- Produces: IDs RN-12..RN-16 (usados por Task 3); ruta `flujos/agendar-asesoria.md`.

- [ ] **Step 1:** Reescribir `reglas-negocio.md` y `estados-reserva.md`. Las decisiones de la spec §7 que son reglas entran aquí: generación de cuotas (sin cotización: `al_reservar` + `al_terminar`; con cotización: manda su plan; asesoría: `al_reservar`) como parte de RN-13/RN-14/RN-16, y la cancelación manual v1 en la nota. Las de cuenta obligatoria y Visitante van a los flujos (paso 3); la de Profesional artístico ya está en `actores-roles` (Task 1).
- [ ] **Step 2:** Actualizar `glosario.md`.
- [ ] **Step 3:** Reescribir los dos flujos y crear `agendar-asesoria.md`. Los flujos enlazan a las RN; no copian filas `| RN-nn |`.
- [ ] **Step 4:** Validador → `OK`; `grep -rn "^| RN-" docs --include=*.md | grep -v reglas-negocio.md` → vacío; `grep -n "D-06\|D-11" docs/02-dominio/reglas-negocio.md docs/02-dominio/estados-reserva.md` → ambas siguen citadas como abiertas.
- [ ] **Step 5:** Commit `docs(dominio): flujo real de contratación, asesoría y pagos validados`.

### Task 3: Requerimientos, modelo, arquitectura y diseño

**Files:**
- Modify: `docs/03-requerimientos/RF-02.md`, `RF-03.md`, `RF-04.md`, `RF-05.md`, `RF-11.md` (título, requerimiento, actores, reglas, flujo y decisiones según spec §6.4; quitar D-02 de "Decisiones abiertas" y enlazar ADR-004)
- Create: `docs/03-requerimientos/RF-15.md` (`id: RF-15`, "Agendar asesoría artística", módulo `asesorias`, `depende_de: [RN-14, RN-16, RF-01, RF-05]`)
- Modify: `docs/01-arquitectura/modelo-datos.md` (tablas de §6.3; quitar la nota "pendiente D-04"; `depende_de: [ADR-006, D-12]`)
- Modify: `docs/01-arquitectura/backend-hexagonal.md` (tabla de módulos: + `asesorias` → RF-15; puerto `PasarelaPagos` con adaptador manual en `pagos`)
- Modify: `docs/01-arquitectura/frontend-islas.md` (islas: "Franjas de sala y simulación" RF-02/03/04; "Registro de pago con captura" RF-05/11; "Agenda de asesoría" RF-15; "Validación de pagos (Administrador)" RF-05)
- Modify: `docs/07-diseno/figma.md` (sección `## Brecha detectada`, mismo encabezado: la rama de asesoría de Figma se conserva; pantallas faltantes de spec §6.5)
- Modify: `docs/README.md` (fila RF-15 en la tabla; títulos nuevos de RF-02..05/11; orden de implementación: `RF-01 → RF-03/04 → RF-05/06 → RF-15 → RF-02 → RF-07/08 → RF-09/10 → RF-11/12 → RF-13 → RF-14`, porque la simulación y la cotización a medida ya forman parte de la contratación)

**Interfaces:**
- Consumes: ADR de Task 1; RN-12..RN-16 y flujos de Task 2.

- [ ] **Step 1:** Reescribir RF-02..05 y RF-11; crear RF-15.
- [ ] **Step 2:** Actualizar `modelo-datos.md`, `backend-hexagonal.md`, `frontend-islas.md`.
- [ ] **Step 3:** Actualizar `figma.md` y `docs/README.md`.
- [ ] **Step 4:** Verificar:
  - Validador → `OK`; unittest → `OK`.
  - `grep -rn "Pasarela de Pagos" docs --include=*.md | grep -v superpowers` → solo menciones históricas en ADR-004.
  - `grep -rn "50% restante" docs --include=*.md | grep -v superpowers` → vacío o solo en contexto de sesión/ensayo/posproducción coherente con RN-05/RN-13.
  - `grep -rln "30 min" docs/02-dominio docs/03-requerimientos` → cada mención coincide con RN-02/12/14 (buffer y múltiplos).
- [ ] **Step 5:** Commit `docs(requerimientos): RF de contratación reescritos y RF-15 asesoría`.

### Task 4: Cierre mecánico (`documentador`)

**Files:** Modify `CHANGELOG.md` (entrada 2026-11-15 "Contratación y D-01..D-04"), `docs/README.md` (hoja de ruta: fase 1 → `Hecho`).

- [ ] **Step 1:** Lanzar `documentador` con la lista de commits de las tareas 1–3 y estas dos ediciones.
- [ ] **Step 2:** Validador → `OK`; commit `docs: changelog y hoja de ruta de la fase 1`.

### Task 5: Compuerta de cierre de fase (`dev-audit`, Opus)

- [ ] **Step 1:** Anotar `git status --short` (debe estar limpio).
- [ ] **Step 2:** Lanzar `dev-audit` con `model: "opus"`: auditar los commits de las tareas 1–4 contra la spec (cobertura de §5, §6.1–6.5, §7), las convenciones y los cinco puntos de Review Focus. Dictamen APROBADO/RECHAZADO.
- [ ] **Step 3:** `git status --short` igual que en el paso 1. Si RECHAZADO: corregir, nuevo commit `fix(docs): …`, repetir paso 2.
- [ ] **Step 4:** Guardar el informe en `docs/superpowers/auditorias/2026-11-15-contratacion.md`; commit. Cerrar la lista `trabajo-2-decisiones` en claude-mem.
