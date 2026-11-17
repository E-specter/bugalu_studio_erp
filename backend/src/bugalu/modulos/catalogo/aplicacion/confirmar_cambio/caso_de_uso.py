from dataclasses import dataclass
from typing import Any

from bugalu.compartido.errores import (
    CambioDesactualizado,
    ConfirmacionNoValida,
    PalabraIncorrecta,
    SinPermiso,
)
from bugalu.modulos.catalogo.aplicacion.lectura_recurso import cargar, valores
from bugalu.modulos.catalogo.aplicacion.permisos import exigir_administrador
from bugalu.modulos.catalogo.aplicacion.previsualizar_cambio.caso_de_uso import hash_de
from bugalu.modulos.catalogo.dominio import cambios_sensibles as sensibles
from bugalu.modulos.catalogo.dominio.cambios_sensibles import CambioRegistrado, Confirmacion
from bugalu.modulos.catalogo.dominio.puertos import RepositorioCambios, RepositorioCatalogo


@dataclass(frozen=True)
class Confirmado:
    confirmacion: Confirmacion
    valor: Any  # el recurso ya actualizado (objeto de dominio)
    cambios: list[CambioRegistrado]


class ConfirmarCambio:
    def __init__(self, catalogo: RepositorioCatalogo, cambios: RepositorioCambios) -> None:
        self._catalogo = catalogo
        self._cambios = cambios

    async def ejecutar(self, token: str, palabra: str) -> Confirmado:
        """Todo en la transaccion del llamador: si algo falla, no se aplica ni se registra nada."""
        await exigir_administrador(self._catalogo)
        confirmacion = await self._cambios.tomar_confirmacion(hash_de(token))
        if confirmacion is None:
            raise ConfirmacionNoValida("La confirmación no existe, venció o ya se usó.")
        if confirmacion.id_autor != await self._cambios.id_usuario():
            raise SinPermiso("Esta confirmación es de otro administrador.")
        if not confirmacion.vigente:
            raise ConfirmacionNoValida("La confirmación no existe, venció o ya se usó.")
        if palabra.strip(" ") != sensibles.PALABRA:
            raise PalabraIncorrecta("Escribe CONFIRMAR, en mayúsculas.", {"campo": "palabra"})
        recurso, id_recurso = confirmacion.recurso, confirmacion.id_recurso
        await self._catalogo.bloquear_recurso(recurso, id_recurso)
        _, actual = await cargar(self._catalogo, recurso, id_recurso)
        vigentes = valores(recurso, actual)
        if any(vigentes.get(c) != anterior for c, (anterior, _) in confirmacion.cambios.items()):
            raise CambioDesactualizado("Otro administrador cambió este recurso mientras revisabas.")
        if recurso == "parametros":
            nuevos = {c: nuevo for c, (_, nuevo) in confirmacion.cambios.items()}
            sensibles.validar_plazos(sensibles.aplicar(recurso, actual, nuevos))
        registrados = await self._cambios.aplicar(confirmacion)
        _, valor = await cargar(self._catalogo, recurso, id_recurso)
        return Confirmado(confirmacion, valor, registrados)
