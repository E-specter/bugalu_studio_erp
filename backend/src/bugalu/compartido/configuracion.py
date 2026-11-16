from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV = Path(__file__).parents[3] / ".env"  # backend/.env, desde cualquier directorio


class Configuracion(BaseSettings):
    """Variables de entorno (o backend/.env). Sin credenciales por defecto."""

    model_config = SettingsConfigDict(env_file=_ENV, extra="ignore")

    url_base_datos: str  # rol `bugalu_api` (supabase/migrations), nunca el superusuario
    url_supabase: str
    # Solo pruebas: rol administrador para altas de usuarios y limpieza (RLS no aplica).
    url_base_datos_admin: str = ""
    # Espera maxima por una conexion libre del pool antes de responder 503.
    timeout_pool_segundos: float = 5
    # Clave publicable (`apikey`) de Supabase: Auth en las pruebas y Storage en la API.
    clave_publicable_supabase: str
    # Origenes del frontend, separados por comas. Vacio = sin CORS.
    origenes_permitidos: str = ""
    # Correo saliente (ADR-009): en local, el SMTP de Mailpit del stack (supabase/config.toml).
    smtp_host: str = "127.0.0.1"
    smtp_puerto: int = 45625
    correo_remitente: str = "no-responder@bugalu.pe"
    # Segundos entre envios de la bandeja de correos; 0 desactiva la tarea periodica.
    intervalo_envio_correos: int = 30

    @property
    def lista_origenes_permitidos(self) -> list[str]:
        return [o.strip() for o in self.origenes_permitidos.split(",") if o.strip()]

    @property
    def emisor_jwt(self) -> str:
        return f"{self.url_supabase}/auth/v1"

    @property
    def url_jwks(self) -> str:
        return f"{self.emisor_jwt}/.well-known/jwks.json"


@lru_cache
def obtener_configuracion() -> Configuracion:
    try:
        return Configuracion()
    except ValidationError as error:
        faltan = ", ".join(
            str(e["loc"][0]).upper() for e in error.errors() if e["type"] == "missing"
        )
        raise RuntimeError(
            f"Falta configuracion: {faltan}. Copia backend/.env.example a backend/.env."
        ) from None
