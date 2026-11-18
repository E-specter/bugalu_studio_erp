from uuid import UUID

from bugalu.compartido.errores import SinPermiso
from bugalu.modulos.asesorias.dominio.puertos import RepositorioAsesorias


async def exigir_administrador(repo: RepositorioAsesorias) -> None:
    if not await repo.es_administrador():
        raise SinPermiso("Solo un administrador puede hacer esto.")


async def exigir_gestion(repo: RepositorioAsesorias, id_actor: UUID, id_profesional: UUID) -> None:
    """El propio profesional o el administrador (la base lo vuelve a exigir)."""
    if id_actor != id_profesional and not await repo.es_administrador():
        raise SinPermiso("Solo el propio profesional o un administrador puede hacer esto.")
