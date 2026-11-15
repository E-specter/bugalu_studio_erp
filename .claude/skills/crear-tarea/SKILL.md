---
name: crear-tarea
description: Úsala cuando leader deba convertir un RF, un ajuste de auditoría o una parte de un plan de Bugalú en una TAREA para dev-backend, dev-frontend, disenador-ui o documentador.
---

# Crear una tarea

Formato: [formato de tarea](../../../docs/05-protocolos/implementacion.md#formato-de-tarea). Una tarea = un implementador + un revisor.

## Antes de crear tareas de un RF

1. **Criterios del RF.** Si su sección "Criterios de aceptación" dice "Pendiente", escríbela tú en el RF a partir de sus RN y su flujo. Cada decisión abierta (D-xx o un hueco del flujo) que cambie lo que se construye se le pregunta al usuario **antes**; no se inventa.
2. **Contrato API.** Escribe en el RF una sección `## Contrato API`: ruta, método, quién accede (público o rol), cuerpo, respuestas y códigos de error `snake_case` en español, con el formato único `{error:{codigo,mensaje}}`. Con el contrato escrito, backend y frontend pueden ir en paralelo; un cambio lo propone el implementador en su ENTREGA y lo apruebas tú.
3. **Dependencias.** Sigue el orden de implementación de [docs/README.md](../../../docs/README.md#requerimientos). Si el RF necesita una tabla o un RF aún no implementado, o se espera, o la tarea lo deja explícitamente en "Fuera de alcance" con un sustituto mínimo acordado con el usuario.

## Cómo dividir

En este orden, una tarea por fila que aplique:

| Orden | Tarea | Rol | Skill |
|---|---|---|---|
| 1 | Spec de pantalla `pantallas/RF-xx-<pantalla>.md` | disenador-ui | `disenar-pantalla` |
| 2 | Migración (tablas, RLS, buckets) | dev-backend | `crear-migracion` |
| 3 | Corte de backend que implementa el contrato | dev-backend | `crear-slice-backend` |
| 4 | Componentes que falten e isla o página | dev-frontend | `crear-componente`, `crear-isla` |
| 5 | Cierre: estado del RF a `implementado`, changelog | documentador | — |

1 y 2 pueden ir en paralelo; 3 tras 2; 4 tras 1 (y en paralelo con 3, gracias al contrato).

## Plantilla

Numeración: `TAREA-RFxx-<n>` en la fase 7; `TAREA-<fase><nn>` en las fases de esqueleto.

```markdown
## TAREA-RFxx-<n>: <título>
- Rol · Requerimiento · Repo y base (rama, HEAD)
- Skills: <las de la tabla>; "invoca primero <skill> con la herramienta Skill" si no está precargada
- Specs: <docs/… y ejemplos de código>
- Objetivo: <una frase>
- Criterios de aceptación: <verificables, con comando y salida esperada, incluidos los casos de rotura>
- Archivos permitidos · Fuera de alcance (incluido "commits")
- Entorno: stack bugalu 456xx; no tocar 543xx; MCP de Supabase solo lectura
- Entrega: formato ENTREGA + RED→GREEN por punto
```

**Casos de rotura que siempre van en los criterios cuando aplican:** token real con `alg` cambiado o caducado → 401; servicio de claves o base caídos → 503; otro usuario o `anon` no leen ni cambian lo ajeno (fila intacta); pruebas que pasan con el `.env` de la guía; estados no solo por color; sin JS; 401/503/red caída/no JSON en las islas.

## Seguimiento

- Una lista de claude-mem por RF (`rf-xx`) o por fase (`fase-n`); un `task` por tarea con `status`, `rol` y `depende_de`.
- Dos tareas corren a la vez solo si sus "Archivos permitidos" no se solapan; dilo en ambas.
- Al recibir la ENTREGA: repite tú las comprobaciones, revisa `git status`, haz el commit (Conventional Commits en español con las líneas de atribución) y lanza `dev-audit` (Opus si toca `identidad`, `pagos`, RLS o cierra la fase).
