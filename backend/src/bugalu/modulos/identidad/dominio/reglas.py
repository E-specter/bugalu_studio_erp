"""Reglas de RF-01 como funciones puras."""

from collections.abc import Mapping

from bugalu.compartido.errores import CampoNoPermitido, Conflicto
from bugalu.modulos.identidad.dominio.solicitud import EstadoSolicitud, Solicitud
from bugalu.modulos.identidad.dominio.usuario import Rol, Usuario


def validar_cambios_de_perfil(usuario: Usuario, cambios: Mapping[str, str | None]) -> None:
    if "nombre_artistico" in cambios and usuario.rol is not Rol.CLIENTE:
        raise CampoNoPermitido("Solo el cliente tiene nombre artistico.")


def validar_solicitud_nueva(usuario: Usuario) -> None:
    if usuario.rol is not Rol.CLIENTE:
        raise Conflicto("El usuario ya tiene acceso interno.")


def validar_resolucion(solicitud: Solicitud) -> None:
    if solicitud.estado is not EstadoSolicitud.PENDIENTE:
        raise Conflicto("La solicitud ya fue resuelta.")
