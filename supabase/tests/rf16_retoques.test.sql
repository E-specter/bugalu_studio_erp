begin;
create extension if not exists pgtap with schema extensions;
select plan(34);

-- RF-16, retoques de la auditoria A (ronda 2): limite por /64, clave de envio con todo el contenido, avisos con los
-- adjuntos guardados, adjuntos no guardados en el reintento y huerfanos de Storage.
create function public.zz_datos(p jsonb default '{}') returns jsonb language sql as $$
  select jsonb_build_object('nombre', 'Ana Prueba', 'tipo_documento', 'dni', 'documento', '12345678',
    'domicilio', 'Av. Lima 123', 'telefono', '987654321', 'correo', 'ana@t.pe', 'es_menor', false,
    'bien_tipo', 'servicio', 'tipo', 'reclamo', 'detalle', 'El servicio no fue el pactado.',
    'pedido', 'Quiero la devolucion.', 'medio_respuesta', 'correo') || p
$$;
grant execute on function public.zz_datos(jsonb) to anon, authenticated;

insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{}');
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';
alter table public.hoja_reclamacion disable trigger user;
alter table public.adjunto_reclamacion disable trigger user;
delete from public.adjunto_reclamacion;
delete from public.hoja_reclamacion;
delete from public.intento_reclamacion;
delete from public.notificacion;
alter table public.hoja_reclamacion enable trigger user;
alter table public.adjunto_reclamacion enable trigger user;

-- 1. Limite por IP: IPv6 se agrupa por /64 (IPv4 por direccion).
set local role anon;
select lives_ok($$select public.registrar_hoja(gen_random_uuid(), public.zz_datos(), '[]', '2001:db8:1:2::' || g, false) from generate_series(1, 5) g$$,
  'cinco hojas desde cinco direcciones de una misma /64');
select throws_ok($$select public.registrar_hoja(gen_random_uuid(), public.zz_datos(), '[]', '2001:db8:1:2:ffff:ffff:ffff:ffff', false)$$,
  'P0001', 'demasiadas_solicitudes', 'otra direccion de la misma /64 cuenta como la misma conexion');
select lives_ok($$select public.registrar_hoja(gen_random_uuid(), public.zz_datos(), '[]', '2001:db8:1:3::1', false)$$,
  'otra /64 no se ve afectada');
select lives_ok($$select public.registrar_hoja(gen_random_uuid(), public.zz_datos(), '[]', 'no-es-una-ip', false)$$,
  'un texto que no es IP no rompe el alta');
reset role;
select is((select count(*)::int from public.intento_reclamacion where ip_hash like '%2001%' or ip_hash like '%:%'), 0, 'no se guarda la IP en claro');

-- 2. Clave de envio: solo es reintento si coincide todo el contenido.
set local role anon;
select lives_ok($$select public.registrar_hoja('33333333-0000-0000-0000-000000000001', public.zz_datos(), '[]', '7.7.6.1', false, 'cccccccc-1111-0000-0000-000000000001')$$,
  'primer envio con clave');
select is((select r_repetida from public.registrar_hoja(gen_random_uuid(), public.zz_datos(), '[]', '7.7.6.2', false, 'cccccccc-1111-0000-0000-000000000001')), true,
  'mismo contenido: es el reintento');
select is((select r_repetida from public.registrar_hoja(gen_random_uuid(), public.zz_datos('{"nombre": "Otra Persona"}'), '[]', '7.7.6.3', false, 'cccccccc-1111-0000-0000-000000000001')), false,
  'otro nombre con la misma clave: hoja nueva');
select is((select r_repetida from public.registrar_hoja(gen_random_uuid(), public.zz_datos('{"descripcion": "Un detalle mas"}'), '[]', '7.7.6.4', false, 'cccccccc-1111-0000-0000-000000000001')), false,
  'un campo extra con la misma clave: hoja nueva');
