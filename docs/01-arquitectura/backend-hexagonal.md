---
id: arq-backend-hexagonal
titulo: Backend — Hexagonal + Vertical Slicing
estado: borrador
depende_de: [arq-stack, convenciones]
---

# Backend — Hexagonal + Vertical Slicing

## Principios obligatorios

- SOLID.
- Arquitectura hexagonal (puertos y adaptadores) en tres capas: `dominio`, `aplicacion`, `infraestructura`.
- Vertical slicing: cada caso de uso es una porción autocontenida dentro de su módulo.

## Regla de dependencias

```
infraestructura  →  aplicacion  →  dominio
```

- `dominio`: entidades, objetos de valor, reglas de negocio y puertos (interfaces). Sin dependencias de FastAPI, Supabase ni librerías externas.
- `aplicacion`: casos de uso. Orquesta el dominio mediante puertos. Sin conocimiento de HTTP ni de la base de datos.
- `infraestructura`: adaptadores de entrada (routers FastAPI, esquemas Pydantic) y de salida (repositorios Supabase, pasarela de pagos, correo, almacenamiento).

## Estructura

```
backend/
├── pyproject.toml
├── src/bugalu/
│   ├── main.py                     # composición de la app y registro de routers
│   ├── compartido/                 # kernel compartido: errores, tipos base, eventos, configuración
│   └── modulos/
│       └── reservas/               # un módulo por contexto (ver tabla de módulos)
│           ├── dominio/
│           │   ├── reserva.py
│           │   ├── estado_reserva.py
│           │   ├── reglas.py       # buffer técnico, solapamientos
│           │   └── puertos.py      # RepositorioReservas, ServicioNotificaciones
│           ├── aplicacion/
│           │   ├── registrar_reserva/
│           │   │   ├── comando.py
│           │   │   └── caso_de_uso.py
│           │   └── cambiar_estado_reserva/
│           └── infraestructura/
│               ├── entrada/http/   # router.py, esquemas.py
│               └── salida/         # repositorio_supabase.py
└── tests/                          # espejo de src/: unitarios, integración, api
```

## Módulos del backend

| Módulo | Requerimientos |
|---|---|
| `identidad` | [RF-01](../03-requerimientos/RF-01.md) |
| `catalogo` | [RF-02](../03-requerimientos/RF-02.md) |
| `reservas` | [RF-03](../03-requerimientos/RF-03.md), [RF-04](../03-requerimientos/RF-04.md), [RF-06](../03-requerimientos/RF-06.md) |
| `pagos` | [RF-05](../03-requerimientos/RF-05.md), [RF-11](../03-requerimientos/RF-11.md) |
| `personal` | [RF-07](../03-requerimientos/RF-07.md) |
| `proyectos` | [RF-08](../03-requerimientos/RF-08.md), [RF-13](../03-requerimientos/RF-13.md) |
| `entregables` | [RF-09](../03-requerimientos/RF-09.md), [RF-10](../03-requerimientos/RF-10.md), [RF-12](../03-requerimientos/RF-12.md) |
| `reportes` | [RF-14](../03-requerimientos/RF-14.md) |
| `notificaciones` | Transversal ([RF-06](../03-requerimientos/RF-06.md)) |

## Correspondencia con el análisis BCE del informe

| BCE (informe RUP) | Implementación |
|---|---|
| Boundary (`FrmCalendarioSalas`, `FrmReproductorFeedback`) | Islas del frontend + routers FastAPI |
| Control (`CtrlGestionReservas`, `CtrlVersionadoAudio`) | Casos de uso en `aplicacion/` |
| Entity (`Reserva`, `VersionAudio`) | Entidades en `dominio/` + tablas en PostgreSQL |
