from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import SecretStr, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV = Path(__file__).parents[3] / ".env"  # backend/.env, desde cualquier directorio


_HOSTS_LOCALES = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}  # noqa: S104 - lista de rechazo


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
    # URL publica de la plataforma (sin barra final): enlaces de los correos (ADR-016).
    url_publica: str = "http://127.0.0.1:4321"
    # Cuenta de Google del estudio (ADR-011): con usuario hacen falta clave y STARTTLS.
    smtp_usuario: str = ""
    smtp_clave: SecretStr = SecretStr("")
    smtp_starttls: bool = False
    # Segundos entre envios de la bandeja de correos; 0 desactiva la tarea periodica.
    intervalo_envio_correos: int = 30
    # Segundos entre limpiezas de adjuntos huerfanos del Libro de Reclamaciones; 0 la desactiva.
    intervalo_limpieza_adjuntos: int = 3600

    @model_validator(mode="after")
    def _smtp_con_usuario_exige_clave_y_starttls(self) -> Configuracion:
        if self.smtp_usuario and not self.smtp_clave.get_secret_value():
            raise ValueError("SMTP_USUARIO exige SMTP_CLAVE")
        if self.smtp_usuario and not self.smtp_starttls:
            raise ValueError(
                "SMTP_USUARIO exige SMTP_STARTTLS=true (no se envia la clave en claro)"
            )
        return self

    @model_validator(mode="after")
    def _url_publica_con_esquema_y_host(self) -> Configuracion:
        url = urlparse(self.url_publica)
        if url.scheme not in ("http", "https") or not url.hostname:
            raise ValueError("URL_PUBLICA debe empezar por http:// o https:// e incluir el host")
        return self

    @model_validator(mode="after")
    def _envio_real_exige_url_publica_no_local(self) -> Configuracion:
        # No hay variable de "produccion": el envio con la cuenta de Google (SMTP_USUARIO) es
        # la senal. Con ella, enlaces a localhost saldrian en correos reales a los clientes.
        if self.smtp_usuario and urlparse(self.url_publica).hostname in _HOSTS_LOCALES:
            raise ValueError("SMTP_USUARIO exige URL_PUBLICA con el dominio real, no una URL local")
        return self

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
        errores = error.errors()
        faltan = ", ".join(str(e["loc"][0]).upper() for e in errores if e["type"] == "missing")
        # Solo el mensaje de nuestras reglas: el detalle de pydantic repetiria los valores.
        invalidas = "; ".join(str(e["ctx"]["error"]) for e in errores if e["type"] == "value_error")
        detalle = "; ".join(
            parte for parte in (f"falta {faltan}" if faltan else "", invalidas) if parte
        )
        raise RuntimeError(
            f"Configuracion invalida: {detalle}. Revisa backend/.env y backend/.env.example."
        ) from None
