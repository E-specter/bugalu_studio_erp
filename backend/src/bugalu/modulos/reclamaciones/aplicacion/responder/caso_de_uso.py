from datetime import datetime
from uuid import UUID

from bugalu.compartido.errores import DatosInvalidos, NoEncontrado, SinPermiso, YaRespondida
from bugalu.modulos.reclamaciones.dominio.modelos import Hoja
from bugalu.modulos.reclamaciones.dominio.puertos import RepositorioHojas


class ResponderHoja:
    """Respuesta unica por el medio que pidio el consumidor (con carta: referencia y fecha)."""

    def __init__(self, hojas: RepositorioHojas) -> None:
        self._hojas = hojas

    async def ejecutar(
        self, id_: UUID, texto: str, referencia: str | None, enviada_en: datetime | None
    ) -> Hoja:
        if not await self._hojas.es_administrador():
            raise SinPermiso("Solo el Administrador responde.")
        hoja = await self._hojas.obtener(id_)
        if hoja is None:
            raise NoEncontrado("No existe esa hoja.")
        if hoja.respuesta is not None:
            raise YaRespondida("Esa hoja ya tiene respuesta.")
        referencia = (referencia or "").strip() or None
        if hoja.contenido.medio_respuesta == "carta":
            if referencia is None:
                raise DatosInvalidos("Falta la referencia.", {"campo": "referencia_carta"})
            if enviada_en is None:
                raise DatosInvalidos("Falta la fecha de envio.", {"campo": "enviada_en"})
        await self._hojas.responder(id_, texto, referencia, enviada_en)
        respondida = await self._hojas.obtener(id_)
        assert respondida is not None  # el administrador lee lo que acaba de responder
        return respondida
