import logging
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from bugalu.compartido.errores import ConfirmacionDeHojaRequerida, SinPermiso
from bugalu.modulos.reclamaciones.dominio.adjuntos import validar_adjuntos
from bugalu.modulos.reclamaciones.dominio.fechas import validar_fecha_original
from bugalu.modulos.reclamaciones.dominio.modelos import (
    Adjunto,
    Contenido,
    Hoja,
    NuevaHoja,
    Registro,
)
from bugalu.modulos.reclamaciones.dominio.puertos import AbrirRepositorio, AlmacenAdjuntos

_registro = logging.getLogger(__name__)


async def _alta(
    abrir: AbrirRepositorio,
    abrir_publico: AbrirRepositorio,
    almacen: AlmacenAdjuntos,
    nueva: NuevaHoja,
    transcribir: bool,
    ip: str | None,
    id_cuenta: UUID | None = None,
) -> Registro:
    """Registrar la hoja (valida todo, aplica el limite y deja una subida pendiente por adjunto) y
    cerrar esa transaccion: Storage solo deja subir a rutas con subida pendiente que ya sean
    visibles. Luego, por cada adjunto, subir y confirmar. Si uno falla, la hoja se conserva."""
    id_ = uuid4()
    async with abrir() as hojas:
        alta = await (
            hojas.transcribir(id_, nueva) if transcribir else hojas.registrar(id_, nueva, ip)
        )
    if alta.existente is not None:  # reintento: nada nuevo que subir ni avisar
        return Registro(alta.existente, False, [])
    adjuntos: list[Adjunto] = []
    no_guardados: list[int] = []
    for a in nueva.adjuntos:
        ruta = alta.subidas[a.n]
        try:
            await almacen.subir(ruta, a.contenido, a.tipo)
            async with abrir_publico() as hojas:
                await hojas.confirmar_adjunto(ruta)
        except Exception:  # la hoja ya esta registrada y avisada: no se pierde por un adjunto
            _registro.exception("El adjunto %s de la hoja %s no se guardo.", a.n, id_)
            no_guardados.append(a.n)
            continue
        adjuntos.append(Adjunto(a.n, a.nombre, a.tipo, a.tamano, ruta))
    hoja = Hoja(
        id=id_,
        numero=alta.numero,
        creada_en=alta.creada_en,
        vence_respuesta=alta.vence_respuesta,
        contenido=nueva.contenido,
        adjuntos=adjuntos,
        origen="libro_fisico" if transcribir else "web",
        fecha_original=nueva.fecha_original,
        numero_hoja_fisica=nueva.numero_hoja_fisica,
        respuesta=None,
        dias_habiles_restantes=alta.dias_habiles_restantes,
        revisar_spam=False if transcribir else None,  # el consumidor no ve la marca
        id_cuenta=id_cuenta,
    )
    return Registro(hoja, True, no_guardados)


class RegistrarHoja:
    def __init__(
        self, abrir: AbrirRepositorio, abrir_publico: AbrirRepositorio, almacen: AlmacenAdjuntos
    ) -> None:
        self._abrir = abrir
        self._abrir_publico = abrir_publico
        self._almacen = almacen

    async def ejecutar(
        self,
        contenido: Contenido,
        confirmado: bool,
        campo_trampa: bool,
        archivos: list[tuple[str, bytes]],
        ip: str | None,
        clave_envio: UUID | None = None,
        id_cuenta: UUID | None = None,
    ) -> Registro:
        if not confirmado:
            raise ConfirmacionDeHojaRequerida
        nueva = NuevaHoja(
            contenido,
            validar_adjuntos(archivos),
            revisar_spam=campo_trampa,
            clave_envio=clave_envio,
        )
        return await _alta(
            self._abrir, self._abrir_publico, self._almacen, nueva, False, ip, id_cuenta
        )


class TranscribirHoja:
    def __init__(
        self,
        abrir: AbrirRepositorio,
        abrir_publico: AbrirRepositorio,
        almacen: AlmacenAdjuntos,
        reloj: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._abrir = abrir
        self._abrir_publico = abrir_publico
        self._almacen = almacen
        self._reloj = reloj

    async def ejecutar(
        self,
        contenido: Contenido,
        confirmado: bool,
        archivos: list[tuple[str, bytes]],
        fecha_original: datetime,
        numero_hoja_fisica: str,
    ) -> Registro:
        async with self._abrir() as hojas:
            if not await hojas.es_administrador():
                raise SinPermiso("Solo el Administrador transcribe hojas.")
        if not confirmado:
            raise ConfirmacionDeHojaRequerida
        validar_fecha_original(fecha_original, self._reloj())
        nueva = NuevaHoja(
            contenido, validar_adjuntos(archivos), False, fecha_original, numero_hoja_fisica
        )
        return await _alta(self._abrir, self._abrir_publico, self._almacen, nueva, True, None)
