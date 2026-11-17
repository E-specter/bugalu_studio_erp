begin;
create extension if not exists pgtap with schema extensions;
select plan(43);

-- RF-17 (etapa A): perfil reforzado, documento repetido, pendientes, consentimientos y aceptacion de condiciones.
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000d1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'pr1@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000d2', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'pr2@t.pe', '{}');

select hasnt_column('public', 'usuario', 'documento_repetido', 'la marca ya no se guarda: se calcula al leer');
select has_column('public', 'usuario', 'integrantes', 'usuario.integrantes');
select has_column('public', 'aceptacion', 'consentimiento', 'aceptacion.consentimiento');
select has_function('public', 'mis_pendientes', 'existe mis_pendientes');
select has_function('public', 'cambiar_consentimiento', array['text', 'boolean'], 'existe cambiar_consentimiento');
select has_function('public', 'aceptar_condiciones', array['text', 'uuid', 'text'], 'existe aceptar_condiciones');

-- Textos vigentes limpios (se deshace con el rollback).
alter table public.aceptacion disable trigger user;
alter table public.texto_legal disable trigger user;
delete from public.aceptacion;
delete from public.texto_legal;
alter table public.aceptacion enable trigger user;
alter table public.texto_legal enable trigger user;
insert into public.texto_legal (tipo, version, tipo_cambio, contenido, resumenes, vigente_desde) values
  ('terminos_uso', '1.0.0', 'mayor', 'T', '{}', now() - interval '1 day'),
  ('politica_privacidad', '1.0.0', 'mayor', 'P', '{}', now() - interval '1 day'),
  ('condiciones_contratacion', '1.0.0', 'mayor', 'C', '{}', now() - interval '1 day'),
  ('declaracion_agrupacion', '1.0.0', 'mayor', 'D', '{}', now() - interval '1 day');

-- Restricciones del perfil (como propietario de la tabla).
select throws_ok($$update public.usuario set documento_tipo = 'dni', documento_numero = '1234' where id = '00000000-0000-0000-0000-0000000000d1'$$,
  '23514', null, 'el DNI tiene 8 cifras');
select throws_ok($$update public.usuario set documento_tipo = 'ce', documento_numero = 'ab123456' where id = '00000000-0000-0000-0000-0000000000d1'$$,
  '23514', null, 'el CE va en mayusculas');
select throws_ok($$update public.usuario set documento_tipo = 'pasaporte' where id = '00000000-0000-0000-0000-0000000000d1'$$,
  '23514', null, 'tipo y numero van juntos');
select throws_ok($$update public.usuario set modalidad = 'banda' where id = '00000000-0000-0000-0000-0000000000d1'$$,
  '23514', null, 'modalidad de lista cerrada');
select throws_ok($$update public.usuario set domicilio = repeat('x', 201) where id = '00000000-0000-0000-0000-0000000000d1'$$,
  '23514', null, 'domicilio hasta 200');
select throws_ok($$update public.usuario set redes = '[1,2,3,4,5,6]' where id = '00000000-0000-0000-0000-0000000000d1'$$,
  '23514', null, 'hasta 5 redes');
select throws_ok($$update public.usuario set integrantes = (select jsonb_agg('{"nombre":"a","rol":"b"}'::jsonb) from generate_series(1, 21)) where id = '00000000-0000-0000-0000-0000000000d1'$$,
  '23514', null, 'hasta 20 integrantes');

-- El cliente edita lo suyo, no el marcador ni lo ajeno.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000d1","role":"authenticated"}', true);
select lives_ok($$update public.usuario set modalidad = 'agrupacion', documento_tipo = 'dni', documento_numero = '12345678', domicilio = 'Av. Lima 1', redes = '[{"red":"instagram","valor":"@x"}]', integrantes = '[{"nombre":"A","rol":"voz"}]', es_menor = false where id = '00000000-0000-0000-0000-0000000000d1'$$,
  'el cliente edita su perfil reforzado');
select hasnt_trigger('public', 'usuario', 'usuario_documento_repetido', 'sin trigger que toque filas ajenas');
update public.usuario set domicilio = 'HACKEADO' where id = '00000000-0000-0000-0000-0000000000d2';
reset role;
select is((select domicilio from public.usuario where id = '00000000-0000-0000-0000-0000000000d2'), null, 'el perfil ajeno queda intacto');

-- Documento repetido: no bloquea, marca a ambos; se recalcula.
update public.usuario set documento_tipo = 'dni', documento_numero = '12345678' where id = '00000000-0000-0000-0000-0000000000d2';
select is((select count(*)::int from public.usuario u where u.id in ('00000000-0000-0000-0000-0000000000d1', '00000000-0000-0000-0000-0000000000d2') and exists (select 1 from public.usuario o where o.documento_tipo = u.documento_tipo and o.documento_numero = u.documento_numero and o.id <> u.id)), 2, 'ambas cuentas quedan marcadas');
update public.usuario set documento_numero = '87654321' where id = '00000000-0000-0000-0000-0000000000d2';
select is((select count(*)::int from public.usuario u where u.id in ('00000000-0000-0000-0000-0000000000d1', '00000000-0000-0000-0000-0000000000d2') and exists (select 1 from public.usuario o where o.documento_tipo = u.documento_tipo and o.documento_numero = u.documento_numero and o.id <> u.id)), 0, 'al cambiar el documento se desmarcan');
update public.usuario set documento_tipo = 'ce', documento_numero = '12345678' where id = '00000000-0000-0000-0000-0000000000d2';
select is((select count(*)::int from public.usuario u where u.id in ('00000000-0000-0000-0000-0000000000d1', '00000000-0000-0000-0000-0000000000d2') and exists (select 1 from public.usuario o where o.documento_tipo = u.documento_tipo and o.documento_numero = u.documento_numero and o.id <> u.id)), 0, 'otro tipo no es el mismo documento');

