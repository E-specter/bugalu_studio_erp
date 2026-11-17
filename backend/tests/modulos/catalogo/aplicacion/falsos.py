from collections.abc import Collection, Mapping, Sequence
from dataclasses import replace
from datetime import date, time
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from bugalu.compartido.errores import FeriadoRepetido
from bugalu.modulos.catalogo.dominio.precio import (
    ConfiguracionImpuestos,
    Especialista,
    Feriado,
    Recargos,
    Servicio,
    Unidad,
)

D = Decimal
INGENIERO = Especialista(uuid4(), "Ingeniero", D("30"), D("25"), Unidad.LAPSO_30, True)
EJECUTANTE = Especialista(uuid4(), "Ejecutante", D("50"), D("40"), Unidad.HORA, True)
SERVICIO = Servicio(uuid4(), "Grabacion", "grabacion", True, D("80"), D("0"), (INGENIERO.id,), True)
MEZCLA = Servicio(uuid4(), "Mezcla", "posproduccion", False, D("0"), D("0"), (), True)
SALA = uuid4()


class CatalogoFalso:
    def __init__(self, administrador: bool = True) -> None:
        self.administrador = administrador
        self.servicios = {s.id: s for s in (SERVICIO, MEZCLA)}
        self.especialistas = {e.id: e for e in (INGENIERO, EJECUTANTE)}
        self.recargos = Recargos(D(25), time(20), time(6), D(20), D(30))
        self.feriados: dict[date, Feriado] = {}
        self.escrituras = 0

    async def es_administrador(self) -> bool:
        return self.administrador

    async def existe_sala(self, id_sala: UUID) -> bool:
        return id_sala == SALA

    async def listar_servicios(self) -> list[Servicio]:
        return list(self.servicios.values())

    async def obtener_servicio(self, id_servicio: UUID) -> Servicio | None:
        return self.servicios.get(id_servicio)

    async def actualizar_servicio(
        self, id_servicio: UUID, cambios: Mapping[str, Decimal | bool]
    ) -> None:
        self.escrituras += 1
        self.servicios[id_servicio] = replace(self.servicios[id_servicio], **cambios)

    async def reemplazar_especialistas_por_defecto(
        self, id_servicio: UUID, ids: Sequence[UUID]
    ) -> None:
        self.escrituras += 1
        self.servicios[id_servicio] = replace(
            self.servicios[id_servicio], especialistas_por_defecto=tuple(ids)
        )

    async def listar_especialistas(self) -> list[Especialista]:
        return list(self.especialistas.values())

    async def obtener_especialistas(self, ids: Collection[UUID]) -> list[Especialista]:
        return [e for i, e in self.especialistas.items() if i in ids]

    async def actualizar_especialista(
        self, id_especialista: UUID, cambios: Mapping[str, Decimal | bool | str]
    ) -> Especialista | None:
        if id_especialista not in self.especialistas:
            return None
        self.escrituras += 1
        self.especialistas[id_especialista] = replace(
            self.especialistas[id_especialista], **cambios
        )
        return self.especialistas[id_especialista]

    async def obtener_impuestos(self) -> ConfiguracionImpuestos:
        return ConfiguracionImpuestos(D("18.00"), True)

    async def parametros_vigentes(self) -> dict[str, Any]:
        return {
            "porcentaje_igv": "18.00",
            "precios_incluyen_igv": True,
            "horas_limite_pago": 1,
            "horas_nivel_1": 48,
            "horas_nivel_2": 24,
            "porcentaje_adelanto": 50,
        }

    async def obtener_recargos(self) -> Recargos:
        return self.recargos

    async def guardar_recargos(self, recargos: Recargos) -> None:
        self.escrituras += 1
        self.recargos = recargos

    async def listar_feriados(self, anio: int | None) -> list[Feriado]:
        return [f for f in self.feriados.values() if anio is None or f.fecha.year == anio]

    async def feriados_en(self, fechas: Collection[date]) -> frozenset[date]:
        return frozenset(f for f in self.feriados if f in fechas)

    async def agregar_feriado(self, feriado: Feriado) -> None:
        if feriado.fecha in self.feriados:
            raise FeriadoRepetido("Ya existe un feriado en esa fecha.")
        self.escrituras += 1
        self.feriados[feriado.fecha] = feriado

    async def eliminar_feriado(self, fecha: date) -> bool:
        self.escrituras += 1
        return self.feriados.pop(fecha, None) is not None
