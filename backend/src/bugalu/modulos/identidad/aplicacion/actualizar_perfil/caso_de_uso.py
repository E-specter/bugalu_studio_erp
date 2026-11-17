from collections.abc import Mapping
from typing import Any
from uuid import UUID

from bugalu.compartido.errores import DeclaracionRequerida
from bugalu.modulos.identidad.aplicacion.obtener_perfil.caso_de_uso import PerfilNoEncontrado
from bugalu.modulos.identidad.dominio.puertos import RepositorioUsuarios
from bugalu.modulos.identidad.dominio.reglas import exige_declaracion, validar_cambios_de_perfil
from bugalu.modulos.identidad.dominio.usuario import Usuario


class ActualizarPerfil:
    def __init__(self, usuarios: RepositorioUsuarios) -> None:
        self._usuarios = usuarios

    async def ejecutar(self, id_usuario: UUID, cambios: Mapping[str, Any]) -> Usuario:
        usuario = await self._usuarios.obtener_por_id(id_usuario)
        if usuario is None:
            raise PerfilNoEncontrado
        validar_cambios_de_perfil(usuario, cambios)
        if not cambios:
            return usuario
        cambios = dict(cambios)
        if cambios.get("modalidad") == "individual":
            cambios.setdefault("integrantes", [])  # una cuenta individual no lleva integrantes
        actualizado = await self._usuarios.actualizar_perfil(id_usuario, cambios)
        if exige_declaracion(usuario, cambios):
            # Con el cambio ya aplicado en la transaccion: si la declaracion vigente no esta
            # aceptada, el error la deshace.
            pendientes = await self._usuarios.pendientes()
            if any(p.tipo == "declaracion_agrupacion" for p in pendientes):
                raise DeclaracionRequerida("Acepta la declaracion de agrupacion para registrarla.")
        return actualizado
