-- La API de Storage lee el objeto antes de borrarlo, con el rol de quien llama: sin esta politica el DELETE de `anon`
-- da 400. Solo las huerfanas (subida caducada hace mas de una hora, sin adjunto), cuyas rutas son aleatorias.
create policy reclamaciones_lee_huerfana on storage.objects for select to anon
  using (bucket_id = 'reclamaciones' and public.subida_reclamacion_huerfana(name));
