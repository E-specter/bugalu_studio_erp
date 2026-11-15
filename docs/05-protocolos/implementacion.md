---
id: protocolo-implementacion
titulo: Protocolo de implementación
estado: borrador
depende_de: [protocolo-pruebas, agentes-equipo]
---

# Protocolo de implementación

Spec aprobada → tarea → rama → código + pruebas + docs → entrega → auditoría.

```
1. leader        → lee RF y specs relacionadas, crea tarea
2. implementador → dev-backend | dev-frontend | disenador-ui | documentador:
                   implementa + pruebas + actualiza docs del módulo
3. dev-audit     → revisa contra spec y criterios → APROBADO | RECHAZADO
4. leader        → integra; documentador actualiza changelog e índice documental
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
## TAREA-RFxx-<n>: <título>
- Rol: dev-backend | dev-frontend | disenador-ui | documentador
- Requerimiento: RF-xx · Repo y base (rama, HEAD)
- Skills: <las que debe cargar el rol>
- Specs: docs/...md y ejemplos de código (lista explícita)
- Objetivo: <una frase>
- Criterios de aceptación: <lista verificable, con comando y salida esperada>
- Archivos permitidos: <rutas>
- Fuera de alcance: <lista>
- Entorno: stack bugalu 456xx; MCP de Supabase solo lectura
- Entrega: formato ENTREGA + RED→GREEN
```

Cómo crearla (criterios y contrato en el RF, división por rol, numeración): skill `crear-tarea`.

## Formato de entrega

```markdown
## ENTREGA TAREA-<nnn>
- Archivos modificados: <lista>
- Pruebas añadidas y resultado: <comando + salida resumida>
- Documentación actualizada: <rutas>
- Desviaciones de la spec: <ninguna | detalle>
```

Rama según [convenciones](../01-arquitectura/convenciones.md#control-de-versiones). Pruebas según [pruebas](pruebas.md).
