"""Cambia el horario de una reserva (SQL de administracion) para probar los niveles de RF-18 sin esperar: solo pruebas.

Uso (desde backend/): uv run python ../frontend/pruebas/real/mover.py <folio> <horas_desde_ahora> <duracion_minutos>
El inicio queda  en la media hora anterior a ahora mas las horas indicadas (negativas: ya empezo); el fin, inicio + duracion.
"""

import sys

import psycopg

from bugalu.compartido.configuracion import Configuracion

folio, horas, minutos = sys.argv[1], float(sys.argv[2]), int(sys.argv[3])
with psycopg.connect(Configuracion().url_base_datos_admin) as conexion:
    fila = conexion.execute(
        """update public.reserva set
             inicio = date_bin('30 minutes', now(), timestamptz '2000-01-01') + interval '1 hour' * %s::float8,
             fin = date_bin('30 minutes', now(), timestamptz '2000-01-01') + interval '1 hour' * %s::float8 + interval '1 minute' * %s::int,
             fin_buffer = date_bin('30 minutes', now(), timestamptz '2000-01-01') + interval '1 hour' * %s::float8 + interval '1 minute' * (%s::int + 30)
           where folio = %s returning inicio""",
        (horas, horas, minutos, horas, minutos, folio),
    ).fetchone()
    print(fila[0].isoformat() if fila else "sin reserva")
