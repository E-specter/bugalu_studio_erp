# Auditoría de cierre · Fase 1 (contratación, pagos y D-01..D-04)

> `dev-audit` con Opus · 2026-11-15 · Spec: `docs/superpowers/specs/2026-11-15-contratacion-y-decisiones-design.md` · Plan: `docs/superpowers/plans/2026-11-15-contratacion-y-decisiones.md`

## Ronda 1 — `acde522..0150059` · RECHAZADO

**Bloqueantes**
1. D-01/D-03/D-04 seguían abiertas en RF-01, RF-09, RF-12 y `flujos/versionado-feedback.md`.
2. `alcance.md` sin asesoría ni RF-15, y moneda como pendiente.

**Elevadas a importantes por `leader`** (efecto en quien lee o implementa)
- RN-13 exigía un servicio previo `Confirmada` literal: excluía a quien ya tenía la grabación `Finalizada` o la asesoría `Realizada`.
- `estados-reserva.md` dejaba cancelar al cliente; la spec (§7) solo menciona al Administrador.
- RF-12 "tras la liquidación" era ambiguo: la liquidación ahora incluye la cuota `al_terminar`.

Cumplía: Review Focus 1–5, cobertura completa de la spec, plantilla de ADR, nombres consistentes. Validador `docs OK`, unittest 17/17.

## Ronda 2 — `e8c8d8f` · APROBADO

Los dos bloqueantes y los tres importantes están resueltos. Validador `docs OK`, unittest 17/17, `git status` limpio antes y después.

## No bloqueantes diferidas

- ADR-003 atribuye el almacenamiento solo al módulo `entregables`; el bucket `comprobantes` lo usa `pagos`.
- Las filas D-06 y D-11 del registro no mencionan la asesoría `Pendiente de pago` ni los pagos distintos del anticipo.
- `CHANGELOG.md` dice "tramos de 30 min" en vez de "múltiplos de 30 min".
- `convenciones.md:22` usa como ejemplo `sala_tecnica.tarifa_hora`, que ya no existe.
- `backend-hexagonal.md:73` cita `FrmCalendarioSalas` (nombre histórico del informe).
- RN-06 se reescribió aunque la spec decía "Igual" (necesario por la nueva definición de liquidación).
- La spec congelada (§6.1) pide `Confirmada` literal en RN-13; el doc vivo la amplía a "`Confirmada` o posterior".
