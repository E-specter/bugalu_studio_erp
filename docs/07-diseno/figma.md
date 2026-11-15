---
id: diseno-figma
titulo: Archivo Figma y flujo diseño → código
estado: borrador
depende_de: [D-13, D-14]
---

# Figma

Archivo maestro, plan y asiento: pendiente (D-13). Code Connect: pendiente (D-14). Ver [decisiones](../00-proyecto/decisiones/README.md).

## Organización del archivo

| Página | Contenido |
|---|---|
| `00 Portada` | Brief resumido, estado y enlaces a `docs/07-diseno/` |
| `01 Fundamentos` | Variables: color, tipografía, espaciado, radios, sombras, puntos de quiebre |
| `02 Componentes` | Botones, campos, tarjetas, modales, tablas, estados de reserva |
| `03 Patrones` | Calendario de salas, reproductor con forma de onda, carga de archivos, resumen de pago |
| `04 Pantallas` | Un grupo por módulo ([módulos](../01-arquitectura/backend-hexagonal.md#modulos-del-backend)); frames nombrados `RF-xx / <pantalla> / <estado>` |
| `05 Prototipos` | Flujos navegables de CUS-04 y CUS-09/10 |

Convenciones de nombres Figma ↔ código: [componentes](componentes.md) y [tokens](tokens.md).

## Flujo diseño → código

```
1. usuario/leader → diseña o aprueba el frame en Figma y registra la spec en docs/07-diseno/pantallas/
2. leader         → crea la tarea con enlace al frame y RF asociado
3. dev_frontend   → obtiene contexto del frame vía Figma MCP (estructura, variables, captura)
                  → traduce a Astro + HTML/CSS/JS nativo usando tokens y componentes existentes
4. dev_audit      → compara captura de Playwright con la captura del frame; valida tokens y accesibilidad
5. leader         → integra y marca la pantalla como implementada en el inventario
```

**Regla de traducción:** el Figma MCP entrega por defecto código de referencia en React + Tailwind. Ese código es solo referencia estructural; nunca se copia. La implementación se hace en Astro, CSS con variables y Web Components según [frontend-islas](../01-arquitectura/frontend-islas.md).

Ningún agente escribe en el lienzo de Figma sin aprobación explícita del usuario.
