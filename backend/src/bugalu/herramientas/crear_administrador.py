"""Herramienta de mantenimiento (CA-11): promueve a administrador a un usuario ya registrado.

Uso: uv run python -m bugalu.herramientas.crear_administrador <correo>
Conecta con URL_BASE_DATOS_ADMIN (superusuario local); no forma parte de la API.
"""

import sys

import psycopg

from bugalu.compartido.configuracion import Configuracion


def main(argumentos: list[str]) -> int:
    if len(argumentos) != 1:
        print("Uso: python -m bugalu.herramientas.crear_administrador <correo>", file=sys.stderr)
        return 2
    url = Configuracion().url_base_datos_admin
    if not url:
        print("Falta URL_BASE_DATOS_ADMIN en backend/.env.", file=sys.stderr)
        return 1
    with psycopg.connect(url) as conexion:
        promovido = conexion.execute(
            "update public.usuario u set rol = 'administrador' from auth.users a "
            "where a.id = u.id and lower(a.email) = lower(%s) returning u.id",
            (argumentos[0],),
        ).fetchone()
    if promovido is None:
        print(f"El usuario {argumentos[0]} no existe: debe registrarse primero.", file=sys.stderr)
        return 1
    print(f"{argumentos[0]} es administrador.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
