# ruff: noqa: E501 - SQL y textos literales largos
from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from psycopg import AsyncConnection, errors
from psycopg.types.json import Jsonb

from bugalu.compartido.errores import (
    DatosInvalidos,
    DemasiadasSolicitudes,
    NoEncontrado,
    SinPermiso,
    YaRespondida,
)
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
    Representante,
    Respuesta,
)

_LIMA = "(h.creada_en at time zone 'America/Lima')::date"
_HOJA = (
    "select h.id, h.numero, h.creada_en, h.vence_respuesta, h.nombre, h.tipo_documento, h.documento, "
    "h.domicilio, h.telefono, h.correo, h.es_menor, h.rep_nombre, h.rep_domicilio, h.rep_telefono, "
    "h.rep_correo, h.bien_tipo, h.monto, h.descripcion, h.tipo, h.detalle, h.pedido, "
    "h.medio_respuesta, h.origen, h.fecha_original, h.numero_hoja_fisica, h.revisar_spam, "
    "h.respuesta_texto, h.respuesta_referencia_carta, h.respuesta_enviada_en, h.respondida_en, "
    "h.respondida_por, u.nombre, "
    "case when h.respuesta_texto is null then public.dias_habiles_restantes(h.vence_respuesta) end, "
    "h.id_cuenta "
    "from public.hoja_reclamacion h left join public.usuario u on u.id = h.respondida_por "
)
_RESUMEN = (
    "select h.id, h.numero, h.creada_en, h.tipo, "
    "case when h.respuesta_texto is null then 'pendiente' else 'respondida' end, "
    "h.vence_respuesta, h.nombre, "
    "case when h.respuesta_texto is null then public.dias_habiles_restantes(h.vence_respuesta) end, "
    "h.revisar_spam, h.origen from public.hoja_reclamacion h "
)
# Pendientes primero y por plazo; las respondidas, la mas reciente antes.
_ORDEN_BANDEJA = (
    "order by (h.respuesta_texto is not null), "
    "case when h.respuesta_texto is null then h.vence_respuesta end, h.creada_en desc"
)


def _plano(c: Contenido) -> dict[str, Any]:
    """Campos planos que lee `crear_hoja`."""
    r = c.representante
    return {
        "nombre": c.consumidor.nombre,
        "tipo_documento": c.consumidor.tipo_documento,
        "documento": c.consumidor.documento,
        "domicilio": c.consumidor.domicilio,
        "telefono": c.consumidor.telefono,
        "correo": c.consumidor.correo,
        "es_menor": c.es_menor,
        "rep_nombre": r.nombre if r else None,
        "rep_domicilio": r.domicilio if r else None,
        "rep_telefono": r.telefono if r else None,
        "rep_correo": r.correo if r else None,
        "bien_tipo": c.bien.tipo,
        "monto": str(c.bien.monto) if c.bien.monto is not None else None,
        "descripcion": c.bien.descripcion,
        "tipo": c.tipo,
        "detalle": c.detalle,
        "pedido": c.pedido,
        "medio_respuesta": c.medio_respuesta,
    }


def _hoja(f: Sequence[Any], adjuntos: list[Adjunto]) -> Hoja:
    representante = Representante(f[11], f[12], f[13], f[14]) if f[10] else None
    contenido = Contenido(
        Consumidor(f[4], f[5], f[6], f[7], f[8], f[9]),
        f[10],
        representante,
        Bien(f[15], f[16], f[17]),
        f[18],
        f[19],
        f[20],
        f[21],
    )
    respuesta = None
    if f[26] is not None:
        autor = Autor(f[30], f[31]) if f[30] else None
        respuesta = Respuesta(f[26], f[21], f[27], f[28], autor, f[29])
    return Hoja(
        f[0],
        f[1],
        f[2],
        f[3],
        contenido,
        adjuntos,
        f[22],
        f[23],
        f[24],
        respuesta,
        f[32],
        f[25],
        f[33],
    )


def _hoja_registrada(d: dict[str, Any]) -> Hoja:
    """La hoja que devuelve `hoja_registrada_json` en un reintento (la ve quien la envio, sin marcas)."""
    rep = (
        Representante(d["rep_nombre"], d["rep_domicilio"], d["rep_telefono"], d["rep_correo"])
        if d["es_menor"]
        else None
    )
    contenido = Contenido(
        Consumidor(
            d["nombre"],
            d["tipo_documento"],
            d["documento"],
            d["domicilio"],
            d["telefono"],
            d["correo"],
        ),
        d["es_menor"],
        rep,
        Bien(
            d["bien_tipo"],
            Decimal(str(d["monto"])) if d["monto"] is not None else None,
            d["descripcion"],
        ),
        d["tipo"],
        d["detalle"],
        d["pedido"],
        d["medio_respuesta"],
    )
    adjuntos = [
        Adjunto(a["n"], a["nombre"], a["tipo"], a["tamano"], a["ruta"]) for a in d["adjuntos"]
    ]
    return Hoja(
        UUID(d["id"]), d["numero"], datetime.fromisoformat(d["creada_en"]),
        datetime.fromisoformat(d["vence_respuesta"]), contenido, adjuntos, "web", None, None, None,
        d["dias"], None, UUID(d["id_cuenta"]) if d["id_cuenta"] else None,
    )  # fmt: skip


