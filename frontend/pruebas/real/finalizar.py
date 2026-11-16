"""Deja una reserva como confirmada con la sesion ya terminada (SQL de administracion) y corre avanzar_reservas(), como pg_cron.

Uso (desde backend/): uv run python ../frontend/pruebas/real/finalizar.py <folio>
La cuota al_reservar pasa a pagada (la reserva confirmada la tiene pagada); inicio y fin en medias horas, como exige la tabla; la de al_terminar queda pendiente.
"""

import sys

import psycopg

from bugalu.compartido.configuracion import Configuracion

with psycopg.connect(Configuracion().url_base_datos_admin) as conexion:
    conexion.execute(
        "update public.cuota set estado = 'pagada' where hito = 'al_reservar' and id_reserva = (select id from public.reserva where folio = %s)",
        (sys.argv[1],),
    )
    conexion.execute(
        "update public.reserva set estado = 'confirmada', vence_pago = null, inicio = date_bin('30 minutes', now(), timestamptz '2000-01-01') - interval '3 hours', fin = date_bin('30 minutes', now(), timestamptz '2000-01-01') - interval '1 hour' where folio = %s",
        (sys.argv[1],),
    )
    print(conexion.execute("select public.avanzar_reservas()").fetchone()[0])
