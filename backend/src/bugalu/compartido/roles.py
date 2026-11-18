"""Las rutas de cliente de sala y pagos no son del rol `profesional` (RF-15, CA-01)."""

from typing import Annotated, Any

from fastapi import Depends, Request

from bugalu.compartido.autenticacion import obtener_claims
from bugalu.compartido.base_datos import transaccion_con_identidad
from bugalu.compartido.errores import SinPermiso


async def negar_profesional(
    request: Request, claims: Annotated[dict[str, Any], Depends(obtener_claims)]
) -> None:
    async with transaccion_con_identidad(request.app.state.pool, claims) as conexion:
        fila = await (await conexion.execute("select public.es_profesional()")).fetchone()
    if fila and fila[0]:
        raise SinPermiso("Un profesional no usa las reservas de sala ni los pagos.")


SOLO_CLIENTES = [Depends(negar_profesional)]