class RepositorioHojasPostgres:
    """Recibe una transaccion con identidad (o `anon` en el alta): la RLS decide el acceso."""

    def __init__(self, conexion: AsyncConnection) -> None:
        self._conexion = conexion

    async def es_administrador(self) -> bool:
        cursor = await self._conexion.execute("select public.es_administrador()")
        return bool((await cursor.fetchone())[0])  # type: ignore[index]

    async def _alta(self, funcion: str, parametros: tuple[Any, ...]) -> Alta:
        marcadores = ", ".join(["%s"] * len(parametros))
        columnas = "r_numero, r_creada_en, r_vence, r_dias" + (
            ", r_repetida, r_existente" if funcion == "registrar_hoja" else ""
        )
        try:
            cursor = await self._conexion.execute(
                f"select {columnas} from public.{funcion}({marcadores})",  # noqa: S608
                parametros,
            )
        except errors.RaiseException as error:
            if error.diag.message_primary == "demasiadas_solicitudes":
                raise DemasiadasSolicitudes(
                    "Se registraron muchas hojas desde esta conexion. Intenta de nuevo en una hora."
                ) from None
            if error.diag.message_primary == "fecha_original_invalida":
                raise DatosInvalidos(
                    "La fecha original no puede ser futura.", {"campo": "fecha_original"}
                ) from None
            raise
        except errors.InsufficientPrivilege:
            raise SinPermiso("Solo el Administrador transcribe hojas.") from None
        except errors.CheckViolation:
            raise DatosInvalidos("Datos invalidos.") from None
        fila = await cursor.fetchone()
        assert fila is not None
        existente = _hoja_registrada(fila[5]) if len(fila) > 4 and fila[4] else None
        return Alta(fila[0], fila[1], fila[2], fila[3], existente)

    @staticmethod
    def _adjuntos(nueva: NuevaHoja) -> Jsonb:
        return Jsonb(
            [{"nombre": a.nombre, "tipo": a.tipo, "tamano": a.tamano} for a in nueva.adjuntos]
        )

    async def registrar(self, id_: UUID, nueva: NuevaHoja, ip: str | None) -> Alta:
        return await self._alta(
            "registrar_hoja",
            (
                id_,
                Jsonb(_plano(nueva.contenido)),
                self._adjuntos(nueva),
                ip,
                nueva.revisar_spam,
                nueva.clave_envio,
            ),
        )

    async def transcribir(self, id_: UUID, nueva: NuevaHoja) -> Alta:
        return await self._alta(
            "transcribir_hoja",
            (
                id_,
                Jsonb(_plano(nueva.contenido)),
                self._adjuntos(nueva),
                nueva.fecha_original,
                nueva.numero_hoja_fisica,
            ),
        )

    async def _cargar(self, filtro: str, parametros: dict[str, Any], orden: str) -> list[Hoja]:
        cursor = await self._conexion.execute(f"{_HOJA}{filtro} {orden}", parametros)  # noqa: S608
        filas = await cursor.fetchall()
        cursor = await self._conexion.execute(
            "select id_hoja, n, nombre, tipo, tamano, ruta from public.adjunto_reclamacion "
            "where id_hoja = any(%s) order by id_hoja, n",
            ([f[0] for f in filas],),
        )
        adjuntos: dict[UUID, list[Adjunto]] = {}
        for id_hoja, *resto in await cursor.fetchall():
            adjuntos.setdefault(id_hoja, []).append(Adjunto(*resto))
        return [_hoja(f, adjuntos.get(f[0], [])) for f in filas]

    async def obtener(self, id_: UUID) -> Hoja | None:
        hojas = await self._cargar("where h.id = %(id)s", {"id": id_}, "")
        return hojas[0] if hojas else None

    async def _resumenes(
        self, filtro: str, parametros: dict[str, Any], orden: str
    ) -> list[HojaResumen]:
        cursor = await self._conexion.execute(f"{_RESUMEN}{filtro} {orden}", parametros)  # noqa: S608
        return [HojaResumen(*f) for f in await cursor.fetchall()]

    async def listar_mias(self) -> list[HojaResumen]:
        return await self._resumenes(
            "where h.id_cuenta = (select auth.uid())", {}, "order by h.creada_en desc"
        )

    async def listar(
        self, estado: str | None, desde: date | None, hasta: date | None
    ) -> list[HojaResumen]:
        filtro = (
            "where (%(estado)s::text is null or (%(estado)s::text = 'pendiente') = "
            "(h.respuesta_texto is null)) "
            f"and (%(desde)s::date is null or {_LIMA} >= %(desde)s::date) "
            f"and (%(hasta)s::date is null or {_LIMA} <= %(hasta)s::date)"
        )
        return await self._resumenes(
            filtro, {"estado": estado, "desde": desde, "hasta": hasta}, _ORDEN_BANDEJA
        )

    async def responder(
        self, id_: UUID, texto: str, referencia: str | None, enviada_en: datetime | None
    ) -> None:
        try:
            await self._conexion.execute(
                "select public.responder_hoja(%s, %s, %s, %s)", (id_, texto, referencia, enviada_en)
            )
        except errors.RaiseException as error:
            if error.diag.message_primary == "ya_respondida":
                raise YaRespondida("Esa hoja ya tiene respuesta.") from None
            raise
        except errors.NoDataFound:
            raise NoEncontrado("No existe esa hoja.") from None
        except errors.InsufficientPrivilege:
            raise SinPermiso("Solo el Administrador responde.") from None
        except errors.CheckViolation:
            raise DatosInvalidos("Datos invalidos.") from None

    async def exportar(self, desde: date, hasta: date) -> list[Hoja]:
        return await self._cargar(
            f"where {_LIMA} between %(desde)s and %(hasta)s",
            {"desde": desde, "hasta": hasta},
            "order by h.creada_en",
        )
