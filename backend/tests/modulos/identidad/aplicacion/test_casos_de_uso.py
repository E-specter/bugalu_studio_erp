from uuid import uuid4

import pytest

from bugalu.compartido.errores import (
    CampoNoPermitido,
    Conflicto,
    NoEncontrado,
    SinPermiso,
    UltimoAdministrador,
)
from bugalu.modulos.identidad.aplicacion.actualizar_perfil.caso_de_uso import ActualizarPerfil
from bugalu.modulos.identidad.aplicacion.actualizar_usuario.caso_de_uso import ActualizarUsuario
from bugalu.modulos.identidad.aplicacion.aprobar_solicitud.caso_de_uso import AprobarSolicitud
from bugalu.modulos.identidad.aplicacion.crear_solicitud.caso_de_uso import CrearSolicitud
from bugalu.modulos.identidad.aplicacion.listar_solicitudes.caso_de_uso import ListarSolicitudes
from bugalu.modulos.identidad.aplicacion.listar_usuarios.caso_de_uso import ListarUsuarios
from bugalu.modulos.identidad.aplicacion.obtener_mi_solicitud.caso_de_uso import (
    ObtenerMiSolicitud,
)
from bugalu.modulos.identidad.aplicacion.rechazar_solicitud.caso_de_uso import RechazarSolicitud
from bugalu.modulos.identidad.aplicacion.verificar_correo.caso_de_uso import VerificarCorreo
from bugalu.modulos.identidad.dominio.solicitud import EstadoSolicitud
from bugalu.modulos.identidad.dominio.usuario import Rol
from tests.modulos.identidad.aplicacion.falsos import (
    SolicitudesFalsas,
    UsuariosFalsos,
    solicitud,
    usuario,
)


async def test_actualizar_perfil_aplica_solo_los_cambios_y_respeta_el_rol() -> None:
    ana = usuario()
    nuevo = await ActualizarPerfil(UsuariosFalsos(ana)).ejecutar(ana.id, {"telefono": "999888777"})
    assert nuevo.telefono == "999888777" and nuevo.nombre == "Ana"
    personal = usuario(Rol.PERSONAL)
    with pytest.raises(CampoNoPermitido):
        await ActualizarPerfil(UsuariosFalsos(personal)).ejecutar(
            personal.id, {"nombre_artistico": "x"}
        )


async def test_verificar_correo_marca_y_devuelve_el_perfil() -> None:
    ana = usuario()
    perfil = await VerificarCorreo(UsuariosFalsos(ana)).ejecutar(ana.id)
    assert perfil.correo_confirmado is True


async def test_crear_solicitud_de_un_cliente_y_conflicto_si_ya_es_personal() -> None:
    ana, luis = usuario(), usuario(Rol.PERSONAL)
    repo = SolicitudesFalsas()
    s = await CrearSolicitud(UsuariosFalsos(ana, luis), repo).ejecutar(ana.id, "ingenieria", None)
    assert s.estado is EstadoSolicitud.PENDIENTE and s.id_usuario == ana.id
    with pytest.raises(Conflicto):
        await CrearSolicitud(UsuariosFalsos(ana, luis), repo).ejecutar(luis.id, "x", None)


async def test_mi_solicitud_o_no_encontrado() -> None:
    ana = usuario()
    with pytest.raises(NoEncontrado):
        await ObtenerMiSolicitud(SolicitudesFalsas()).ejecutar(ana.id)
    s = solicitud(id_usuario=ana.id)
    assert await ObtenerMiSolicitud(SolicitudesFalsas(s)).ejecutar(ana.id) == s


