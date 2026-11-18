import logging
from uuid import UUID, uuid4

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


class ReemplazarFoto:
    def __init__(self, repo: RepositorioAsesorias, almacen: AlmacenFotos) -> None:
        self._repo = repo
        self._almacen = almacen

    async def ejecutar(self, id_actor: UUID, id_profesional: UUID, contenido: bytes) -> str:
        """Sube la foto nueva (validada por su contenido), guarda su ruta y borra la anterior."""
        perfil = await self._repo.obtener_profesional(id_profesional)
        if perfil is None:
            raise NoEncontrado("No existe el profesional.")
        await exigir_gestion(self._repo, id_actor, id_profesional)
        if len(contenido) > LIMITE_BYTES:
            raise ArchivoMuyGrande("La foto pesa mas de 2 MB.")
        tipo = detectar_tipo(contenido[:BYTES_FIRMA])
        if tipo is None:
            raise FormatoNoAdmitido("La foto debe ser JPG, PNG o WebP.", {"campo": "archivo"})
        ruta = f"{id_profesional}/{uuid4().hex}.{tipo.extension}"
        await self._almacen.subir(ruta, contenido, tipo.mime)
        try:
            await self._repo.fijar_foto(id_profesional, ruta)
        except Exception:
            await self._borrar_sin_fallar(ruta)  # no deja un objeto huerfano
            raise
        if perfil.foto_ruta:
            await self._borrar_sin_fallar(perfil.foto_ruta)
        return ruta

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
