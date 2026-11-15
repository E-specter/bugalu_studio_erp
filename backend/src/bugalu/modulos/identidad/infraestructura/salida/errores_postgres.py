"""Traduce los SQLSTATE de las migraciones (BG001, BG002) y de permiso a errores de negocio."""

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg

from bugalu.compartido.errores import (
    NoEncontrado,
    SinPermiso,
    UltimoAdministrador,
    VerificacionNoValida,
)


@contextmanager
def traduciendo_errores_de_postgres() -> Iterator[None]:
    try:
        yield
    except psycopg.Error as error:
        if error.sqlstate == "BG001":
            raise UltimoAdministrador from error
        if error.sqlstate == "BG002":
            raise VerificacionNoValida from error
        if error.sqlstate == "42501":
            raise SinPermiso("No tienes permiso para esta operacion.") from error
        if error.sqlstate == "P0002":
            raise NoEncontrado("No existe el usuario.") from error
        raise
