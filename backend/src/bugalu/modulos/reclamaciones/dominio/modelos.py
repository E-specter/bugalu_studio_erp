"""Hoja de reclamacion (Anexo I del D.S. 101-2022-PCM): datos del consumidor, bien, detalle y respuesta."""

# ruff: noqa: E501 - SQL y textos literales largos

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class Consumidor:
    nombre: str
    tipo_documento: str  # dni | ce | pasaporte
    documento: str
    domicilio: str
    telefono: str | None
    correo: str


@dataclass(frozen=True)
class Representante:
    nombre: str
    domicilio: str
    telefono: str | None
    correo: str


@dataclass(frozen=True)
class Bien:
    tipo: str  # producto | servicio
    monto: Decimal | None
    descripcion: str | None


@dataclass(frozen=True)
class Contenido:
    consumidor: Consumidor
    es_menor: bool
    representante: Representante | None
    bien: Bien
    tipo: str | None  # reclamo | queja | None (solo transcritas sin marcar)
    detalle: str
    pedido: str
    medio_respuesta: str  # correo | carta


@dataclass(frozen=True)
class AdjuntoNuevo:
    n: int
    nombre: str
    tipo: str  # mime verificado por contenido
    tamano: int
    contenido: bytes
    extension: str


@dataclass(frozen=True)
class NuevaHoja:
    contenido: Contenido
    adjuntos: list[AdjuntoNuevo]
    revisar_spam: bool = False
    fecha_original: datetime | None = None  # solo transcripciones
    numero_hoja_fisica: str | None = None
    clave_envio: UUID | None = None


@dataclass(frozen=True)
class Adjunto:
    n: int
    nombre: str
    tipo: str
    tamano: int
    ruta: str


@dataclass(frozen=True)
class Autor:
    id: UUID
    nombre: str | None


@dataclass(frozen=True)
class Respuesta:
    texto: str
    medio: str
    referencia_carta: str | None
    enviada_en: datetime
    respondida_por: Autor | None
    respondida_en: datetime | None = None  # cuando se registro (con carta, enviada_en es otra)


@dataclass(frozen=True)
class Hoja:
    id: UUID
    numero: str
    creada_en: datetime
    vence_respuesta: datetime
    contenido: Contenido
    adjuntos: list[Adjunto]
    origen: str  # web | libro_fisico
    fecha_original: datetime | None
    numero_hoja_fisica: str | None
    respuesta: Respuesta | None
    dias_habiles_restantes: int | None  # None si ya esta respondida
    revisar_spam: bool | None  # solo lo ve el administrador
    id_cuenta: UUID | None = None  # la cuenta a la que esta vinculada (no se expone)

    @property
    def estado(self) -> str:
        return "pendiente" if self.respuesta is None else "respondida"


@dataclass(frozen=True)
class Alta:
    """Lo que la base calcula al registrar: la hoja no se relee (anon no la puede leer)."""

    numero: str
    creada_en: datetime
    vence_respuesta: datetime
    dias_habiles_restantes: int
    existente: Hoja | None = None  # reintento con la misma clave de envio: la hoja ya registrada
    subidas: dict[int, str] = field(
        default_factory=dict
    )  # n del adjunto -> ruta que genero la base


@dataclass(frozen=True)
class Registro:
    """Resultado del alta: la hoja siempre queda; los adjuntos que no se guardaron se informan."""

    hoja: Hoja
    creada: bool  # False: reintento con la misma clave de envio
    no_guardados: list[int]  # posiciones (desde 1) de los adjuntos que no se pudieron guardar


@dataclass(frozen=True)
class HojaResumen:
    id: UUID
    numero: str
    creada_en: datetime
    tipo: str | None
    estado: str
    vence_respuesta: datetime
    nombre: str
    dias_habiles_restantes: int | None
    revisar_spam: bool | None
    origen: str = "web"  # web | libro_fisico
