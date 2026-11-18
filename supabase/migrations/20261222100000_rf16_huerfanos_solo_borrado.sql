-- Auditoria A de RF-16, ronda 3: las politicas de `anon` sobre los huerfanos valian para cualquier operacion (listar,
-- descargar, firmar). Ahora solo valen mientras Storage ejecuta un DELETE.
drop policy reclamaciones_lee_huerfana on storage.objects;
drop policy reclamaciones_borra_huerfana on storage.objects;

create policy reclamaciones_lee_huerfana on storage.objects for select to anon
  using (bucket_id = 'reclamaciones' and storage.operation() = 'storage.object.delete'
         and public.subida_reclamacion_huerfana(name));
create policy reclamaciones_borra_huerfana on storage.objects for delete to anon
  using (bucket_id = 'reclamaciones' and storage.operation() = 'storage.object.delete'
         and public.subida_reclamacion_huerfana(name));