-- Pendientes: agrupacion sin aceptar nada.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000d1","role":"authenticated"}', true);
select is((select array_agg(tipo order by tipo) from public.mis_pendientes()),
  array['declaracion_agrupacion', 'politica_privacidad', 'terminos_uso'], 'faltan terminos, politica y declaracion');
select is((select motivo from public.mis_pendientes() where tipo = 'terminos_uso'), 'registro_pendiente', 'motivo de lo no aceptado');
select lives_ok($$select * from public.aceptar_textos('registro', '[{"tipo":"terminos_uso","version":"1.0.0"},{"tipo":"politica_privacidad","version":"1.0.0"},{"tipo":"declaracion_agrupacion","version":"1.0.0"}]')$$,
  'acepta el registro junto con la declaracion');
select is((select count(*)::int from public.mis_pendientes()), 0, 'sin pendientes tras aceptar');
reset role;
select is((select count(*)::int from public.aceptacion where id_usuario = '00000000-0000-0000-0000-0000000000d1' and tipo = 'declaracion_agrupacion' and contexto = 'registro'), 1,
  'la declaracion queda en contexto registro');

-- Una menor o la politica mayor no piden nada; una mayor de terminos si.
insert into public.texto_legal (tipo, version, tipo_cambio, contenido, resumenes, vigente_desde) values
  ('terminos_uso', '1.1.0', 'menor', 'T', '{}', now() - interval '1 hour'),
  ('politica_privacidad', '2.0.0', 'mayor', 'P', '{}', now() - interval '1 hour');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000d1","role":"authenticated"}', true);
select is((select count(*)::int from public.mis_pendientes()), 0, 'menor y la politica mayor no piden aceptar');
reset role;
insert into public.texto_legal (tipo, version, tipo_cambio, contenido, resumenes, vigente_desde) values
  ('terminos_uso', '2.0.0', 'mayor', 'T', '{}', now() - interval '1 minute');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000d1","role":"authenticated"}', true);
select results_eq($$select tipo, version, contexto, motivo from public.mis_pendientes()$$,
  $$values ('terminos_uso', '2.0.0', 'registro', 'version_mayor')$$, 'la mayor de terminos queda pendiente');
-- El otro cliente (individual, sin nada aceptado): terminos y politica, no la declaracion.
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000d2","role":"authenticated"}', true);
select is((select array_agg(tipo order by tipo) from public.mis_pendientes()), array['politica_privacidad', 'terminos_uso'], 'el individual no debe la declaracion');

-- Consentimientos opcionales.
select lives_ok($$select public.cambiar_consentimiento('promociones_correo', true)$$, 'da promociones por correo');
select lives_ok($$select public.cambiar_consentimiento('promociones_correo', true)$$, 'repetir no duplica');
select lives_ok($$select public.cambiar_consentimiento('fotos_videos', true)$$, 'da fotos y videos');
select throws_ok($$select public.cambiar_consentimiento('otro', true)$$, '22023', null, 'consentimiento de lista cerrada');
reset role;
select is((select version from public.aceptacion where consentimiento = 'promociones_correo' and id_usuario = '00000000-0000-0000-0000-0000000000d2'), '2.0.0',
  'promociones usa la version vigente de la politica');
select is((select tipo from public.aceptacion where consentimiento = 'fotos_videos' and id_usuario = '00000000-0000-0000-0000-0000000000d2'), 'condiciones_contratacion',
  'los usos promocionales usan las condiciones');
select is((select count(*)::int from public.aceptacion where consentimiento = 'promociones_correo' and id_usuario = '00000000-0000-0000-0000-0000000000d2'), 1, 'una sola aceptacion activa');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000d2","role":"authenticated"}', true);
select lives_ok($$select public.cambiar_consentimiento('promociones_correo', false)$$, 'retira');
select lives_ok($$select public.cambiar_consentimiento('promociones_correo', true)$$, 'volver a darlo');
reset role;
select is((select count(*)::int from public.aceptacion where consentimiento = 'promociones_correo' and id_usuario = '00000000-0000-0000-0000-0000000000d2'), 2, 'volver a darlo crea otra aceptacion');
select is((select count(*)::int from public.aceptacion where consentimiento = 'promociones_correo' and retirada_en is not null and id_usuario = '00000000-0000-0000-0000-0000000000d2'), 1, 'la anterior conserva su retiro');

-- Condiciones de reserva y de pago (el camino feliz lo cubren las pruebas de la API).
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000d2","role":"authenticated"}', true);
select throws_ok($$select public.aceptar_condiciones('reserva', gen_random_uuid(), '9.9.9')$$, 'P0001', 'texto_desactualizado', 'solo la version vigente');
select throws_ok($$select public.aceptar_condiciones('reserva', gen_random_uuid(), '1.0.0')$$, '42501', null, 'la operacion ajena o inexistente no se acepta');
select throws_ok($$select public.insertar_aceptacion('00000000-0000-0000-0000-0000000000d2', 'terminos_uso', '2.0.0', 'registro', null, null)$$,
  '42501', null, 'insertar_aceptacion sigue sin ser llamable');
reset role;

-- Datos que faltan para reservar (nombre, documento y telefono).
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000d2","role":"authenticated"}', true);
select is(public.campos_faltantes_para_reservar(), array['nombre', 'telefono'], 'faltan nombre y telefono');
reset role;
update public.usuario set nombre = 'Ana', telefono = '999888777' where id = '00000000-0000-0000-0000-0000000000d2';
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000d2","role":"authenticated"}', true);
select is(public.campos_faltantes_para_reservar(), array[]::text[], 'perfil completo');
reset role;

select * from finish();
rollback;
