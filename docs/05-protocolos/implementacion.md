---
id: protocolo-implementacion
titulo: Protocolo de implementación
estado: borrador
depende_de: [protocolo-pruebas]
---

# Protocolo de implementación

Spec aprobada → tarea → rama → código + pruebas + docs → entrega → auditoría.

```
1. leader       → lee RF y specs relacionadas, crea tarea
2. dev_backend  → implementa + pruebas + actualiza docs del módulo
   dev_frontend → implementa sobre contrato aprobado + pruebas
3. dev_audit    → revisa contra spec y criterios → APROBADO | RECHAZADO
4. leader       → integra, actualiza changelog e índice documental
```

Un rechazo en el paso 3 devuelve la tarea al paso 2 junto con el informe de auditoría.

## Ciclo de bajo consumo

- `leader` usa `superpowers:brainstorming` solo cuando hay preguntas abiertas, y `superpowers:writing-plans` para un plan por fase o por RF.
- La ejecución **no** carga `superpowers:subagent-driven-development` ni `superpowers:executing-plans`: el ciclo es este documento. La cabecera de cada plan enlaza aquí en lugar de citar esas skills.
- Por tarea: un implementador (`dev-backend`, `dev-frontend`, `disenador-ui` o `documentador`) y **un solo revisor**, `dev-audit`, en Sonnet.
- Compuertas Opus (`dev-audit` con `model: "opus"`): ver [equipo](../04-agentes/equipo.md#compuertas-opus).
- Tareas que caen en el alcance de `leader` (docs semánticos, `.claude/`, `scripts/`): las ejecuta `leader`, y solo la compuerta de cierre las revisa.
- Seguimiento: `leader` registra cada TAREA en la lista de trabajo de claude-mem de la fase o del RF.

## Formato de tarea

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

## Formato de entrega

```markdown
## ENTREGA TAREA-<nnn>
- Archivos modificados: <lista>
- Pruebas añadidas y resultado: <comando + salida resumida>
- Documentación actualizada: <rutas>
- Desviaciones de la spec: <ninguna | detalle>
```

Rama según [convenciones](../01-arquitectura/convenciones.md#control-de-versiones). Pruebas según [pruebas](pruebas.md).
