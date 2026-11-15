---
id: protocolo-cambios
titulo: Protocolo de cambios
estado: borrador
depende_de: []
---

# Protocolo de cambios

1. **Solicitud:** el usuario o un agente describe el cambio.
2. **Impacto en specs:** `leader` identifica qué archivos de `docs/` cambian (RF, RN, modelo de datos, pantallas).
3. **ADR:** si altera la arquitectura o cierra una decisión abierta, se crea un ADR en [decisiones](../00-proyecto/decisiones/README.md).
4. **Aprobación:** `leader` aprueba y actualiza las specs **antes** de crear tareas de implementación.

Los requerimientos nuevos o informales se integran a `03-requerimientos/` con numeración secuencial (siguiente RF libre) y estado `borrador`.