select is((select r_repetida from public.registrar_hoja(gen_random_uuid(), public.zz_datos('{"monto": 50}'), '[]', '7.7.6.5', false, 'cccccccc-1111-0000-0000-000000000001')), false,
  'otro monto con la misma clave: hoja nueva');
reset role;

-- 3. Avisos: solo los adjuntos guardados; la hoja con adjuntos espera a que termine la subida.
set local role anon;
select lives_ok($$select public.registrar_hoja('44444444-0000-0000-0000-000000000001', public.zz_datos(),
  '[{"nombre": "a.pdf", "tipo": "application/pdf", "tamano": 10}, {"nombre": "b.png", "tipo": "image/png", "tamano": 20}]',
  '8.8.1.1', false, 'cccccccc-1111-0000-0000-000000000002')$$, 'alta con dos adjuntos declarados');
reset role;
select is((select datos -> 'adjuntos' from public.notificacion where tipo = 'reclamacion_registrada' and datos ->> 'id' = '44444444-0000-0000-0000-000000000001'),
  '[]'::jsonb, 'antes de subir, la copia no lista adjuntos');
select is((select (datos ->> 'adjuntos_no_guardados')::int from public.notificacion where tipo = 'reclamacion_registrada' and datos ->> 'id' = '44444444-0000-0000-0000-000000000001'),
  2, 'y cuenta los dos como no guardados si nadie la completa');
select cmp_ok((select enviar_desde from public.notificacion where tipo = 'reclamacion_registrada' and datos ->> 'id' = '44444444-0000-0000-0000-000000000001'),
  '>', now() + interval '4 minutes', 'el aviso espera a que termine la subida');
select is((select count(*)::int from public.notificacion where datos ->> 'id' <> '44444444-0000-0000-0000-000000000001'
  and tipo like 'reclamacion_%' and enviar_desde > now() + interval '1 minute'), 0, 'sin adjuntos el aviso sale enseguida');

select set_config('zz.ruta1', (select ruta from public.subida_reclamacion where id_hoja = '44444444-0000-0000-0000-000000000001' and n = 1), false);
set local role anon;
insert into storage.objects (bucket_id, name) values ('reclamaciones', current_setting('zz.ruta1'));
select public.confirmar_adjunto(current_setting('zz.ruta1'));
select lives_ok($$select public.avisar_hoja('44444444-0000-0000-0000-000000000001')$$, 'anon cierra la hoja tras las subidas');
reset role;
select is((select datos -> 'adjuntos' from public.notificacion where tipo = 'reclamacion_registrada' and datos ->> 'id' = '44444444-0000-0000-0000-000000000001'),
  '["a.pdf"]'::jsonb, 'la copia lista solo el adjunto guardado');
select is((select (datos ->> 'adjuntos_no_guardados')::int from public.notificacion where tipo = 'reclamacion_registrada' and datos ->> 'id' = '44444444-0000-0000-0000-000000000001'),
  1, 'y dice cuantos no se guardaron');
select is((select (datos ->> 'adjuntos')::int || '/' || (datos ->> 'adjuntos_no_guardados') from public.notificacion where tipo = 'reclamacion_recibida' and datos ->> 'id' = '44444444-0000-0000-0000-000000000001'),
  '1/1', 'el aviso al Administrador cuenta guardados y no guardados');
select cmp_ok((select max(enviar_desde) from public.notificacion where datos ->> 'id' = '44444444-0000-0000-0000-000000000001'), '<=', now(),
  'los dos avisos quedan listos para enviar');

-- 4. El 200 del reintento informa los adjuntos que no se guardaron.
set local role anon;
select lives_ok($$select public.registrar_hoja('55555555-0000-0000-0000-000000000001', public.zz_datos('{"nombre": "Con adjuntos"}'),
  '[{"nombre": "a.pdf", "tipo": "application/pdf", "tamano": 10}, {"nombre": "b.png", "tipo": "image/png", "tamano": 20}]',
  '8.8.2.1', false, 'cccccccc-1111-0000-0000-000000000003')$$, 'alta con clave y dos adjuntos');
