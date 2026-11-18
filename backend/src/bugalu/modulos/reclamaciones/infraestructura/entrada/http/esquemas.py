import re
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationInfo,
    field_validator,
)

from bugalu.compartido.esquemas import TextoCorto
from bugalu.modulos.reclamaciones.dominio.modelos import (
    Bien,
    Consumidor,
    Contenido,
    Hoja,
    HojaResumen,
    Representante,
)

# Mismo criterio que `compartido.esquemas.TextoLargo` (sin NUL ni controles; admite saltos de linea)
# pero con los largos de la hoja.
_SIN_CONTROLES = r"^[^\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\x{2028}\x{2029}]+$"


def _saltos(valor: str) -> str:
    return valor.replace("\r\n", "\n").replace("\r", "\n")


def _constraints(minimo: int, maximo: int) -> StringConstraints:
    return StringConstraints(
        strip_whitespace=True, min_length=minimo, max_length=maximo, pattern=_SIN_CONTROLES
    )


def _vacio_a_none(valor: Any) -> Any:
    return None if isinstance(valor, str) and not valor.strip() else valor


Detalle = Annotated[str, _constraints(10, 3000), AfterValidator(_saltos)]  # detalle y pedido
TextoRespuesta = Annotated[str, _constraints(10, 5000), AfterValidator(_saltos)]
Descripcion = Annotated[
    Annotated[str, _constraints(1, 1000), AfterValidator(_saltos)] | None,
    BeforeValidator(_vacio_a_none),
]
Telefono = Annotated[
    Annotated[
        str,
        StringConstraints(
            strip_whitespace=True, min_length=1, max_length=20, pattern=r"^[^\x00-\x1f\x7f-\x9f]+$"
        ),
    ]
    | None,
    BeforeValidator(_vacio_a_none),
]
Correo = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        max_length=254,
        pattern=r"^[^@\s\x00-\x1f]+@[^@\s\x00-\x1f]+\.[^@\s\x00-\x1f]+$",
    ),
]
Monto = Annotated[
    Decimal | None,
    BeforeValidator(_vacio_a_none),
    Field(ge=Decimal("0.01"), le=Decimal("999999.99"), max_digits=8, decimal_places=2),
]
_NUMERO = {
    "dni": re.compile(r"[0-9]{8}"),
    "ce": re.compile(r"[A-Z0-9]{6,12}"),
    "pasaporte": re.compile(r"[A-Z0-9]{6,12}"),
}  # las reglas de RF-17
PROVEEDOR = {
    "razon_social": "Aural Perú E.I.R.L.",
    "ruc": "20615656128",
    "domicilio": "Av. Javier Prado Este 5920, La Molina, Lima",
}


