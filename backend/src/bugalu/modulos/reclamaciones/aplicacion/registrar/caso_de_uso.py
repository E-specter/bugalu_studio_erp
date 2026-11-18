from datetime import datetime
from uuid import UUID, uuid4

from bugalu.compartido.errores import ConfirmacionDeHojaRequerida, SinPermiso
from bugalu.modulos.reclamaciones.dominio.adjuntos import validar_adjuntos
from bugalu.modulos.reclamaciones.dominio.modelos import Adjunto, Contenido, Hoja, NuevaHoja
from bugalu.modulos.reclamaciones.dominio.puertos import AlmacenAdjuntos, RepositorioHojas


async def _alta(
    repo: RepositorioHojas,
    almacen: AlmacenAdjuntos,
    nueva: NuevaHoja,
    transcribir: bool,
    ip: str | None,
    id_cuenta: UUID | None = None,
) -> tuple[Hoja, bool]:
    """Insertar (valida todo y aplica el limite) -> subir -> confirmar al cerrar la transaccion:
    si falla un adjunto, el error sale y la transaccion deshace la hoja."""
    id_ = uuid4()
    alta = await (repo.transcribir(id_, nueva) if transcribir else repo.registrar(id_, nueva, ip))
    if alta.existente is not None:  # reintento: nada nuevo que subir ni avisar
        return alta.existente, False
    adjuntos = []
    for a in nueva.adjuntos:
        ruta = f"{id_}/{a.n}.{a.extension}"
        await almacen.subir(ruta, a.contenido, a.tipo)
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
    return hoja, True


class RegistrarHoja:
    def __init__(self, hojas: RepositorioHojas, almacen: AlmacenAdjuntos) -> None:
        self._hojas = hojas
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
    ) -> tuple[Hoja, bool]:
        """Devuelve la hoja y si se creo ahora (False: reintento con la misma clave)."""
        if not confirmado:
            raise ConfirmacionDeHojaRequerida
        nueva = NuevaHoja(
            contenido,
            validar_adjuntos(archivos),
            revisar_spam=campo_trampa,
            clave_envio=clave_envio,
        )
        return await _alta(self._hojas, self._almacen, nueva, False, ip, id_cuenta)


class TranscribirHoja:
    def __init__(self, hojas: RepositorioHojas, almacen: AlmacenAdjuntos) -> None:
        self._hojas = hojas
        self._almacen = almacen

    async def ejecutar(
        self,
        contenido: Contenido,
        confirmado: bool,
        archivos: list[tuple[str, bytes]],
        fecha_original: datetime,
        numero_hoja_fisica: str,
    ) -> Hoja:
        if not await self._hojas.es_administrador():
            raise SinPermiso("Solo el Administrador transcribe hojas.")
        if not confirmado:
            raise ConfirmacionDeHojaRequerida
        nueva = NuevaHoja(
            contenido, validar_adjuntos(archivos), False, fecha_original, numero_hoja_fisica
        )
        return (await _alta(self._hojas, self._almacen, nueva, True, None))[0]
