# Auditoría · Parámetros de daños (RF-20) y editor de textos (RF-17)

## Backend D2 + E2 (cd9e038) · APROBADO (Opus)

- Seguridad: `configuracion_danos` con RLS (solo lectura del Administrador, nadie escribe salvo `aplicar_cambio_confirmado`); `parametros_danos()` security definer con `search_path=''`; redefiniciones de `es_parametro_sensible`, `bloquear_recurso_sensible` y `aplicar_cambio_confirmado` sin pérdidas frente a la versión anterior; ningún camino cambia tarifa o tope sin 428 → vista previa → CONFIRMAR → registro. Vista previa: solo Administrador, no escribe, mismo saneado que `TextoLegal` (HTML crudo, `javascript:`, `data:`).
- No bloqueantes: límite de vista previa (200 000) menor que el de publicar (300 000); render síncrono (~1,7 s en el peor caso, solo Administrador); `obtener_parametros` duplicado en catalogo y reservas; firma `Mapping[str, int]` desactualizada en `guardar_parametros`.
- Decisiones de leader: unificar el límite de la vista previa con el de publicar (300 000) en la siguiente corrección; el resto queda anotado.

## Frontend D3 + E3 (dae0879) · APROBADO

- Sin bloqueantes.
- Seguridad: el único camino de HTML al DOM en las superficies nuevas (Ver, VISTA PREVIA y R1) es `limpiar(contenido_html)` con el HTML saneado por el backend; no hay XSS por otra vía.
- Flujo sensible sin atajos: los cambios de tarifa y tope de daños pasan por la vista previa, `CONFIRMAR` y el registro, igual que el resto de parámetros sensibles.
- Carga de `.md`: UTF-8 estricto; un archivo que no lo cumple muestra el mensaje y el contenido no cambia.
- R1 bloqueado si la vista previa no corresponde al contenido actual; si la vista previa falla, no se abre y se publica solo lo que se ha visto.
- No bloqueantes (se corrigen en un retoque posterior): Reintentar del prellenado podía pisar lo escrito; faltaba prueba de HTML hostil en las superficies nuevas; anuncios encadenados en la región de estado.
- Menores: salto de nivel de encabezados si el texto empieza en `<h5>`; `bloquearEditor(false)` reactiva un botón.
- Ajuste 433d476: la vista previa acepta el mismo máximo que publicar (300 000 caracteres), en lugar de 200 000 como en la revisión D2 + E2.
