from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from bugalu.compartido.errores import FranjaSolapada
from bugalu.modulos.reservas.dominio.disponibilidad import Tramo
from bugalu.modulos.reservas.dominio.modelos import Cierre, Franja, ReservaVisible, Sala

LIMA = timezone(timedelta(hours=-5))
SALA = Sala(uuid4(), "Sala principal", "La Molina")


def t(dia: int, hora: int, minuto: int = 0) -> datetime:
    return datetime(2026, 12, dia, hora, minuto, tzinfo=LIMA)


class ReservasFalso:
    def __init__(self, administrador: bool = True, personal: bool = True) -> None:
        self.administrador = administrador
        self.personal = personal
        self.franjas: dict[UUID, Franja] = {}
        self.cierres: dict[UUID, Cierre] = {}
        self.ocupados: list[Tramo] = []
        self.bloqueos: list[UUID] = []
        self.visibles: list[ReservaVisible] = []
        self.nombres: dict[UUID, str | None] = {}
        self.parametros = {
            "dias_limite_pago": 3,
            "horas_limite_pago": 1,
            "anticipacion_minima_horas": 2,
            "anticipacion_maxima_semanas": 8,
            "porcentaje_adelanto": 50,
            "horas_nivel_1": 48,
            "horas_nivel_2": 24,
            "porcentaje_penalizacion_nivel_2": 25,
            "minutos_tolerancia_inasistencia": 15,
            "dias_vigencia_credito": 30,
            "reprogramaciones_nivel_1": 2,
            "reprogramaciones_nivel_2": 1,
        }

    async def es_administrador(self) -> bool:
        return self.administrador

    async def es_personal(self) -> bool:
        return self.personal

    async def listar_salas(self) -> list[Sala]:
        return [SALA]

    async def existe_sala(self, id_sala: UUID) -> bool:
        return id_sala == SALA.id

    async def limites_reserva(self) -> tuple[int, int]:
        return (
            self.parametros["anticipacion_minima_horas"],
            self.parametros["anticipacion_maxima_semanas"],
        )

    async def franjas_en(self, id_sala: UUID, desde: datetime, hasta: datetime) -> list[Franja]:
        return [f for f in self.franjas.values() if f.inicio < hasta and desde < f.fin]

    async def franjas_antes_de(self, id_sala: UUID, instante: datetime) -> list[Franja]:
        return [f for f in self.franjas.values() if f.inicio < instante]

    async def cierres_en(self, id_sala: UUID, desde: datetime, hasta: datetime) -> list[Cierre]:
        return [c for c in self.cierres.values() if c.inicio < hasta and desde < c.fin]

    async def ocupacion(self, id_sala: UUID, desde: datetime, hasta: datetime) -> list[Tramo]:
        return [o for o in self.ocupados if o.inicio < hasta and desde < o.fin]

    async def reservas_visibles(
        self, id_sala: UUID, desde: datetime, hasta: datetime
    ) -> list[ReservaVisible]:
        return self.visibles

    async def nombres_de_clientes(self, ids: Sequence[UUID]) -> Mapping[UUID, str | None]:
        return self.nombres

    async def insertar_franjas(self, id_sala: UUID, tramos: Sequence[Tramo]) -> list[Franja]:
        nuevas = []
        for tr in tramos:
            if any(f.inicio < tr.fin and tr.inicio < f.fin for f in self.franjas.values()):
                raise FranjaSolapada("Se solapa con otra franja.")
            f = Franja(uuid4(), id_sala, tr.inicio, tr.fin)
            self.franjas[f.id] = f
            nuevas.append(f)
        return nuevas

    async def bloquear_sala(self, id_sala: UUID) -> None:
        self.bloqueos.append(id_sala)

    async def obtener_franja(self, id_franja: UUID) -> Franja | None:
        return self.franjas.get(id_franja)

    async def eliminar_franja(self, id_franja: UUID) -> None:
        del self.franjas[id_franja]

    async def insertar_cierre(self, id_sala: UUID, tramo: Tramo, motivo: str) -> Cierre:
        c = Cierre(uuid4(), id_sala, tramo.inicio, tramo.fin, motivo)
        self.cierres[c.id] = c
        return c

    async def obtener_cierre(self, id_cierre: UUID) -> Cierre | None:
        return self.cierres.get(id_cierre)

    async def eliminar_cierre(self, id_cierre: UUID) -> None:
        del self.cierres[id_cierre]

    async def obtener_parametros(self) -> dict[str, int]:
        return dict(self.parametros)

    async def guardar_parametros(self, cambios: Mapping[str, int]) -> None:
        self.parametros.update(cambios)
