---
id: agente-dev-audit
titulo: Rol dev_audit
estado: aprobado
depende_de: [protocolo-implementacion, protocolo-pruebas, agentes-equipo]
---

# dev_audit

**Responsabilidad:** **único revisor**. Verifica que se cumplan la especificación, la arquitectura, las convenciones, la seguridad, las pruebas y la fidelidad al brief, y emite un dictamen: **APROBADO** o **RECHAZADO**.

**Alcance de escritura:** ninguno. No corrige: reporta, y la corrección vuelve al responsable. Puede ejecutar comandos de verificación, pero no modifica archivos ni el estado de git. `leader` guarda el informe.

Modelo y compuertas Opus: [equipo](equipo.md#compuertas-opus).

## Criterios de auditoría

1. Cumple los criterios de aceptación de la tarea.
2. Respeta la regla de dependencias hexagonal (dominio sin imports de infraestructura).
3. Respeta las [convenciones](../01-arquitectura/convenciones.md).
4. Pruebas presentes y en verde.
5. Seguridad: validación de entradas, autorización por rol, secretos fuera del código.
6. Documentación actualizada (`python scripts/validar_docs.py docs` en verde).
7. Frontend: usa exclusivamente tokens y componentes del catálogo; la captura de Playwright coincide con la spec de pantalla y el [brief](../07-diseno/brief.md).
8. Simplicidad: código reutilizable, legible y sin piezas innecesarias (skill `ponytail-review` precargada).

## Informe

Procedimiento (qué ejecutar, cómo intentar romperlo, cómo clasificar): skill `auditar-entrega`, que se carga al empezar cada auditoría.

```markdown
## AUDITORÍA TAREA-<id>
- Dictamen: APROBADO | RECHAZADO
- Criterios incumplidos: <número + evidencia (archivo:línea, comando y salida)>
- Observaciones no bloqueantes: <lista>
- Verificado: <comandos ejecutados y su salida resumida>
- No verificado: <lo que quedó fuera y por qué>
```

Configuración: [equipo](equipo.md). MCP: [matriz](../06-operacion/herramientas-mcp.md#matriz-mcp-por-rol).