reset role;
select set_config('zz.ruta2', (select ruta from public.subida_reclamacion where id_hoja = '55555555-0000-0000-0000-000000000001' and n = 1), false);
set local role anon;
insert into storage.objects (bucket_id, name) values ('reclamaciones', current_setting('zz.ruta2'));
select public.confirmar_adjunto(current_setting('zz.ruta2'));
select is((select r_existente -> 'adjuntos_no_guardados' from public.registrar_hoja(gen_random_uuid(), public.zz_datos('{"nombre": "Con adjuntos"}'),
  '[{"nombre": "a.pdf", "tipo": "application/pdf", "tamano": 10}, {"nombre": "b.png", "tipo": "image/png", "tamano": 20}]',
  '8.8.2.2', false, 'cccccccc-1111-0000-0000-000000000003')), '[2]'::jsonb, 'el reintento dice que el adjunto 2 no se guardo');
select is((select r_existente -> 'adjuntos_no_guardados' from public.registrar_hoja(gen_random_uuid(), public.zz_datos(), '[]', '8.8.2.3', false, 'cccccccc-1111-0000-0000-000000000001')),
  '[]'::jsonb, 'una hoja sin adjuntos declarados no tiene no guardados');
reset role;

-- 5. Huerfanos: la subida terminada sin confirmar, ya caducada, la limpia el backend en Storage y luego la base.
select has_function('public', 'rutas_huerfanas_reclamacion', 'existe rutas_huerfanas_reclamacion');
select ok(exists (select 1 from pg_policies where schemaname = 'storage' and tablename = 'objects' and policyname = 'reclamaciones_borra_huerfana' and cmd = 'DELETE' and roles = '{anon}'),
  'anon solo borra del bucket por la politica de huerfanas');
select ok(exists (select 1 from pg_policies where schemaname = 'storage' and policyname = 'reclamaciones_lee_huerfana' and cmd = 'SELECT' and roles = '{anon}'),
  'y la lee para que Storage pueda borrarla');
select set_config('zz.ruta3', (select ruta from public.subida_reclamacion where id_hoja = '55555555-0000-0000-0000-000000000001' and n = 2), false);
insert into storage.objects (bucket_id, name) values ('reclamaciones', current_setting('zz.ruta3'));
select is((select count(*)::int from public.rutas_huerfanas_reclamacion()), 0, 'una subida vigente no es huerfana');
update public.subida_reclamacion set caduca_en = now() - interval '2 hours' where ruta = current_setting('zz.ruta3');
select is((select array_agg(r) from public.rutas_huerfanas_reclamacion() r), array[current_setting('zz.ruta3')], 'caducada, con objeto y sin adjunto: es huerfana');
select is(public.limpiar_subidas_reclamacion(), 0, 'la limpieza no borra la subida mientras el objeto siga en Storage');
set local role anon;
select throws_ok($$select public.rutas_huerfanas_reclamacion()$$, '42501', null, 'anon no lista huerfanas');
select is((select count(*)::int from storage.objects where bucket_id = 'reclamaciones'), 1, 'anon solo lee la huerfana, no los objetos vigentes');
select is(public.subida_reclamacion_huerfana(current_setting('zz.ruta3')), true, 'la politica de borrado de anon reconoce la huerfana');
select is(public.subida_reclamacion_huerfana(current_setting('zz.ruta2')), false, 'y no una ya confirmada');
reset role;
select set_config('storage.allow_delete_query', 'true', true);
delete from storage.objects where bucket_id = 'reclamaciones' and name = current_setting('zz.ruta3');
select is(public.limpiar_subidas_reclamacion(), 1, 'sin objeto, la limpieza borra la subida caducada');

select * from finish();
rollback;
