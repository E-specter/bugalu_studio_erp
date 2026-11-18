from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from bugalu.compartido.errores import AlmacenamientoNoDisponible
from bugalu.modulos.reclamaciones.dominio.modelos import (
    Adjunto,
    Alta,
    Autor,
    Bien,
    Consumidor,
    Contenido,
    Hoja,
    HojaResumen,
    NuevaHoja,
    Respuesta,
)

AHORA = datetime(2026, 11, 17, 15, 0, tzinfo=UTC)


def contenido(medio: str = "correo", tipo: str | None = "reclamo") -> Contenido:
    return Contenido(
        Consumidor("Ana Prueba", "dni", "12345678", "Av. Lima 123", None, "ana@t.pe"),
        False,
        None,
        Bien("servicio", Decimal("50.00"), None),
        tipo,
        "El servicio no fue el pactado.",
        "Quiero la devolucion.",
        medio,
    )


def hoja(id_: UUID | None = None, medio: str = "correo", **cambios: object) -> Hoja:
    base = Hoja(
        id_ or uuid4(),
        "000000001-2026",
        AHORA,
        AHORA + timedelta(days=21),
        contenido(medio),
        [],
        "web",
        None,
        None,
        None,
        15,
        False,
    )
    return replace(base, **cambios)  # type: ignore[arg-type]


class AlmacenFalso:
    def __init__(self, falla_en: int | None = None, eventos: list[str] | None = None) -> None:
        self.subidos: list[tuple[str, int, str]] = []
        self.borrados: list[str] = []
        self.falla_borrar: set[str] = set()
        self.falla_en = falla_en
        self.intentos = 0
        self.eventos = eventos if eventos is not None else []

    async def subir(self, ruta: str, contenido: bytes, mime: str) -> None:
        self.intentos += 1
        if self.falla_en == self.intentos:
            raise AlmacenamientoNoDisponible("no")
        self.eventos.append(f"subir:{ruta}")
        self.subidos.append((ruta, len(contenido), mime))

    async def borrar(self, ruta: str) -> None:
        if ruta in self.falla_borrar:
            raise AlmacenamientoNoDisponible("no")
        self.borrados.append(ruta)

    async def firmar(self, ruta: str, segundos: int) -> str:
        return f"http://firmada/{ruta}?s={segundos}"


class HojasFalso:
    def __init__(self, administrador: bool = False) -> None:
        self.administrador = administrador
        self.hojas: dict[UUID, Hoja] = {}
        self.ocultas: set[UUID] = set()
        self.eventos: list[str] = []
        self.ultima_alta: tuple[UUID, NuevaHoja, str | None] | None = None
        self.consultas: list[tuple[str | None, date | None, date | None]] = []
        self.existente: Hoja | None = None
        self.falla_confirmar_en: int | None = None  # la n-esima confirmacion falla...
        self.fallas_confirmar = 1  # ...y tantas seguidas como diga esto
        self.confirmaciones = 0
        self.no_guardados_previos: list[int] = []  # lo que informa un reintento
        self.huerfanas: list[str] = []

    async def es_administrador(self) -> bool:
        return self.administrador

    async def registrar(self, id_: UUID, nueva: NuevaHoja, ip: str | None) -> Alta:
        self.eventos.append("registrar")
        self.ultima_alta = (id_, nueva, ip)
        return Alta(
            "000000007-2026",
            AHORA,
            AHORA + timedelta(days=21),
            15,
            self.existente,
            self._subidas(id_, nueva),
            self.no_guardados_previos,
        )

    async def transcribir(self, id_: UUID, nueva: NuevaHoja) -> Alta:
        self.eventos.append("transcribir")
        self.ultima_alta = (id_, nueva, None)
        return Alta(
            "000000008-2026", AHORA, AHORA + timedelta(days=21), 15, None, self._subidas(id_, nueva)
        )

    @staticmethod
    def _subidas(id_: UUID, nueva: NuevaHoja) -> dict[int, str]:
        return {a.n: f"{id_}/{uuid4()}.{a.extension}" for a in nueva.adjuntos}

    async def confirmar_adjunto(self, ruta: str) -> None:
        self.confirmaciones += 1
        en = self.falla_confirmar_en
        if en is not None and en <= self.confirmaciones < en + self.fallas_confirmar:
            raise AlmacenamientoNoDisponible("no se pudo confirmar")
        self.eventos.append(f"confirmar:{ruta}")

    async def avisar_hoja(self, id_: UUID) -> None:
        self.eventos.append(f"avisar:{id_}")

    async def rutas_huerfanas(self) -> list[str]:
        return self.huerfanas

    async def obtener(self, id_: UUID) -> Hoja | None:
        return None if id_ in self.ocultas else self.hojas.get(id_)

    async def listar_mias(self) -> list[HojaResumen]:
        return [self._resumen(h) for h in self.hojas.values()]

    async def listar(
        self, estado: str | None, desde: date | None, hasta: date | None
    ) -> list[HojaResumen]:
        self.consultas.append((estado, desde, hasta))
        return [self._resumen(h) for h in self.hojas.values()]

    async def responder(
        self, id_: UUID, texto: str, referencia: str | None, enviada_en: datetime | None
    ) -> None:
        self.eventos.append("responder")
        h = self.hojas[id_]
        autor = Autor(uuid4(), "Admin")
        respuesta = Respuesta(texto, h.contenido.medio_respuesta, referencia, AHORA, autor)
        self.hojas[id_] = replace(h, respuesta=respuesta)

    async def exportar(self, desde: date, hasta: date) -> list[Hoja]:
        self.consultas.append((None, desde, hasta))
        return list(self.hojas.values())

    @staticmethod
    def _resumen(h: Hoja) -> HojaResumen:
        return HojaResumen(
            h.id,
            h.numero,
            h.creada_en,
            h.contenido.tipo,
            h.estado,
            h.vence_respuesta,
            h.contenido.consumidor.nombre,
            h.dias_habiles_restantes,
            h.revisar_spam,
        )


def adjunto(n: int = 1) -> Adjunto:
    return Adjunto(n, "foto.png", "image/png", 10, f"x/{n}.png")


def abridor(repo: HojasFalso) -> Callable[[], AbstractAsyncContextManager[HojasFalso]]:
    """Una transaccion falsa: deja constancia de cuando se abre y cuando se cierra (commit)."""

    @asynccontextmanager
    async def abrir() -> AsyncIterator[HojasFalso]:
        repo.eventos.append("abre")
        yield repo
        repo.eventos.append("cierra")

    return abrir