async def test_listados_de_administracion_exigen_administrador() -> None:
    admin, cliente = usuario(Rol.ADMINISTRADOR), usuario()
    usuarios = UsuariosFalsos(admin, cliente)
    solicitudes = SolicitudesFalsas(solicitud(), solicitud(estado=EstadoSolicitud.RECHAZADA))
    with pytest.raises(SinPermiso):
        await ListarSolicitudes(usuarios, solicitudes).ejecutar(cliente.id, None)
    with pytest.raises(SinPermiso):
        await ListarUsuarios(usuarios).ejecutar(cliente.id, None)
    with pytest.raises(SinPermiso):
        await ListarUsuarios(usuarios).ejecutar(uuid4(), None)  # sin perfil
    pendientes = await ListarSolicitudes(usuarios, solicitudes).ejecutar(
        admin.id, EstadoSolicitud.PENDIENTE
    )
    assert len(pendientes) == 1
    assert [u.id for u in await ListarUsuarios(usuarios).ejecutar(admin.id, Rol.CLIENTE)] == [
        cliente.id
    ]


async def test_aprobar_asigna_el_rol_y_marca_la_solicitud() -> None:
    admin, ana = usuario(Rol.ADMINISTRADOR), usuario()
    usuarios = UsuariosFalsos(admin, ana)
    s = solicitud(id_usuario=ana.id)
    resultado = await AprobarSolicitud(usuarios, SolicitudesFalsas(s)).ejecutar(
        admin.id, s.id, Rol.PERSONAL, "mezcla"
    )
    assert resultado.estado is EstadoSolicitud.APROBADA
    assert (usuarios.usuarios[ana.id].rol, usuarios.usuarios[ana.id].especialidad) == (
        Rol.PERSONAL,
        "mezcla",
    )


async def test_aprobar_errores() -> None:
    admin, cliente = usuario(Rol.ADMINISTRADOR), usuario()
    usuarios = UsuariosFalsos(admin, cliente)
    hecha = solicitud(estado=EstadoSolicitud.APROBADA)
    caso = AprobarSolicitud(usuarios, SolicitudesFalsas(hecha))
    with pytest.raises(SinPermiso):
        await caso.ejecutar(cliente.id, hecha.id, Rol.PERSONAL, "x")
    with pytest.raises(NoEncontrado):
        await caso.ejecutar(admin.id, uuid4(), Rol.PERSONAL, "x")
    with pytest.raises(Conflicto):
        await caso.ejecutar(admin.id, hecha.id, Rol.PERSONAL, "x")


async def test_rechazar_guarda_el_motivo_y_no_toca_el_rol() -> None:
    admin, ana = usuario(Rol.ADMINISTRADOR), usuario()
    usuarios = UsuariosFalsos(admin, ana)
    s = solicitud(id_usuario=ana.id)
    repo = SolicitudesFalsas(s)
    r = await RechazarSolicitud(usuarios, repo).ejecutar(admin.id, s.id, "sin cupo")
    assert (r.estado, r.motivo) == (EstadoSolicitud.RECHAZADA, "sin cupo")
    assert usuarios.usuarios[ana.id].rol is Rol.CLIENTE
    with pytest.raises(Conflicto):
        await RechazarSolicitud(usuarios, repo).ejecutar(admin.id, s.id, "otra vez")


async def test_actualizar_usuario_fusiona_campos_y_protege_al_ultimo_administrador() -> None:
    admin, ana = usuario(Rol.ADMINISTRADOR), usuario()
    caso = ActualizarUsuario(UsuariosFalsos(admin, ana))
    nuevo = await caso.ejecutar(admin.id, ana.id, {"rol": Rol.PERSONAL})
    assert nuevo.rol is Rol.PERSONAL and nuevo.especialidad is None
    nuevo = await caso.ejecutar(admin.id, ana.id, {"especialidad": "mezcla"})
    assert (nuevo.rol, nuevo.especialidad) == (Rol.PERSONAL, "mezcla")
    with pytest.raises(UltimoAdministrador):
        await caso.ejecutar(admin.id, admin.id, {"rol": Rol.CLIENTE})
    with pytest.raises(NoEncontrado):
        await caso.ejecutar(admin.id, uuid4(), {"rol": Rol.PERSONAL})
    with pytest.raises(SinPermiso):
        await caso.ejecutar(ana.id, admin.id, {"rol": Rol.CLIENTE})
