import logging
from dataclasses import dataclass
from uuid import UUID

from bugalu.compartido.errores import (
    AlmacenamientoNoDisponible,
    ArchivoMuyGrande,
    FormatoNoAdmitido,
    NoEncontrado,
)
from bugalu.modulos.asesorias.aplicacion.permisos import exigir_gestion
from bugalu.modulos.asesorias.dominio.foto import BYTES_FIRMA, LIMITE_BYTES, detectar_tipo
from bugalu.modulos.asesorias.dominio.puertos import AlmacenFotos, RepositorioAsesorias

_registro = logging.getLogger(__name__)


@dataclass(frozen=True)
class FotoReemplazada:
    nueva: str
    anterior: str | None


class ReemplazarFoto:
    def __init__(self, repo: RepositorioAsesorias, almacen: AlmacenFotos) -> None:
        self._repo = repo
        self._almacen = almacen

    async def ejecutar(
        self, id_actor: UUID, id_profesional: UUID, contenido: bytes
    ) -> FotoReemplazada:
        """Sube la foto nueva (validada por su contenido) a la ruta libre y guarda su ruta.

        La anterior sigue en el almacenamiento hasta que el llamador confirme la transaccion y
        llame a `confirmar`; si la base falla, `descartar` borra la nueva y la anterior sigue.
        """
        perfil = await self._repo.obtener_profesional(id_profesional)
        if perfil is None:
            raise NoEncontrado("No existe el profesional.")
        await exigir_gestion(self._repo, id_actor, id_profesional)
        if len(contenido) > LIMITE_BYTES:
            raise ArchivoMuyGrande("La foto pesa mas de 2 MB.")
        tipo = detectar_tipo(contenido[:BYTES_FIRMA])
        if tipo is None:
            raise FormatoNoAdmitido("La foto debe ser JPG, PNG o WebP.", {"campo": "archivo"})
        # Storage solo admite estas dos rutas por perfil: se alterna para no pisar la vigente.
        ruta = f"{id_profesional}/foto-{2 if (perfil.foto_ruta or '').endswith('/foto-1') else 1}"
        await self._almacen.subir(ruta, contenido, tipo.mime)
        reemplazo = FotoReemplazada(ruta, perfil.foto_ruta)
        try:
            await self._repo.fijar_foto(id_profesional, ruta)
        except Exception:
            await self.descartar(reemplazo)  # no deja un objeto huerfano
            raise
        return reemplazo

    async def confirmar(self, reemplazo: FotoReemplazada) -> None:
        """Tras el commit: borra la foto anterior."""
        if reemplazo.anterior:
            await self._borrar_sin_fallar(reemplazo.anterior)

    async def descartar(self, reemplazo: FotoReemplazada) -> None:
        """La base no guardo la ruta nueva: se borra la subida y la anterior sigue."""
        await self._borrar_sin_fallar(reemplazo.nueva)

    async def _borrar_sin_fallar(self, ruta: str) -> None:
        try:
            await self._almacen.borrar(ruta)
        except AlmacenamientoNoDisponible:
            _registro.warning("Foto sin borrar del almacenamiento: %s", ruta)


class QuitarFoto:
    def __init__(self, repo: RepositorioAsesorias, almacen: AlmacenFotos) -> None:
        self._repo = repo
        self._almacen = almacen

    async def ejecutar(self, id_actor: UUID, id_profesional: UUID) -> None:
        """Estricto: si el almacenamiento falla, el llamador revierte la base y responde 503."""
        perfil = await self._repo.obtener_profesional(id_profesional)
        if perfil is None:
            raise NoEncontrado("No existe el profesional.")
        await exigir_gestion(self._repo, id_actor, id_profesional)
        await self._repo.fijar_foto(id_profesional, None)
        if perfil.foto_ruta:
            await self._almacen.borrar(perfil.foto_ruta)
