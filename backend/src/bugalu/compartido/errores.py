"""Errores del kernel, sin dependencias de HTTP (formato de respuesta: manejadores_http)."""

from typing import Any


class ErrorDeNegocio(Exception):
    codigo = "error_de_negocio"
    estado_http = 400

    def __init__(self, mensaje: str, detalles: dict[str, Any] | None = None) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.detalles = detalles  # serializable a JSON; la respuesta lo incluye solo si existe


class NoAutenticado(ErrorDeNegocio):
    codigo = "no_autenticado"
    estado_http = 401


class NoEncontrado(ErrorDeNegocio):
    codigo = "no_encontrado"
    estado_http = 404


class AutenticacionNoDisponible(ErrorDeNegocio):
    codigo = "autenticacion_no_disponible"
    estado_http = 503


class SinPermiso(ErrorDeNegocio):
    codigo = "sin_permiso"
    estado_http = 403


class Conflicto(ErrorDeNegocio):
    codigo = "conflicto"
    estado_http = 409


class UltimoAdministrador(Conflicto):
    codigo = "ultimo_administrador"

    def __init__(self) -> None:
        super().__init__("No puede quedar el sistema sin administradores.")


class VerificacionNoValida(Conflicto):
    codigo = "verificacion_no_valida"

    def __init__(self) -> None:
        super().__init__("La sesion no viene de un enlace de correo ni de Google.")


class CampoNoPermitido(ErrorDeNegocio):
    codigo = "campo_no_permitido"
    estado_http = 422


class DatosInvalidos(ErrorDeNegocio):
    codigo = "datos_invalidos"
    estado_http = 422


class TramoInvalido(DatosInvalidos):
    codigo = "tramo_invalido"


class ServicioNoReservable(DatosInvalidos):
    codigo = "servicio_no_reservable"


class FeriadoRepetido(Conflicto):
    codigo = "feriado_repetido"


class FranjaSolapada(Conflicto):
    codigo = "franja_solapada"


class FranjaConReservas(Conflicto):
    codigo = "franja_con_reservas"


class CierreConReservas(Conflicto):
    codigo = "cierre_con_reservas"


class RangoInvalido(DatosInvalidos):
    codigo = "rango_invalido"
