begin;
create extension if not exists pgtap with schema extensions;
select plan(72);

-- RF-17 (etapa A): textos legales versionados e inmutables y aceptaciones inmutables.
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli1@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000c2', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli2@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{}');
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';

select has_table('public', 'texto_legal', 'existe texto_legal');
select has_table('public', 'aceptacion', 'existe aceptacion');
select has_function('public', 'publicar_texto_legal', 'existe publicar_texto_legal');
select has_function('public', 'retirar_texto_legal', array['text', 'text'], 'existe retirar_texto_legal');
select has_function('public', 'textos_vigentes', 'existe textos_vigentes');
select has_function('public', 'aceptar_textos', array['text', 'jsonb'], 'existe aceptar_textos');
select has_function('public', 'insertar_aceptacion', 'existe insertar_aceptacion');
select hasnt_column('public', 'aceptacion', 'ip', 'no se guarda la IP (decision 6)');

-- Estado limpio (se deshace con el rollback): sin textos ni aceptaciones previas.
alter table public.aceptacion disable trigger user;
alter table public.texto_legal disable trigger user;
delete from public.aceptacion;
delete from public.texto_legal;
delete from public.notificacion where tipo = 'texto_legal_nuevo';
alter table public.aceptacion enable trigger user;
alter table public.texto_legal enable trigger user;

-- Administrador: publica.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.publicar_texto_legal('terminos_uso', '1.0.0', 'mayor', '# Terminos', '{"registro": "Resumen"}', null, now())$$,
  'el administrador publica la primera version');
reset role;
select is((select count(*)::int from public.notificacion where tipo = 'texto_legal_nuevo'), 0, 'la primera version no avisa a nadie');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.publicar_texto_legal('terminos_uso', '2.0.0', 'mayor', '# Terminos 2', '{}', 'Nuevos plazos', now() + interval '20 days')$$,
  'publica una mayor programada');
reset role;
select is((select count(*)::int from public.notificacion where tipo = 'texto_legal_nuevo'),
  (select count(*)::int from public.usuario where rol = 'cliente'), 'la mayor avisa a cada cliente');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
reset role;
select is((select datos ->> 'version' from public.notificacion where tipo = 'texto_legal_nuevo' limit 1), '2.0.0', 'el aviso lleva la version');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select throws_ok($$select public.publicar_texto_legal('terminos_uso', '2.1.0', 'menor', 'x', '{}', null, now() + interval '20 days')$$,
  'P0001', 'version_programada', 'solo una programada por texto');
select throws_ok($$select public.publicar_texto_legal('politica_privacidad', '1.0', 'mayor', 'x', '{}', null, now())$$,
  '23514', null, 'la version debe ser semantica');
select throws_ok($$select public.publicar_texto_legal('otro_texto', '1.0.0', 'mayor', 'x', '{}', null, now())$$,
  '23514', null, 'el tipo es de lista cerrada');
select throws_ok($$select public.publicar_texto_legal('politica_privacidad', '1.0.0', 'mayor', 'x', '{"cualquiera": "x"}', null, now())$$,
  '23514', null, 'los resumenes van por contexto conocido');
select lives_ok($$select public.publicar_texto_legal('politica_privacidad', '1.0.0', 'mayor', 'x', '{}', null, now())$$, 'otro texto publica aparte');
select throws_ok($$select public.publicar_texto_legal('politica_privacidad', '1.0.0', 'mayor', 'x', '{}', null, now())$$,
  '23505', null, 'una version no se repite');
select lives_ok($$select public.retirar_texto_legal('terminos_uso', '2.0.0')$$, 'retira la programada');
reset role;
select is((select count(*)::int from public.notificacion where tipo = 'texto_legal_nuevo'), 0, 'retirar la programada anula su aviso pendiente');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select throws_ok($$select public.retirar_texto_legal('terminos_uso', '1.0.0')$$, 'P0001', 'version_vigente', 'la vigente no se retira');
select throws_ok($$select public.retirar_texto_legal('terminos_uso', '9.9.9')$$, 'P0002', null, 'retirar lo inexistente');
select lives_ok($$select public.publicar_texto_legal('terminos_uso', '2.0.0', 'mayor', '# Terminos 2', '{}', 'Nuevos plazos', now() + interval '20 days')$$,
  'se puede publicar de nuevo tras retirar');
