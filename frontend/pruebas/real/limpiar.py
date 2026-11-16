"""Limpieza de los recorridos reales (RF-01 y reservas): borra los usuarios de prueba y todo lo que crearon
(reservas con sus cuotas, comprobantes y especialistas, franjas, cierres, avisos) y comprueba que no quedan huerfanos.

Uso (desde backend/): uv run python ../frontend/pruebas/real/limpiar.py <correo>...
Mismo criterio que backend/tests/conftest.py: solo se apaga el trigger del ultimo administrador.
"""

import sys

import psycopg

from bugalu.compartido.configuracion import Configuracion

correos = [c.lower() for c in sys.argv[1:]]
with psycopg.connect(Configuracion().url_base_datos_admin) as conexion:
    ids = [f[0] for f in conexion.execute("select id from auth.users where lower(email) = any(%s)", (correos,))]
    # Reservas y avisos de los usuarios de prueba; sus franjas y cierres los publica el administrador de prueba.
    conexion.execute("delete from public.comprobante_pago where id_cliente = any(%s)", (ids,))  # antes que la cuota: su FK no es en cascada
    conexion.execute("delete from public.reserva where id_cliente = any(%s)", (ids,))
    conexion.execute("delete from public.notificacion where lower(destinatario) = any(%s)", (correos,))
    conexion.execute("delete from public.franja_sala where id_publicador = any(%s)", (ids,))
    conexion.execute("delete from public.cierre_sala where id_autor = any(%s)", (ids,))
    trigger = "alter table public.usuario {} trigger usuario_conserva_administrador"
    conexion.execute(trigger.format("disable"))
    conexion.execute("delete from public.solicitud_acceso where id_usuario = any(%s) or id_revisor = any(%s)", (ids, ids))
    conexion.execute("delete from auth.users where id = any(%s)", (ids,))
    conexion.execute(trigger.format("enable"))
    restos = conexion.execute(
        """select (select count(*) from public.usuario u where not exists (select 1 from auth.users a where a.id = u.id))
                + (select count(*) from public.solicitud_acceso s where not exists (select 1 from auth.users a where a.id = s.id_usuario))
                + (select count(*) from auth.users where lower(email) = any(%s))
                + (select count(*) from public.reserva r where not exists (select 1 from auth.users a where a.id = r.id_cliente))
                + (select count(*) from public.cuota c where not exists (select 1 from public.reserva r where r.id = c.id_reserva))
                + (select count(*) from public.comprobante_pago p where not exists (select 1 from public.cuota c where c.id = p.id_cuota))
                + (select count(*) from public.comprobante_pago where id_cliente = any(%s))
                + (select count(*) from public.reserva_especialista e where not exists (select 1 from public.reserva r where r.id = e.id_reserva))
                + (select count(*) from public.notificacion where lower(destinatario) = any(%s))
                + (select count(*) from public.franja_sala where id_publicador is null)
                + (select count(*) from public.cierre_sala where id_autor is null)""",
        (correos, ids, correos),
    ).fetchone()
if restos != (0,):
    sys.exit(f"Quedaron {restos[0]} restos de las pruebas en la base.")
print(f"Limpieza: {len(ids)} usuarios borrados, sin huerfanos.")
