"""Storage de Supabase (bucket publico `profesionales`) con el token del propio usuario: la RLS de
Storage decide quien escribe en la carpeta de cada perfil."""

import httpx

from bugalu.compartido.errores import AlmacenamientoNoDisponible

BUCKET = "profesionales"
TIMEOUT_SEGUNDOS = 10.0


def url_publica(url_supabase: str, ruta: str) -> str:
    return f"{url_supabase.rstrip('/')}/storage/v1/object/public/{BUCKET}/{ruta}"


class AlmacenFotosStorage:
    def __init__(
        self,
        url_supabase: str,
        clave_publicable: str,
        token_usuario: str,
        transporte: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base = f"{url_supabase.rstrip('/')}/storage/v1/object/{BUCKET}"
        self._cabeceras = {"Authorization": f"Bearer {token_usuario}", "apikey": clave_publicable}
        self._transporte = transporte

    async def _pedir(
        self,
        metodo: str,
        ruta: str,
        cabeceras: dict[str, str] | None = None,
        contenido: bytes | None = None,
    ) -> httpx.Response:
        try:
            async with httpx.AsyncClient(
                transport=self._transporte, timeout=TIMEOUT_SEGUNDOS
            ) as cliente:
                respuesta = await cliente.request(
                    metodo,
                    f"{self._base}/{ruta}",
                    headers={**self._cabeceras, **(cabeceras or {})},
                    content=contenido,
                )
            if respuesta.status_code != 404 or metodo != "DELETE":  # borrar lo ya borrado es ok
                respuesta.raise_for_status()
        except httpx.HTTPError as error:
            raise AlmacenamientoNoDisponible("No se pudo usar el almacenamiento ahora.") from error
        return respuesta

    async def subir(self, ruta: str, contenido: bytes, mime: str) -> None:
        await self._pedir("POST", ruta, {"Content-Type": mime, "x-upsert": "true"}, contenido)

    async def borrar(self, ruta: str) -> None:
        await self._pedir("DELETE", ruta)
