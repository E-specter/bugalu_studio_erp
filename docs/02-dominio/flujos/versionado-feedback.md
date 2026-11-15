---
id: flujo-versionado-feedback
titulo: CUS-09/10 Versionado y feedback
estado: borrador
depende_de: [RF-09, RF-10, RN-08, RN-09, RN-10]
---

# CUS-09/10 Versionado y feedback

1. El ingeniero carga un WAV; se valida que el formato sea sin pérdida ([RN-09](../reglas-negocio.md)).
2. Se genera la nomenclatura incremental ([RN-08](../reglas-negocio.md)), se sube por multipart al almacenamiento y se crea `version_audio` en estado `En revision`.
3. El cliente reproduce la versión con forma de onda.
4. Al pausar en un instante, registra una observación; se valida el saldo de rondas ([RN-10](../reglas-negocio.md)) y se crea `observacion_tecnica` con timestamp.

Requerimientos: [RF-09](../../03-requerimientos/RF-09.md), [RF-10](../../03-requerimientos/RF-10.md). Almacenamiento: Supabase Storage ([ADR-003](../../00-proyecto/decisiones/ADR-003-almacenamiento-supabase-storage.md)).
