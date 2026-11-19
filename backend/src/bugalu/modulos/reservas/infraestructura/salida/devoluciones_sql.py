"""Lectura de devoluciones compartida: `Reserva.devolucion` y la cola del administrador."""

from typing import Any

from bugalu.modulos.reservas.dominio.modelos import Devolucion, Referencia

DEVOLUCION = (
    "select d.id, d.id_credito, d.id_reserva, r.folio, d.id_cliente, u.nombre, d.tipo, d.motivo, "
    "d.monto_solicitado, d.solicitada_en, d.estado, d.monto_aprobado, d.motivo_decision, "
    "d.decidida_en, d.nota_realizada, d.realizada_en, d.limite, r.tipo "
    "from public.devolucion d join public.reserva r on r.id = d.id_reserva "
    "left join public.usuario u on u.id = d.id_cliente "
)


def devolucion_desde_fila(f: tuple[Any, ...]) -> Devolucion:
    return Devolucion(f[0], f[1], f[2], f[3], Referencia(f[4], f[5]), *f[6:])
