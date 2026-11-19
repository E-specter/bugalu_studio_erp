# ruff: noqa: E501 - datos y firmas de prueba
"""RF-15 B1: casos de uso de agendar, consultar y cambiar el encuentro con un repositorio falso."""

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest

from bugalu.compartido.errores import (
    DatosInvalidos,
    DuracionNoOfrecida,
    FueraDeHorario,
    NoEncontrado,
    ReaceptacionRequerida,
    SinPermiso,
)
from bugalu.modulos.asesorias.aplicacion.agendar.caso_de_uso import AgendarAsesoria
from bugalu.modulos.asesorias.aplicacion.consultar.caso_de_uso import (
    ListarAsesorias,
    ListarMisAsesorias,
    ObtenerAsesoria,
)
from bugalu.modulos.asesorias.aplicacion.encuentro.caso_de_uso import CambiarEncuentro
from bugalu.modulos.asesorias.dominio.asesoria import Asesoria, NuevaAsesoria, PersonaAsesoria
from bugalu.modulos.asesorias.dominio.modelos import Horario
from bugalu.modulos.catalogo.dominio.precio import ConfiguracionImpuestos
from bugalu.modulos.reservas.dominio.modelos import RequisitosReserva
from tests.modulos.asesorias.aplicacion.falsos import PABLO, perfil

CLIENTE = uuid4()
INICIO = datetime(2027, 3, 10, 15, 0, tzinfo=UTC)
AHORA = datetime(2027, 3, 1, 12, 0, tzinfo=UTC)
OK = RequisitosReserva((), (), False, {"tipo": "condiciones_contratacion", "version": "1.0.0"})  # type: ignore[arg-type]


class AgendaFalsa:
    def __init__(self) -> None:
        self.administrador = False
        self.profesional = False
        self.requisitos = OK
        self.perfiles = {PABLO: perfil(PABLO)}
        self.horarios = [
            Horario(uuid4(), PABLO, INICIO - timedelta(hours=1), INICIO + timedelta(hours=3))
        ]
        self.nuevas: list[NuevaAsesoria] = []
        self.pasos: list[str] = []
        self.asesoria: Asesoria | None = None
        self.encuentros: list[tuple[str, str | None, str | None]] = []

    async def es_administrador(self) -> bool:
        return self.administrador

    async def es_profesional(self) -> bool:
        return self.profesional

    async def requisitos_para_reservar(self) -> RequisitosReserva:
        return self.requisitos

    async def limites_reserva(self) -> tuple[int, int]:
        return 2, 8

    async def plazos_pago(self) -> tuple[int, int]:
        return 3, 24

    async def obtener_profesional(self, id_profesional: UUID) -> Any:
        return self.perfiles.get(id_profesional)

    async def obtener_impuestos(self) -> ConfiguracionImpuestos:
        return ConfiguracionImpuestos(Decimal("18"), True)

    async def listar_horarios(
        self, id_profesional: UUID, desde: datetime, hasta: datetime
    ) -> list[Horario]:
        return self.horarios

    async def insertar_asesoria(self, nueva: NuevaAsesoria) -> UUID:
        self.pasos.append("insertar")
        self.nuevas.append(nueva)
        self.asesoria = Asesoria(
            uuid4(), "A-2027-00001", "pre_reservada", None, nueva.inicio, nueva.fin, nueva.precio,
            nueva.vence_pago, CLIENTE, PersonaAsesoria(PABLO, "Pablo", None), nueva.modalidad, None, None,
            cliente=PersonaAsesoria(CLIENTE, "Ana", None, "999", "a@x.pe"), notas="secreto",
        )  # fmt: skip
        return self.asesoria.id

    async def aceptar_condiciones(self, id_asesoria: UUID, version: str) -> None:
        self.pasos.append("aceptar")

    async def encolar_aviso(self, id_asesoria: UUID) -> None:
        self.pasos.append("aviso")

    async def obtener_asesoria(self, id_asesoria: UUID) -> Asesoria | None:
        return self.asesoria

    async def listar_mias(self) -> list[Asesoria]:
        return [self.asesoria] if self.asesoria else []

    async def listar(self, *args: Any) -> list[Asesoria]:
        return [self.asesoria] if self.asesoria else []

    async def cambiar_encuentro(
        self, id_asesoria: UUID, modalidad: str, lugar: str | None, enlace: str | None
    ) -> None:
        self.encuentros.append((modalidad, lugar, enlace))
        if self.asesoria:
            self.asesoria = replace(self.asesoria, modalidad=modalidad, lugar=lugar, enlace=enlace)


