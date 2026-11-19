# Auditoría · Parámetros de daños (RF-20) y editor de textos (RF-17)

## Backend D2 + E2 (cd9e038) · APROBADO (Opus)

- Seguridad: `configuracion_danos` con RLS (solo lectura del Administrador, nadie escribe salvo `aplicar_cambio_confirmado`); `parametros_danos()` security definer con `search_path=''`; redefiniciones de `es_parametro_sensible`, `bloquear_recurso_sensible` y `aplicar_cambio_confirmado` sin pérdidas frente a la versión anterior; ningún camino cambia tarifa o tope sin 428 → vista previa → CONFIRMAR → registro. Vista previa: solo Administrador, no escribe, mismo saneado que `TextoLegal` (HTML crudo, `javascript:`, `data:`).
- No bloqueantes: límite de vista previa (200 000) menor que el de publicar (300 000); render síncrono (~1,7 s en el peor caso, solo Administrador); `obtener_parametros` duplicado en catalogo y reservas; firma `Mapping[str, int]` desactualizada en `guardar_parametros`.
- Decisiones de leader: unificar el límite de la vista previa con el de publicar (300 000) en la siguiente corrección; el resto queda anotado.