select is((select version from public.textos_vigentes() where tipo = 'terminos_uso'), '1.0.0', 'la programada no es vigente');
select is((select count(*)::int from public.textos_vigentes()), 2, 'una vigente por tipo publicado');

-- Nadie escribe directo: ni el administrador ni el cliente.
select throws_ok($$insert into public.texto_legal (tipo, version, tipo_cambio, contenido, vigente_desde) values ('terminos_uso', '3.0.0', 'mayor', 'x', now())$$, '42501', null, 'el administrador no inserta directo');
select throws_ok($$update public.texto_legal set contenido = 'x'$$, '42501', null, 'el administrador no edita');
select throws_ok($$delete from public.texto_legal$$, '42501', null, 'el administrador no borra');
reset role;

set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select throws_ok($$select public.publicar_texto_legal('terminos_uso', '5.0.0', 'mayor', 'x', '{}', null, now() + interval '20 days')$$, '42501', null, 'el cliente no publica');
select throws_ok($$select public.retirar_texto_legal('terminos_uso', '2.0.0')$$, '42501', null, 'el cliente no retira');
select throws_ok($$insert into public.texto_legal (tipo, version, tipo_cambio, contenido, vigente_desde) values ('terminos_uso', '3.0.0', 'mayor', 'x', now())$$, '42501', null, 'el cliente no inserta directo');
select throws_ok($$update public.texto_legal set contenido = 'x'$$, '42501', null, 'el cliente no edita');
select throws_ok($$delete from public.texto_legal$$, '42501', null, 'el cliente no borra');
select is((select count(*)::int from public.texto_legal), 3, 'el cliente lee los textos');
reset role;

set local role anon;
select is((select count(*)::int from public.texto_legal), 3, 'el visitante lee los textos');
reset role;

-- Inmutabilidad: tampoco el propietario edita una publicada ni borra una vigente.
select throws_ok($$update public.texto_legal set contenido = 'otro' where tipo = 'terminos_uso' and version = '1.0.0'$$, 'P0001', null, 'ni el propietario edita una version publicada');
select throws_ok($$delete from public.texto_legal where tipo = 'terminos_uso' and version = '1.0.0'$$, 'P0001', null, 'ni el propietario borra una vigente');
select throws_ok($$truncate public.texto_legal cascade$$, 'P0001', null, 'ni el propietario vacia los textos');

-- Aceptaciones.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select is((select count(*)::int from public.aceptar_textos('registro', '[{"tipo":"terminos_uso","version":"1.0.0"},{"tipo":"politica_privacidad","version":"1.0.0"}]')), 2, 'el cliente acepta la vigente');
select is((select count(*)::int from public.aceptar_textos('registro', '[{"tipo":"terminos_uso","version":"1.0.0"}]')), 1, 'repetir no duplica y devuelve la existente');
select is((select count(*)::int from public.aceptacion), 2, 'solo dos filas del cliente');
select throws_ok($$select public.aceptar_textos('registro', '[{"tipo":"terminos_uso","version":"2.0.0"}]')$$, 'P0001', 'texto_desactualizado', 'no se acepta una version que no es la vigente');
select throws_ok($$select public.aceptar_textos('reserva', '[{"tipo":"terminos_uso","version":"1.0.0"}]')$$, '22023', null, 'por esta via solo el contexto registro');
select throws_ok($$select public.aceptar_textos('registro', '[{"tipo":"condiciones_contratacion","version":"1.0.0"}]')$$, '22023', null, 'las condiciones no se aceptan en el registro');
select throws_ok($$insert into public.aceptacion (id_usuario, tipo, version, contexto) values ('00000000-0000-0000-0000-0000000000c1', 'terminos_uso', '1.0.0', 'reserva')$$, '42501', null, 'nadie inserta directo');
select throws_ok($$update public.aceptacion set retirada_en = now()$$, '42501', null, 'el cliente no edita aceptaciones');
select throws_ok($$delete from public.aceptacion$$, '42501', null, 'el cliente no borra aceptaciones');
select throws_ok($$select public.insertar_aceptacion('00000000-0000-0000-0000-0000000000c1', 'terminos_uso', '1.0.0', 'reserva', null, null)$$, '42501', null, 'la insercion interna no se llama desde la API');
reset role;

set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c2","role":"authenticated"}', true);
select is((select count(*)::int from public.aceptacion), 0, 'otro cliente no ve las aceptaciones ajenas');
reset role;

