from bugalu.modulos.identidad.dominio.puertos import RepositorioUsuarios
from bugalu.modulos.identidad.dominio.usuario import PerfilCompleto, Usuario


class ArmarPerfil:
    """El perfil propio con lo que la app necesita para decidir el siguiente paso (RF-17)."""

    def __init__(self, usuarios: RepositorioUsuarios) -> None:
        self._usuarios = usuarios

    async def ejecutar(self, usuario: Usuario) -> PerfilCompleto:
        return PerfilCompleto(
            usuario=usuario,
            consentimientos=await self._usuarios.consentimientos(usuario.id),
            pendientes=tuple(await self._usuarios.pendientes()),
            datos_para_reservar=not await self._usuarios.campos_faltantes_para_reservar(),
        )
