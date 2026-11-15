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
    # Solo la usan las pruebas de integracion (alta de usuarios en Auth).
    clave_publicable_supabase: str = ""
    # Origenes del frontend, separados por comas. Vacio = sin CORS.
    origenes_permitidos: str = ""

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
