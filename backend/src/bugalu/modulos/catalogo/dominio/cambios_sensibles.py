"""Campos sensibles (RF-20 CA-04) y su comparacion.

Cada recurso se ve como un mapa plano {campo: texto canonico}: asi "mismo valor" es una igualdad de
texto, la vista previa y el registro de cambios guardan lo mismo, y los recargos anidados se nombran
`noche.porcentaje`, `noche.desde`...
"""

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime, time
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID

from bugalu.compartido.errores import ConfirmacionRequerida, PlazosIncoherentes
from bugalu.modulos.catalogo.dominio.precio import (
    ConfiguracionImpuestos,
    Especialista,
    Recargos,
    Servicio,
    Unidad,
)

PALABRA = "CONFIRMAR"
MINUTOS_DE_VIGENCIA = 10

PARAMETROS_SENSIBLES = (
    "dias_limite_pago",
    "horas_limite_pago",
    "porcentaje_adelanto",
    "horas_nivel_1",
    "horas_nivel_2",
    "porcentaje_penalizacion_nivel_2",
    "minutos_tolerancia_inasistencia",
    "dias_vigencia_credito",
    "reprogramaciones_nivel_1",
    "reprogramaciones_nivel_2",
)
SENSIBLES: dict[str, tuple[str, ...]] = {
    "impuestos": ("porcentaje_igv", "precios_incluyen_igv"),
    "servicio": ("tarifa_hora", "monto_fijo"),
    "especialista": ("monto_fijo", "monto_variable", "unidad"),
    "recargos": (
        "noche.porcentaje",
        "noche.desde",
        "noche.hasta",
        "fin_de_semana.porcentaje",
        "feriado.porcentaje",
    ),
    "parametros": PARAMETROS_SENSIBLES,
}
_BOOLEANOS = frozenset({"precios_incluyen_igv", "activo"})
_HORAS = frozenset({"noche.desde", "noche.hasta"})


def texto(valor: Any) -> str:
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, Decimal):
        return str(valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    if isinstance(valor, Unidad):
        return valor.value
    if isinstance(valor, time):
        return valor.strftime("%H:%M")
    return str(valor)


def tipar(campo: str, valor: str) -> Any:
    """Inversa de `texto` segun el campo (para aplicar lo que guardo la vista previa)."""
    if campo in _BOOLEANOS:
        return valor == "true"
    if campo in _HORAS:
        return time.fromisoformat(valor)
    if campo == "unidad":
        return Unidad(valor)
    if campo in PARAMETROS_SENSIBLES or campo.startswith("anticipacion_"):
        return int(valor)
    return Decimal(valor)


def valores_servicio(s: Servicio) -> dict[str, str]:
    return {"tarifa_hora": texto(s.tarifa_hora), "monto_fijo": texto(s.monto_fijo)}


def valores_especialista(e: Especialista) -> dict[str, str]:
    return {
        "monto_fijo": texto(e.monto_fijo),
        "monto_variable": texto(e.monto_variable),
        "unidad": texto(e.unidad),
    }


def valores_recargos(r: Recargos) -> dict[str, str]:
    return {
        "noche.porcentaje": texto(r.noche),
        "noche.desde": texto(r.desde_noche),
        "noche.hasta": texto(r.hasta_noche),
        "fin_de_semana.porcentaje": texto(r.fin_de_semana),
        "feriado.porcentaje": texto(r.feriado),
    }


def valores_impuestos(c: ConfiguracionImpuestos) -> dict[str, str]:
    return {"porcentaje_igv": texto(c.porcentaje), "precios_incluyen_igv": texto(c.incluido)}


def valores_parametros(p: Mapping[str, int]) -> dict[str, str]:
    return {clave: texto(valor) for clave, valor in p.items()}


_ATRIBUTO_IMPUESTOS = {"porcentaje_igv": "porcentaje", "precios_incluyen_igv": "incluido"}
_ATRIBUTO_RECARGOS = {
    "noche.porcentaje": "noche",
    "noche.desde": "desde_noche",
    "noche.hasta": "hasta_noche",
    "fin_de_semana.porcentaje": "fin_de_semana",
    "feriado.porcentaje": "feriado",
}


def tipados(cambios: Mapping[str, str]) -> dict[str, Any]:
    return {campo: tipar(campo, valor) for campo, valor in cambios.items()}


def aplicar(recurso: str, actual: Any, cambios: Mapping[str, str]) -> Any:
    """El recurso (objeto de dominio, o {clave: entero} en parametros) con los cambios puestos."""
    nuevos = tipados(cambios)
    if recurso == "parametros":
        return {**actual, **nuevos}
    atributos = {"impuestos": _ATRIBUTO_IMPUESTOS, "recargos": _ATRIBUTO_RECARGOS}.get(recurso)
    return replace(actual, **{(atributos or {}).get(c, c): v for c, v in nuevos.items()})


def diferencias(
    actual: Mapping[str, str], propuesto: Mapping[str, str]
) -> dict[str, tuple[str, str]]:
    """{campo: (anterior, nuevo)} solo de lo que de verdad cambia."""
    return {k: (actual[k], v) for k, v in propuesto.items() if k in actual and actual[k] != v}


def exigir_confirmacion(
    recurso: str, actual: Mapping[str, str], propuesto: Mapping[str, str]
) -> None:
    """428 si la peticion cambia el valor de algun campo sensible; lo demas sigue en un paso."""
    sensibles = {k: v for k, v in propuesto.items() if k in SENSIBLES[recurso]}
    if campos := list(diferencias(actual, sensibles)):
        raise ConfirmacionRequerida(campos)


def validar_plazos(parametros: Mapping[str, int]) -> None:
    """El nivel 1 (mas lejano) debe superar al nivel 2 (ADR-015)."""
    if parametros["horas_nivel_1"] <= parametros["horas_nivel_2"]:
        raise PlazosIncoherentes(
            "Las horas del nivel 1 deben ser mayores que las del nivel 2.",
            {"campo": "horas_nivel_1"},
        )


@dataclass(frozen=True)
class Confirmacion:
    """Lo guardado en la vista previa; `cambios` = {campo: (anterior, nuevo)}."""

    id: UUID
    id_autor: UUID
    recurso: str
    id_recurso: UUID | None
    nombre_recurso: str
    cambios: dict[str, tuple[str, str]]
    vigente: bool  # sin usar y sin vencer


@dataclass(frozen=True)
class CambioRegistrado:
    id: UUID
    cambiado_en: datetime
    id_autor: UUID
    autor_nombre: str
    recurso: str
    id_recurso: UUID | None
    nombre_recurso: str
    campo: str
    anterior: str
    nuevo: str
