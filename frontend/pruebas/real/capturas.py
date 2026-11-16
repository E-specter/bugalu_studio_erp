"""Imprime en JSON los ids de los usuarios de prueba (para vaciar su carpeta de Storage `comprobantes/<id>/`).

Uso (desde backend/): uv run python ../frontend/pruebas/real/capturas.py <correo>...
"""

import json
import sys

import psycopg

from bugalu.compartido.configuracion import Configuracion

correos = [c.lower() for c in sys.argv[1:]]
with psycopg.connect(Configuracion().url_base_datos_admin) as conexion:
    print(json.dumps([str(f[0]) for f in conexion.execute("select id from auth.users where lower(email) = any(%s)", (correos,))]))
