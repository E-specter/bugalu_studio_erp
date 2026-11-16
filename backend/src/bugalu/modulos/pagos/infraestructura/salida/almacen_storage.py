"""Storage de Supabase por HTTP con el token del propio usuario: decide la RLS de Storage."""

from typing import Any

import httpx

from bugalu.compartido.errores import AlmacenamientoNoDisponible

BUCKET = "comprobantes"
TIMEOUT_SEGUNDOS = 10.0


class AlmacenStorage:
    def __init__(
        self,
        url_supabase: str,
        clave_publicable: str,
        token_usuario: str,
        transporte: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base = f"{url_supabase.rstrip('/')}/storage/v1"
        self._cabeceras = {"Authorization": f"Bearer {token_usuario}", "apikey": clave_publicable}
        self._transporte = transporte

    async def _post(self, ruta: str, **parametros: Any) -> httpx.Response:
        try:
            async with httpx.AsyncClient(
                transport=self._transporte, timeout=TIMEOUT_SEGUNDOS
            ) as cliente:
                respuesta = await cliente.post(
                    f"{self._base}{ruta}",
                    headers={**self._cabeceras, **parametros.pop("headers", {})},
                    **parametros,
                )
            respuesta.raise_for_status()
        except httpx.HTTPError as error:
            raise AlmacenamientoNoDisponible("No se pudo usar el almacenamiento ahora.") from error
        return respuesta

    async def subir(self, ruta: str, contenido: bytes, mime: str) -> None:
        await self._post(
            f"/object/{BUCKET}/{ruta}",
            content=contenido,
            headers={"Content-Type": mime, "x-upsert": "false"},
        )

    async def firmar(self, ruta: str, segundos: int) -> str:
        respuesta = await self._post(f"/object/sign/{BUCKET}/{ruta}", json={"expiresIn": segundos})
        try:
            return f"{self._base}{respuesta.json()['signedURL']}"
        except (ValueError, KeyError, TypeError) as error:
            raise AlmacenamientoNoDisponible("Respuesta invalida del almacenamiento.") from error
