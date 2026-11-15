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