class _Cuerpo(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConsumidorEntrada(_Cuerpo):
    nombre: TextoCorto
    tipo_documento: Literal["dni", "ce", "pasaporte"]
    documento: str
    domicilio: TextoCorto
    telefono: Telefono = None
    correo: Correo

    @field_validator("documento")
    @classmethod
    def _formato(cls, valor: str, info: ValidationInfo) -> str:
        numero = "".join(valor.split()).upper()
        patron = _NUMERO.get(info.data.get("tipo_documento", ""))
        if patron is not None and not patron.fullmatch(numero):
            raise ValueError("Numero de documento invalido.")
        return numero


class RepresentanteEntrada(_Cuerpo):
    nombre: TextoCorto
    domicilio: TextoCorto
    telefono: Telefono = None
    correo: Correo


class BienEntrada(_Cuerpo):
    tipo: Literal["producto", "servicio"]
    monto: Monto = None
    descripcion: Descripcion = None


class _HojaBase(_Cuerpo):
    confirmado: bool = False  # el caso de uso exige `true` (409 `confirmacion_requerida`)
    consumidor: ConsumidorEntrada
    es_menor: bool = False
    representante: RepresentanteEntrada | None = Field(default=None, validate_default=True)
    bien: BienEntrada
    detalle: Detalle
    pedido: Detalle
    medio_respuesta: Literal["correo", "carta"]
    clave_envio: UUID | None = None  # la genera el formulario y la reutiliza en los reintentos
    sitio_web: str | None = None  # campo trampa: con valor, la hoja se registra para revisar

    @field_validator("representante")
    @classmethod
    def _representante(
        cls, valor: RepresentanteEntrada | None, info: ValidationInfo
    ) -> RepresentanteEntrada | None:
        if not info.data.get("es_menor"):
            return None  # solo se guardan los datos del Anexo I que corresponden
        if valor is None:
            raise ValueError("Un menor de edad exige los datos de su representante.")
        return valor

    @property
    def campo_trampa(self) -> bool:
        return bool((self.sitio_web or "").strip())

    def a_dominio(self, tipo: str | None) -> Contenido:
        c, b, r = self.consumidor, self.bien, self.representante
        return Contenido(
            Consumidor(c.nombre, c.tipo_documento, c.documento, c.domicilio, c.telefono, c.correo),
            self.es_menor,
            Representante(r.nombre, r.domicilio, r.telefono, r.correo) if r else None,
            Bien(b.tipo, b.monto, b.descripcion),
            tipo,
            self.detalle,
            self.pedido,
            self.medio_respuesta,
        )


class NuevaHojaEntrada(_HojaBase):
    tipo: Literal["reclamo", "queja"]  # obligatorio en el formulario publico


class NuevaTranscripcionEntrada(_HojaBase):
    tipo: Literal["reclamo", "queja"] | None = None  # la hoja fisica puede no traerlo marcado
    fecha_original: AwareDatetime
    numero_hoja_fisica: TextoCorto = Field(max_length=50)


class RespuestaEntrada(_Cuerpo):
    texto: TextoRespuesta
    referencia_carta: Annotated[TextoCorto | None, BeforeValidator(_vacio_a_none)] = None
    enviada_en: AwareDatetime | None = None


# --- salida --------------------------------------------------------------------------------------


class ProveedorSalida(BaseModel):
    razon_social: str
    ruc: str
    domicilio: str


class ConsumidorSalida(BaseModel):
    nombre: str
    tipo_documento: str
    documento: str
    domicilio: str
    telefono: str | None
    correo: str


class RepresentanteSalida(BaseModel):
    nombre: str
    domicilio: str
    telefono: str | None
    correo: str


class BienSalida(BaseModel):
    tipo: str
    monto: str | None
    descripcion: str | None


class AdjuntoSalida(BaseModel):
    n: int
    nombre: str
    tipo: str
    tamano: int


class AutorSalida(BaseModel):
    id: UUID
    nombre: str | None


class RespuestaSalida(BaseModel):
    texto: str
    medio: str
    referencia_carta: str | None
    enviada_en: datetime
    respondida_por: AutorSalida | None = None  # solo para el Administrador


class HojaSalida(BaseModel):
    id: UUID
    numero: str
    creada_en: datetime
    vence_respuesta: datetime
    proveedor: ProveedorSalida
    consumidor: ConsumidorSalida
    es_menor: bool
    representante: RepresentanteSalida | None
    bien: BienSalida
    tipo: str | None
    detalle: str
    pedido: str
    medio_respuesta: str
    adjuntos: list[AdjuntoSalida]
    origen: str
    fecha_original: datetime | None
    numero_hoja_fisica: str | None
    estado: str
    respuesta: RespuestaSalida | None
    dias_habiles_restantes: int | None
    revisar_spam: bool | None  # solo para el Administrador
    en_tu_cuenta: bool  # vinculada a la cuenta del token de esta peticion
    adjuntos_no_guardados: list[int] = []  # solo en el alta: posiciones que no se pudieron guardar

    @classmethod
    def desde_dominio(
        cls, h: Hoja, solicitante: UUID | None = None, no_guardados: list[int] | None = None
    ) -> HojaSalida:
        c = h.contenido
        r = h.respuesta
        autor = r.respondida_por if r else None
        return cls(
            id=h.id,
            numero=h.numero,
            creada_en=h.creada_en,
            vence_respuesta=h.vence_respuesta,
            proveedor=ProveedorSalida(**PROVEEDOR),
            consumidor=ConsumidorSalida(**vars(c.consumidor)),
            es_menor=c.es_menor,
            representante=RepresentanteSalida(**vars(c.representante)) if c.representante else None,
            bien=BienSalida(
                tipo=c.bien.tipo,
                monto=f"{c.bien.monto:.2f}" if c.bien.monto is not None else None,
                descripcion=c.bien.descripcion,
            ),
            tipo=c.tipo,
            detalle=c.detalle,
            pedido=c.pedido,
            medio_respuesta=c.medio_respuesta,
            adjuntos=[
                AdjuntoSalida(n=a.n, nombre=a.nombre, tipo=a.tipo, tamano=a.tamano)
                for a in h.adjuntos
            ],
            origen=h.origen,
            fecha_original=h.fecha_original,
            numero_hoja_fisica=h.numero_hoja_fisica,
            estado=h.estado,
            respuesta=RespuestaSalida(
                texto=r.texto,
                medio=r.medio,
                referencia_carta=r.referencia_carta,
                enviada_en=r.enviada_en,
                respondida_por=AutorSalida(id=autor.id, nombre=autor.nombre) if autor else None,
            )
            if r
            else None,
            dias_habiles_restantes=h.dias_habiles_restantes,
            revisar_spam=h.revisar_spam,
            en_tu_cuenta=solicitante is not None and h.id_cuenta == solicitante,
            adjuntos_no_guardados=no_guardados or [],
        )


class NombreSalida(BaseModel):
    nombre: str


class HojaResumenSalida(BaseModel):
    id: UUID
    numero: str
    creada_en: datetime
    tipo: str | None
    estado: str
    vence_respuesta: datetime
    consumidor: NombreSalida
    dias_habiles_restantes: int | None
    revisar_spam: bool | None
    origen: str

    @classmethod
    def desde_dominio(cls, h: HojaResumen) -> HojaResumenSalida:
        return cls(
            id=h.id,
            numero=h.numero,
            creada_en=h.creada_en,
            tipo=h.tipo,
            estado=h.estado,
            vence_respuesta=h.vence_respuesta,
            consumidor=NombreSalida(nombre=h.nombre),
            dias_habiles_restantes=h.dias_habiles_restantes,
            revisar_spam=h.revisar_spam,
            origen=h.origen,
        )


class AdjuntoFirmado(BaseModel):
    url: str
    expira_en: datetime
