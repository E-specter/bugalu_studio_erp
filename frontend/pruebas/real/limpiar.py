"""Limpieza de los recorridos reales (RF-01 y reservas): borra los usuarios de prueba y todo lo que crearon
(aceptaciones por cascada, reservas con sus cuotas, comprobantes y especialistas, franjas, cierres, avisos) y comprueba que no quedan huerfanos.

Uso (desde backend/): uv run python ../frontend/pruebas/real/limpiar.py [--avisos-desde=<iso>] <correo>...
Mismo criterio que backend/tests/conftest.py: solo se apaga el trigger del ultimo administrador.
"""

import sys

import psycopg

from bugalu.compartido.configuracion import Configuracion

# --avisos-desde=<iso>: borra tambien los avisos `texto_legal_nuevo` encolados desde ese instante (una version mayor o menor avisa a todos los clientes).
desde = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--avisos-desde=")), "infinity")
correos = [c.lower() for c in sys.argv[1:] if not c.startswith("--")]
with psycopg.connect(Configuracion().url_base_datos_admin) as conexion:
    ids = [f[0] for f in conexion.execute("select id from auth.users where lower(email) = any(%s)", (correos,))]
    # Reservas y avisos de los usuarios de prueba; sus franjas y cierres los publica el administrador de prueba.
    conexion.execute("delete from public.comprobante_pago where id_cliente = any(%s)", (ids,))  # antes que la cuota: su FK no es en cascada
    conexion.execute("delete from public.reserva where id_cliente = any(%s)", (ids,))
    conexion.execute("delete from public.notificacion where lower(destinatario) = any(%s)", (correos,))
    conexion.execute("delete from public.notificacion where tipo = 'texto_legal_nuevo' and creada_en >= %s", (desde,))
    # RF-16: las hojas de reclamacion y sus adjuntos son inmutables y no se borran (al borrar la cuenta quedan con id_cuenta nulo): no cuentan como restos.
    # Si, los intentos del limite por IP de esta corrida, para no agotar las 5 hojas por hora.
    conexion.execute("delete from public.intento_reclamacion where creado_en >= %s", (desde,))
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
                + (select count(*) from public.credito c where not exists (select 1 from public.reserva r where r.id = c.id_reserva))
                + (select count(*) from public.devolucion d where not exists (select 1 from public.reserva r where r.id = d.id_reserva))
                + (select count(*) from public.reprogramacion g where not exists (select 1 from public.reserva r where r.id = g.id_reserva))
                + (select count(*) from public.aplicacion_credito a where not exists (select 1 from public.credito c where c.id = a.id_credito))
                + (select count(*) from public.franja_sala where id_publicador is null)
                + (select count(*) from public.cierre_sala where id_autor is null)
                + (select count(*) from public.aceptacion a where not exists (select 1 from public.usuario u where u.id = a.id_usuario))
                + (select count(*) from public.notificacion where tipo = 'texto_legal_nuevo' and creada_en >= %s)""",
        (correos, ids, correos, desde),
    ).fetchone()
if restos != (0,):
    sys.exit(f"Quedaron {restos[0]} restos de las pruebas en la base.")
print(f"Limpieza: {len(ids)} usuarios borrados, sin huerfanos.")
