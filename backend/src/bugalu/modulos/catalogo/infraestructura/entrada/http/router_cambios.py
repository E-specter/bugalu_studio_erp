"""RF-20: cambios sensibles con vista previa, confirmacion y registro de cambios."""

from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ValidationError

from bugalu.compartido.autenticacion import obtener_claims
from bugalu.compartido.base_datos import transaccion_con_identidad
from bugalu.compartido.errores import DatosInvalidos
from bugalu.compartido.esquemas import RespuestaError
from bugalu.modulos.catalogo.aplicacion.confirmar_cambio.caso_de_uso import ConfirmarCambio
from bugalu.modulos.catalogo.aplicacion.listar_registro_cambios.caso_de_uso import (
    ListarRegistroCambios,
)
from bugalu.modulos.catalogo.aplicacion.previsualizar_cambio.caso_de_uso import (
    PrevisualizarCambio,
)
from bugalu.modulos.catalogo.dominio import cambios_sensibles as sensibles
from bugalu.modulos.catalogo.dominio.precio import LIMA
from bugalu.modulos.catalogo.infraestructura.entrada.http import esquemas as e
from bugalu.modulos.catalogo.infraestructura.salida.repositorio_cambios_postgres import (
    RepositorioCambiosPostgres,
)
from bugalu.modulos.catalogo.infraestructura.salida.repositorio_postgres import (
    RepositorioCatalogoPostgres,
)
from bugalu.modulos.reservas.infraestructura.entrada.http.esquemas import (
    CambiosParametros,
    Parametros,
)

router = APIRouter(tags=["cambios-sensibles"])

Claims = Annotated[dict[str, Any], Depends(obtener_claims)]

_DESCRIPCION = {
    401: "Token ausente, invalido o caducado",
    403: "Se requiere el rol administrador (y, al confirmar, ser quien hizo la vista previa)",
    404: "No existe el servicio o el especialista",
    409: "Confirmacion no valida (usada, vencida o inexistente) o cambio desactualizado",
    422: "Datos invalidos, sin cambios, plazos incoherentes, palabra incorrecta o rango invalido",
    503: "Servicio de autenticacion o base de datos no disponible",
}


def _respuestas(*codigos: int) -> dict[int | str, dict[str, Any]]:
    return {
        c: {"model": RespuestaError, "description": _DESCRIPCION[c]}
        for c in (401, 403, *codigos, 503)
    }


_MODELOS: dict[str, type[BaseModel]] = {
    "impuestos": e.CambiosImpuestos,
    "servicio": e.SensiblesServicio,
    "especialista": e.SensiblesEspecialista,
    "recargos": e.Recargos,
    "parametros": CambiosParametros,
}


def _texto_de_cambios(cuerpo: e.NuevaPrevisualizacion) -> dict[str, str]:
    """Valida `cambios` como el endpoint del recurso y lo pasa a {campo: texto canonico}."""
    if (cuerpo.id_recurso is not None) != (cuerpo.recurso in ("servicio", "especialista")):
        raise DatosInvalidos(
            "id_recurso solo va en servicio y especialista.", {"campo": "id_recurso"}
        )
    try:
        modelo = _MODELOS[cuerpo.recurso].model_validate(cuerpo.cambios)
    except ValidationError as error:
        campo = ".".join(str(p) for p in error.errors()[0]["loc"]) or "cambios"
        raise DatosInvalidos(f"Datos invalidos: {campo}.", {"campo": campo}) from error
    if isinstance(modelo, e.Recargos):
        return sensibles.valores_recargos(modelo.a_dominio())
    propuesto = {c: sensibles.texto(v) for c, v in modelo.model_dump(exclude_unset=True).items()}
    if extra := [c for c in propuesto if c not in sensibles.SENSIBLES[cuerpo.recurso]]:
        raise DatosInvalidos(f"Datos invalidos: {extra[0]}.", {"campo": extra[0]})
    return propuesto


@router.post(
    "/cambios-sensibles/previsualizar",
    response_model=e.Previsualizacion,
    summary="Vista previa de un cambio sensible: antes, despues, impacto y token (administrador)",
    responses=_respuestas(404, 422),
)
async def previsualizar(
    request: Request, claims: Claims, cuerpo: e.NuevaPrevisualizacion
) -> e.Previsualizacion:
    propuesto = _texto_de_cambios(cuerpo)
    async with transaccion_con_identidad(request.app.state.pool, claims) as conexion:
        p = await PrevisualizarCambio(
            RepositorioCatalogoPostgres(conexion), RepositorioCambiosPostgres(conexion)
        ).ejecutar(cuerpo.recurso, cuerpo.id_recurso, propuesto, datetime.now(UTC))
    return e.Previsualizacion(
        token=p.token,
        expira_en=p.expira_en,
        recurso=p.recurso,
        id_recurso=p.id_recurso,
        nombre_recurso=p.nombre_recurso,
        cambios=[e.CambioPrevio(campo=c, anterior=a, nuevo=n) for c, a, n in p.cambios],
        impacto=e.Impacto(
            ejemplos=[e.EjemploImpacto(**vars(x)) for x in p.ejemplos],
            operaciones_vigentes=p.operaciones_vigentes,
        ),
    )


def _valor(recurso: str, objeto: Any) -> dict[str, Any]:
    construir: dict[str, Callable[[Any], BaseModel]] = {
        "servicio": e.Servicio.desde_dominio,
        "especialista": e.Especialista.desde_dominio,
        "impuestos": e.Impuestos.desde_dominio,
        "recargos": e.Recargos.desde_dominio,
        "parametros": lambda valores: Parametros(**valores),
    }
    valor: dict[str, Any] = construir[recurso](objeto).model_dump(mode="json")
    return valor


@router.post(
    "/cambios-sensibles/confirmar",
    response_model=e.CambioConfirmado,
    summary="Aplica el cambio de una vista previa con la palabra CONFIRMAR (administrador)",
    responses=_respuestas(409, 422),
)
async def confirmar(
    request: Request, claims: Claims, cuerpo: e.NuevaConfirmacion
) -> e.CambioConfirmado:
    async with transaccion_con_identidad(request.app.state.pool, claims) as conexion:
        c = await ConfirmarCambio(
            RepositorioCatalogoPostgres(conexion), RepositorioCambiosPostgres(conexion)
        ).ejecutar(cuerpo.token, cuerpo.palabra)
    return e.CambioConfirmado(
        recurso=c.confirmacion.recurso,
        id_recurso=c.confirmacion.id_recurso,
        valor=_valor(c.confirmacion.recurso, c.valor),
        cambios=[e.CambioRegistrado.desde_dominio(x) for x in c.cambios],
    )


@router.get(
    "/registro-cambios",
    response_model=list[e.CambioRegistrado],
    summary="Registro de cambios sensibles, del mas reciente al mas antiguo (administrador)",
    responses=_respuestas(422),
)
async def listar_registro(
    request: Request,
    claims: Claims,
    desde: Annotated[date | None, Query()] = None,
    hasta: Annotated[date | None, Query()] = None,
    recurso: Annotated[e.Recurso | None, Query()] = None,
) -> list[e.CambioRegistrado]:
    async with transaccion_con_identidad(request.app.state.pool, claims) as conexion:
        cambios = await ListarRegistroCambios(
            RepositorioCatalogoPostgres(conexion), RepositorioCambiosPostgres(conexion)
        ).ejecutar(desde, hasta, recurso, datetime.now(LIMA).date())
    return [e.CambioRegistrado.desde_dominio(c) for c in cambios]
