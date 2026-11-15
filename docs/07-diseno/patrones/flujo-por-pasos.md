---
id: patron-flujo-por-pasos
titulo: Patrón — Flujo por pasos
estado: borrador
depende_de: [comp-pasos, comp-resumen-persistente, comp-barra-acciones]
---

# Flujo por pasos

Origen: flujo de contratación (`141:28605` selección de servicio → `141:28788` brief → `141:29060` agenda de asesoría → `141:29356` cotización → `141:29617` revisión y contratación → `141:29858` proyecto activado). Es la rama de asesoría del flujo real ([agendar-asesoria](../../02-dominio/flujos/agendar-asesoria.md)); el mismo patrón sirve para la reserva de sala ([registrar-reserva](../../02-dominio/flujos/registrar-reserva.md)).

## Composición

```
cabecera-app (Flujo): identidad ─── guardado · código de solicitud
pasos: 01 ── 02 ── 03 ── 04 ── 05 ── 06
┌ formulario del paso ─────────────┐ ┌ resumen persistente ┐
│ encabezado (Flujo)               │ │ estado              │
│ paneles del paso                 │ │ datos elegidos      │
│ barra de acciones                │ │ total               │
└──────────────────────────────────┘ └─────────────────────┘
```

## Reglas

1. **Un paso = una página** con su URL (`/solicitud/<codigo>/agenda`). Avanzar envía el formulario; el servidor guarda y redirige al siguiente.
2. **Se puede volver** a cualquier paso hecho desde [pasos](../componentes/pasos.md) o "Anterior", sin perder datos.
3. **Guardado continuo:** cada paso enviado queda guardado; la cabecera muestra el [indicador](../componentes/indicador-estado.md) y el código de solicitud (para retomarla).
4. **El resumen persistente** muestra siempre lo elegido y el importe que corresponda; el usuario nunca llega a la revisión sin haber visto el precio.
5. **Revisión antes de comprometer:** el penúltimo paso muestra todo, condiciones (cláusulas) y la [casilla](../componentes/casilla.md) de aceptación; el botón principal nombra el compromiso ("Confirmar contratación").
6. **Paso final de confirmación:** qué pasó, qué sigue (próximos hitos) y acceso al portal; sin barra de acciones de flujo.
7. **Visitante sin cuenta:** la cuenta se crea dentro del flujo, en el paso donde es necesaria, sin sacarlo del flujo ([actores](../../02-dominio/actores-roles.md)).
8. Máximo 6 pasos visibles; si un proceso necesita más, se agrupan.

## Móvil

[Pasos](../componentes/pasos.md) Compacta, resumen como `<details>` sobre la barra de acciones y botones apilados.

## Accesibilidad

- Al cargar cada paso, el foco va al título (`<h1>`) y el `<title>` del documento incluye "Paso 3 de 6".
- Los errores del paso siguen [formularios](formularios.md#validación).
- Si hay retención de tiempo (franja pre-reservada), el tiempo restante se muestra en texto y se avisa antes de vencer.