set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select is((select count(*)::int from public.aceptacion), 2, 'el administrador ve todas');
select throws_ok($$update public.aceptacion set retirada_en = now()$$, '42501', null, 'el administrador no edita aceptaciones');
select throws_ok($$delete from public.aceptacion$$, '42501', null, 'el administrador no borra aceptaciones');
reset role;
set local role anon;
select throws_ok($$select count(*) from public.aceptacion$$, '42501', null, 'el visitante no lee aceptaciones');
reset role;

-- Inmutabilidad de aceptaciones, tambien para el propietario; solo se retira un consentimiento opcional.
select throws_ok($$update public.aceptacion set version = '0.0.1'$$, 'P0001', null, 'ni el propietario edita una aceptacion');
select throws_ok($$delete from public.aceptacion$$, 'P0001', null, 'ni el propietario borra una aceptacion');
select throws_ok($$update public.aceptacion set retirada_en = now() where contexto = 'registro'$$, '23514', null, 'el registro no se retira');
select lives_ok($$select public.insertar_aceptacion('00000000-0000-0000-0000-0000000000c1', 'politica_privacidad', '1.0.0', 'promociones', null, null)$$, 'la funcion interna registra una promocion');
select lives_ok($$update public.aceptacion set retirada_en = now() where contexto = 'promociones'$$, 'un consentimiento opcional se retira');
select throws_ok($$update public.aceptacion set retirada_en = null where contexto = 'promociones'$$, 'P0001', null, 'el retiro no se deshace');

-- La baja de la cuenta (derecho de supresion) si arrastra sus aceptaciones.
select lives_ok($$delete from auth.users where id = '00000000-0000-0000-0000-0000000000c1'$$, 'borrar la cuenta borra sus aceptaciones');
select is((select count(*)::int from public.aceptacion), 0, 'no quedan aceptaciones de la cuenta borrada');

-- Correcciones de la auditoria: tope de cifras de la version y reglas de CA-02 en la propia funcion.
select throws_ok($$insert into public.texto_legal (tipo, version, tipo_cambio, contenido, vigente_desde) values ('condiciones_contratacion', '1.0.3000000000', 'parche', 'x', now())$$,
  '23514', null, 'una parte de la version no pasa de nueve cifras');
select throws_ok($$insert into public.texto_legal (tipo, version, tipo_cambio, contenido, vigente_desde) values ('condiciones_contratacion', '3000000000.0.0', 'mayor', 'x', now())$$,
  '23514', null, 'tampoco la parte mayor');
select lives_ok($$insert into public.texto_legal (tipo, version, tipo_cambio, contenido, vigente_desde) values ('condiciones_contratacion', '999999999.999999999.999999999', 'mayor', 'x', now() + interval '1 day')$$,
  'nueve cifras si caben');
select lives_ok($$delete from public.texto_legal where tipo = 'condiciones_contratacion'$$, 'se retira la programada de prueba');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select throws_ok($$select public.publicar_texto_legal('condiciones_contratacion', '1.0.3000000000', 'parche', 'x', '{}', null, now())$$,
  '23514', null, 'publicar una version enorme falla antes de dejar nada');
select lives_ok($$select public.publicar_texto_legal('condiciones_contratacion', '1.0.0', 'mayor', 'x', '{}', null, now() - interval '3 days')$$,
  'la primera version puede regir ya, con fecha pasada');
select throws_ok($$select public.publicar_texto_legal('condiciones_contratacion', '0.9.0', 'mayor', 'x', '{}', null, now() + interval '20 days')$$,
  'P0001', 'version_invalida', 'una version inferior no se publica por SQL');
select throws_ok($$select public.publicar_texto_legal('condiciones_contratacion', '1.1.0', 'mayor', 'x', '{}', null, now() + interval '20 days')$$,
  'P0001', 'version_invalida', 'la version debe ser coherente con el tipo de cambio');
select throws_ok($$select public.publicar_texto_legal('condiciones_contratacion', '2.0.0', 'mayor', 'x', '{}', null, now() - interval '1 day')$$,
  'P0001', 'aviso_insuficiente', 'una mayor con fecha pasada no se publica por SQL');
select throws_ok($$select public.publicar_texto_legal('condiciones_contratacion', '1.1.0', 'menor', 'x', '{}', null, now() + interval '14 days')$$,
  'P0001', 'aviso_insuficiente', 'una menor exige 15 dias de aviso');
select * from finish();
rollback;
