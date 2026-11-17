"""RF-17 etapa A: reglas del perfil reforzado y consentimientos, con repositorio falso."""

import pytest

from bugalu.compartido.errores import DatosInvalidos, DeclaracionRequerida, TelefonoRequerido
from bugalu.modulos.identidad.aplicacion.actualizar_consentimientos.caso_de_uso import (
    ActualizarConsentimientos,
)
from bugalu.modulos.identidad.aplicacion.actualizar_perfil.caso_de_uso import ActualizarPerfil
from bugalu.modulos.identidad.aplicacion.armar_perfil.caso_de_uso import ArmarPerfil
from bugalu.modulos.identidad.aplicacion.listar_usuarios.caso_de_uso import ListarUsuarios
from bugalu.modulos.identidad.dominio.usuario import Pendiente, Rol
from tests.modulos.identidad.aplicacion.falsos import UsuariosFalsos, usuario

INTEGRANTES = [{"nombre": "Ana", "rol": "voz"}]
DECLARACION = Pendiente("declaracion_agrupacion", "1.0.0", "registro", "registro_pendiente")


async def test_agrupacion_sin_integrantes_es_datos_invalidos() -> None:
    ana = usuario()
    with pytest.raises(DatosInvalidos) as error:
        await ActualizarPerfil(UsuariosFalsos(ana)).ejecutar(ana.id, {"modalidad": "agrupacion"})
    assert error.value.detalles == {"campo": "integrantes"}


async def test_individual_con_integrantes_es_datos_invalidos() -> None:
    ana = usuario()
    with pytest.raises(DatosInvalidos):
        await ActualizarPerfil(UsuariosFalsos(ana)).ejecutar(ana.id, {"integrantes": INTEGRANTES})


async def test_agrupacion_con_la_declaracion_pendiente_es_409() -> None:
    ana = usuario()
    repo = UsuariosFalsos(ana)
    repo.textos_pendientes = [DECLARACION]
    with pytest.raises(DeclaracionRequerida):
        await ActualizarPerfil(repo).ejecutar(
            ana.id, {"modalidad": "agrupacion", "integrantes": INTEGRANTES}
        )


async def test_agrupacion_con_la_declaracion_aceptada_se_guarda() -> None:
    ana = usuario()
    repo = UsuariosFalsos(ana)
    guardado = await ActualizarPerfil(repo).ejecutar(
        ana.id, {"modalidad": "agrupacion", "integrantes": INTEGRANTES}
    )
    assert (guardado.modalidad, guardado.integrantes) == ("agrupacion", tuple(INTEGRANTES))


async def test_editar_el_domicilio_de_una_agrupacion_no_pide_la_declaracion() -> None:
    ana = usuario(modalidad="agrupacion", integrantes=tuple(INTEGRANTES))
    repo = UsuariosFalsos(ana)
    repo.textos_pendientes = [DECLARACION]
    guardado = await ActualizarPerfil(repo).ejecutar(ana.id, {"domicilio": "Av. Lima 1"})
    assert guardado.domicilio == "Av. Lima 1"


async def test_volver_a_individual_vacia_los_integrantes() -> None:
    ana = usuario(modalidad="agrupacion", integrantes=tuple(INTEGRANTES))
    guardado = await ActualizarPerfil(UsuariosFalsos(ana)).ejecutar(
        ana.id, {"modalidad": "individual"}
    )
    assert (guardado.modalidad, guardado.integrantes) == ("individual", ())


async def test_el_perfil_trae_pendientes_consentimientos_y_si_puede_reservar() -> None:
    ana = usuario()
    repo = UsuariosFalsos(ana)
    repo.textos_pendientes = [DECLARACION]
    repo.faltantes = ["documento"]
    repo.activos = {"fotos_videos"}
    perfil = await ArmarPerfil(repo).ejecutar(ana)
    assert perfil.pendientes == (DECLARACION,)
    assert perfil.datos_para_reservar is False
    assert perfil.consentimientos == {
        "promociones_correo": False,
        "promociones_whatsapp": False,
        "fotos_videos": True,
        "excluir_material": False,
    }
    repo.faltantes = []
    assert (await ArmarPerfil(repo).ejecutar(ana)).datos_para_reservar is True


async def test_los_consentimientos_solo_registran_lo_que_cambia() -> None:
    ana = usuario(telefono="987654321")
    repo = UsuariosFalsos(ana)
    repo.activos = {"fotos_videos"}
    finales = await ActualizarConsentimientos(repo).ejecutar(
        ana.id, {"fotos_videos": True, "promociones_correo": True, "excluir_material": False}
    )
    assert repo.cambios_de_consentimiento == [("promociones_correo", True)]
    assert finales["fotos_videos"] and finales["promociones_correo"]
    await ActualizarConsentimientos(repo).ejecutar(ana.id, {"fotos_videos": False})
    assert repo.cambios_de_consentimiento[-1] == ("fotos_videos", False)


async def test_whatsapp_sin_telefono_es_telefono_requerido_y_no_registra() -> None:
    ana = usuario()
    repo = UsuariosFalsos(ana)
    with pytest.raises(TelefonoRequerido):
        await ActualizarConsentimientos(repo).ejecutar(ana.id, {"promociones_whatsapp": True})
    assert repo.cambios_de_consentimiento == []


async def test_el_filtro_de_documento_repetido_lo_pasa_al_repositorio() -> None:
    admin = usuario(Rol.ADMINISTRADOR)
    repetido = usuario(documento_repetido=True)
    limpio = usuario()
    repo = UsuariosFalsos(admin, repetido, limpio)
    assert await ListarUsuarios(repo).ejecutar(admin.id, None, True) == [repetido]
