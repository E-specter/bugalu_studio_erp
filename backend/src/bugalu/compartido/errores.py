"""Errores del kernel, sin dependencias de HTTP (formato de respuesta: manejadores_http)."""


class ErrorDeNegocio(Exception):
    codigo = "error_de_negocio"
    estado_http = 400

    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


class NoAutenticado(ErrorDeNegocio):
    codigo = "no_autenticado"
    estado_http = 401


class NoEncontrado(ErrorDeNegocio):
    codigo = "no_encontrado"
    estado_http = 404


class AutenticacionNoDisponible(ErrorDeNegocio):
    codigo = "autenticacion_no_disponible"
    estado_http = 503
