"""Pone vence_pago de una reserva en el pasado (SQL de administracion) y corre caducar_reservas(), como pg_cron.

Uso (desde backend/): uv run python ../frontend/pruebas/real/caducar.py <folio>
"""

import sys

import psycopg

from bugalu.compartido.configuracion import Configuracion

with psycopg.connect(Configuracion().url_base_datos_admin) as conexion:
    conexion.execute("update public.reserva set vence_pago = now() - interval '1 minute' where folio = %s", (sys.argv[1],))
    print(conexion.execute("select public.caducar_reservas()").fetchone()[0])
