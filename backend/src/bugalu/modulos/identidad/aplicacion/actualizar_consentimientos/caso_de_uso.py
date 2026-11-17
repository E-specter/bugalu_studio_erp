from collections.abc import Mapping
from uuid import UUID

from bugalu.compartido.errores import TelefonoRequerido
from bugalu.modulos.identidad.aplicacion.obtener_perfil.caso_de_uso import PerfilNoEncontrado
from bugalu.modulos.identidad.dominio.puertos import RepositorioUsuarios


class ActualizarConsentimientos:
    """CA-12: solo se registra lo que cambia; nunca condiciona el servicio."""

    def __init__(self, usuarios: RepositorioUsuarios) -> None:
        self._usuarios = usuarios

    async def ejecutar(self, id_usuario: UUID, deseados: Mapping[str, bool]) -> dict[str, bool]:
        usuario = await self._usuarios.obtener_por_id(id_usuario)
        if usuario is None:
            raise PerfilNoEncontrado
        actuales = await self._usuarios.consentimientos(id_usuario)
        finales = {**actuales, **deseados}
        if finales["promociones_whatsapp"] and not usuario.telefono:
            raise TelefonoRequerido(
                "Registra tu telefono para recibir promociones por WhatsApp.",
                {"campo": "promociones_whatsapp"},
            )
        for consentimiento, dar in deseados.items():
            if actuales[consentimiento] != dar:
                await self._usuarios.cambiar_consentimiento(consentimiento, dar)
        return finales
