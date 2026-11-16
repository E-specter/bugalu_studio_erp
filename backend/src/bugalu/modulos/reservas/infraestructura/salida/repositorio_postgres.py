from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from psycopg import AsyncConnection, errors

from bugalu.compartido.errores import FranjaSolapada
from bugalu.modulos.reservas.dominio.disponibilidad import Tramo
from bugalu.modulos.reservas.dominio.modelos import (
    PARAMETROS,
    Cierre,
    Franja,
    ReservaVisible,
    Sala,
)

_TOPE_SUGERENCIA = 300


class RepositorioReservasPostgres:
    """Recibe una transaccion ya abierta (publica o con identidad): la RLS decide el acceso."""

    def __init__(self, conexion: AsyncConnection) -> None:
        self._conexion = conexion

    async def _filas(self, consulta: str, parametros: Sequence[Any] = ()) -> list[Any]:
        cursor = await self._conexion.execute(consulta, parametros)
        return await cursor.fetchall()

    async def es_administrador(self) -> bool:
        return bool((await self._filas("select public.es_administrador()"))[0][0])

    async def es_personal(self) -> bool:
        return bool((await self._filas("select public.es_personal()"))[0][0])

    async def listar_salas(self) -> list[Sala]:
        filas = await self._filas(
            "select id, nombre, sede from public.sala_tecnica where activa order by sede, nombre"
        )
        return [Sala(*f) for f in filas]

    async def existe_sala(self, id_sala: UUID) -> bool:
        filas = await self._filas(
            "select 1 from public.sala_tecnica where id = %s and activa", (id_sala,)
        )
        return bool(filas)

    async def limites_reserva(self) -> tuple[int, int]:
        minima, maxima = (await self._filas("select * from public.limites_reserva()"))[0]
        return int(minima), int(maxima)

    async def franjas_en(self, id_sala: UUID, desde: datetime, hasta: datetime) -> list[Franja]:
        filas = await self._filas(
            "select id, id_sala, inicio, fin from public.franja_sala "
            "where id_sala = %s and inicio < %s and fin > %s order by inicio",
            (id_sala, hasta, desde),
        )
        return [Franja(*f) for f in filas]

    async def franjas_antes_de(self, id_sala: UUID, instante: datetime) -> list[Franja]:
        filas = await self._filas(
            "select id, id_sala, inicio, fin from public.franja_sala "
            "where id_sala = %s and inicio < %s order by inicio desc limit %s",
            (id_sala, instante, _TOPE_SUGERENCIA),
        )
        return [Franja(*f) for f in filas]

    async def cierres_en(self, id_sala: UUID, desde: datetime, hasta: datetime) -> list[Cierre]:
        filas = await self._filas(
            "select id, id_sala, inicio, fin, motivo from public.cierre_sala "
            "where id_sala = %s and inicio < %s and fin > %s order by inicio",
            (id_sala, hasta, desde),
        )
        return [Cierre(*f) for f in filas]

    async def ocupacion(self, id_sala: UUID, desde: datetime, hasta: datetime) -> list[Tramo]:
        filas = await self._filas(
            "select inicio, fin_buffer from public.ocupacion_sala(%s, %s, %s)",
            (id_sala, desde, hasta),
        )
        return [Tramo(*f) for f in filas]

    async def reservas_visibles(
        self, id_sala: UUID, desde: datetime, hasta: datetime
    ) -> list[ReservaVisible]:
        filas = await self._filas(
            "select r.id, r.folio, r.id_cliente, s.nombre, r.estado, r.inicio, r.fin_buffer "
            "from public.reserva r join public.servicio s on s.id = r.id_servicio "
            "where r.id_sala = %s and r.estado <> 'cancelada' "
            "and r.inicio < %s and r.fin_buffer > %s order by r.inicio",
            (id_sala, hasta, desde),
        )
        return [ReservaVisible(*f) for f in filas]

    async def nombres_de_clientes(self, ids: Sequence[UUID]) -> Mapping[UUID, str | None]:
        if not ids:
            return {}
        filas = await self._filas(
            "select id, nombre from public.nombres_de_clientes(%s)", (list(ids),)
        )
        return {f[0]: f[1] for f in filas}

    async def insertar_franjas(self, id_sala: UUID, tramos: Sequence[Tramo]) -> list[Franja]:
        nuevas = []
        for tramo in tramos:
            try:
                filas = await self._filas(
                    "insert into public.franja_sala (id_sala, inicio, fin, id_publicador) "
                    "values (%s, %s, %s, (select auth.uid())) "
                    "returning id, id_sala, inicio, fin",
                    (id_sala, tramo.inicio, tramo.fin),
                )
            except errors.ExclusionViolation:
                raise FranjaSolapada("La franja se solapa con otra de la sala.") from None
            nuevas.append(Franja(*filas[0]))
        return nuevas

    async def obtener_franja(self, id_franja: UUID) -> Franja | None:
        filas = await self._filas(
            "select id, id_sala, inicio, fin from public.franja_sala where id = %s", (id_franja,)
        )
        return Franja(*filas[0]) if filas else None

    async def eliminar_franja(self, id_franja: UUID) -> None:
        await self._conexion.execute("delete from public.franja_sala where id = %s", (id_franja,))

    async def insertar_cierre(self, id_sala: UUID, tramo: Tramo, motivo: str) -> Cierre:
        filas = await self._filas(
            "insert into public.cierre_sala (id_sala, inicio, fin, motivo, id_autor) "
            "values (%s, %s, %s, %s, (select auth.uid())) "
            "returning id, id_sala, inicio, fin, motivo",
            (id_sala, tramo.inicio, tramo.fin, motivo),
        )
        return Cierre(*filas[0])

    async def obtener_cierre(self, id_cierre: UUID) -> Cierre | None:
        filas = await self._filas(
            "select id, id_sala, inicio, fin, motivo from public.cierre_sala where id = %s",
            (id_cierre,),
        )
        return Cierre(*filas[0]) if filas else None

    async def eliminar_cierre(self, id_cierre: UUID) -> None:
        await self._conexion.execute("delete from public.cierre_sala where id = %s", (id_cierre,))

    async def obtener_parametros(self) -> dict[str, int]:
        filas = await self._filas("select clave, valor from public.parametro")
        return {clave: int(valor) for clave, valor in filas}

    async def guardar_parametros(self, cambios: Mapping[str, int]) -> None:
        for clave, valor in cambios.items():
            if clave not in PARAMETROS:
                raise ValueError("Parametro desconocido.")
            await self._conexion.execute(
                "update public.parametro set valor = %s where clave = %s", (valor, clave)
            )
