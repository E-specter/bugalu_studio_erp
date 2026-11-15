from uuid import UUID

from bugalu.compartido.errores import SinPermiso
from bugalu.modulos.identidad.dominio.puertos import RepositorioUsuarios
from bugalu.modulos.identidad.dominio.usuario import Rol


async def exigir_administrador(usuarios: RepositorioUsuarios, id_actor: UUID) -> None:
    actor = await usuarios.obtener_por_id(id_actor)
    if actor is None or actor.rol is not Rol.ADMINISTRADOR:
        raise SinPermiso("Solo un administrador puede hacer esto.")
