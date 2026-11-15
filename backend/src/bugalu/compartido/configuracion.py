from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracion(BaseSettings):
    """Variables de entorno (o backend/.env). Los valores por defecto son los del stack local."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    url_base_datos: str = "postgresql://postgres:postgres@127.0.0.1:45622/postgres"
    url_supabase: str = "http://127.0.0.1:45621"
    # Solo la usan las pruebas de integracion (alta de usuarios en Auth).
    clave_publicable_supabase: str = ""

    @property
    def emisor_jwt(self) -> str:
        return f"{self.url_supabase}/auth/v1"

    @property
    def url_jwks(self) -> str:
        return f"{self.emisor_jwt}/.well-known/jwks.json"


@lru_cache
def obtener_configuracion() -> Configuracion:
    return Configuracion()
