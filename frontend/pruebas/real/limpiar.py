"""Limpieza del recorrido real de RF-01: borra los usuarios de prueba y comprueba que no quedan huerfanos.

Uso (desde backend/): uv run python ../frontend/pruebas/real/limpiar.py <correo>...
Mismo criterio que backend/tests/conftest.py: solo se apaga el trigger del ultimo administrador.
"""

import sys

import psycopg

from bugalu.compartido.configuracion import Configuracion

correos = [c.lower() for c in sys.argv[1:]]
with psycopg.connect(Configuracion().url_base_datos_admin) as conexion:
    ids = [f[0] for f in conexion.execute("select id from auth.users where lower(email) = any(%s)", (correos,))]
    trigger = "alter table public.usuario {} trigger usuario_conserva_administrador"
    conexion.execute(trigger.format("disable"))
    conexion.execute("delete from public.solicitud_acceso where id_usuario = any(%s) or id_revisor = any(%s)", (ids, ids))
    conexion.execute("delete from auth.users where id = any(%s)", (ids,))
    conexion.execute(trigger.format("enable"))
    restos = conexion.execute(
        """select (select count(*) from public.usuario u where not exists (select 1 from auth.users a where a.id = u.id))
                + (select count(*) from public.solicitud_acceso s where not exists (select 1 from auth.users a where a.id = s.id_usuario))
                + (select count(*) from auth.users where lower(email) = any(%s))""",
        (correos,),
    ).fetchone()
if restos != (0,):
    sys.exit(f"Quedaron {restos[0]} restos de las pruebas en la base.")
print(f"Limpieza: {len(ids)} usuarios borrados, sin huerfanos.")