async def agendar(repo: AgendaFalsa, inicio: datetime = INICIO, duracion: int = 30) -> Asesoria:
    return await AgendarAsesoria(repo).ejecutar(
        CLIENTE, PABLO, inicio, duracion, "virtual", "1.0.0", AHORA
    )


async def test_agendar_guarda_precio_y_cuota_y_acepta_y_avisa_en_orden() -> None:
    repo = AgendaFalsa()
    a = await agendar(repo)
    assert repo.pasos == ["insertar", "aceptar", "aviso"]
    n = repo.nuevas[0]
    assert (n.total, n.fin - n.inicio, n.precio["total"]) == (
        Decimal("50.00"),
        timedelta(minutes=30),
        "50.00",
    )
    assert n.vence_pago <= INICIO
    assert a.cliente is None and a.notas is None  # el cliente no ve el contacto ni las notas


@pytest.mark.parametrize(
    ("ajuste", "error"),
    [
        (lambda r: setattr(r, "profesional", True), SinPermiso),
        (
            lambda r: setattr(
                r, "requisitos", RequisitosReserva(({"tipo": "t"},), (), False, None)
            ),
            ReaceptacionRequerida,
        ),  # type: ignore[arg-type]
        (lambda r: r.perfiles.clear(), NoEncontrado),
        (lambda r: r.perfiles.update({PABLO: perfil(PABLO, publicado=False)}), NoEncontrado),
        (lambda r: r.horarios.clear(), FueraDeHorario),
    ],
)
async def test_errores_de_agendar_no_escriben_nada(
    ajuste: Callable[[AgendaFalsa], object], error: type[Exception]
) -> None:
    repo = AgendaFalsa()
    ajuste(repo)
    with pytest.raises(error):
        await agendar(repo)
    assert repo.pasos == []


async def test_duracion_sin_precio_y_inicio_fuera_de_media_hora() -> None:
    repo = AgendaFalsa()
    with pytest.raises(DuracionNoOfrecida):
        await agendar(repo, duracion=60)  # el perfil de prueba solo ofrece 30
    with pytest.raises(DatosInvalidos):
        await agendar(repo, INICIO + timedelta(minutes=10))
    assert repo.pasos == []


async def test_cada_rol_ve_lo_suyo_de_una_asesoria() -> None:
    repo = AgendaFalsa()
    await agendar(repo)
    assert repo.asesoria is not None
    dueno = await ObtenerAsesoria(repo).ejecutar(CLIENTE, repo.asesoria.id)
    assert dueno.cliente is None and dueno.notas is None
    pro = await ObtenerAsesoria(repo).ejecutar(PABLO, repo.asesoria.id)
    assert (
        pro.cliente is not None
        and pro.notas == "secreto"
        and pro.cuotas is None
        and pro.pagado is None
    )
    repo.administrador = True
    assert (await ObtenerAsesoria(repo).ejecutar(uuid4(), repo.asesoria.id)).cliente is not None
    repo.asesoria = None
    with pytest.raises(NoEncontrado):
        await ObtenerAsesoria(repo).ejecutar(CLIENTE, uuid4())


async def test_las_listas_exigen_el_rol_y_validan_el_estado() -> None:
    repo = AgendaFalsa()
    with pytest.raises(SinPermiso):
        await ListarAsesorias(repo).ejecutar(None, None, None, None, False, AHORA)
    repo.profesional = True
    with pytest.raises(DatosInvalidos):
        await ListarAsesorias(repo).ejecutar("inventado", None, None, None, False, AHORA)
    assert await ListarAsesorias(repo).ejecutar("confirmada", None, None, None, True, AHORA) == []
    with pytest.raises(SinPermiso):  # un profesional no tiene "mis asesorias" de cliente
        await ListarMisAsesorias(repo).ejecutar()


async def test_cambiar_el_encuentro_exige_a_su_profesional_o_al_administrador() -> None:
    repo = AgendaFalsa()
    await agendar(repo)
    assert repo.asesoria is not None
    with pytest.raises(SinPermiso):
        await CambiarEncuentro(repo).ejecutar(
            CLIENTE, repo.asesoria.id, {"enlace": "https://meet.google.com/a"}
        )
    assert repo.encuentros == []
    a = await CambiarEncuentro(repo).ejecutar(
        PABLO, repo.asesoria.id, {"enlace": "https://meet.google.com/a"}
    )
    assert a.enlace == "https://meet.google.com/a"
    a = await CambiarEncuentro(repo).ejecutar(
        PABLO, repo.asesoria.id, {"modalidad": "presencial", "lugar": "Av. 1"}
    )
    assert (a.modalidad, a.lugar, a.enlace) == ("presencial", "Av. 1", None)
