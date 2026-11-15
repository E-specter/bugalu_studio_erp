import pytest

from bugalu.compartido.errores import CampoNoPermitido, Conflicto
from bugalu.modulos.identidad.dominio.reglas import (
    validar_cambios_de_perfil,
    validar_resolucion,
    validar_solicitud_nueva,
)
from bugalu.modulos.identidad.dominio.solicitud import EstadoSolicitud
from bugalu.modulos.identidad.dominio.usuario import Rol
from tests.modulos.identidad.aplicacion.falsos import solicitud, usuario


def test_el_cliente_cambia_su_nombre_artistico() -> None:
    validar_cambios_de_perfil(usuario(), {"nombre_artistico": "Ana MC", "nombre": "Ana"})


@pytest.mark.parametrize("rol", [Rol.PERSONAL, Rol.ADMINISTRADOR])
def test_el_personal_no_tiene_nombre_artistico(rol: Rol) -> None:
    with pytest.raises(CampoNoPermitido):
        validar_cambios_de_perfil(usuario(rol), {"nombre_artistico": "x"})


def test_el_personal_si_cambia_nombre_y_telefono() -> None:
    validar_cambios_de_perfil(usuario(Rol.PERSONAL), {"nombre": "x", "telefono": "999888777"})


def test_solo_un_cliente_solicita_acceso() -> None:
    validar_solicitud_nueva(usuario())
    for rol in (Rol.PERSONAL, Rol.ADMINISTRADOR):
        with pytest.raises(Conflicto):
            validar_solicitud_nueva(usuario(rol))


def test_solo_una_solicitud_pendiente_se_resuelve() -> None:
    validar_resolucion(solicitud())
    with pytest.raises(Conflicto):
        validar_resolucion(solicitud(estado=EstadoSolicitud.APROBADA))
