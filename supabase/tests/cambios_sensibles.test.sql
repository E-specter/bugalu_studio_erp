begin;
create extension if not exists pgtap with schema extensions;
select plan(27);

-- RF-20 (2/2): confirmaciones de cambios sensibles (token de un solo uso) y registro de cambios inmutable.
-- La barrera de los campos sensibles y el flujo completo estan en barrera_sensibles.test.sql.
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000ae', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ae@t.pe', '{}');
update public.usuario set rol = 'administrador', nombre = 'Ana Admin' where id = '00000000-0000-0000-0000-0000000000ad';
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ae';

select has_table('public', 'confirmacion_cambio', 'existe confirmacion_cambio');
select has_table('public', 'registro_cambio', 'existe registro_cambio');
select has_function('public', 'aplicar_cambio_confirmado', array['uuid'], 'existe aplicar_cambio_confirmado');
select has_function('public', 'confirmacion_para_aplicar', array['text'], 'existe confirmacion_para_aplicar');

-- El administrador A previsualiza: guarda su propia confirmacion con crear_confirmacion.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.crear_confirmacion('hash-a', 'impuestos', null, 'Impuestos',
  '{"porcentaje_igv": {"anterior": "18.00", "nuevo": "10.00"}}', 10)$$, 'el administrador guarda su confirmacion');
select throws_ok($$select public.crear_confirmacion('hash-x', 'impuestos', null, 'Impuestos', '{}', 0)$$, '22023', null, 'la vigencia va de 1 a 60 minutos');
select throws_ok($$update public.confirmacion_cambio set usada_en = now()$$, '42501', null, 'nadie marca usada una confirmacion sin la funcion');
select throws_ok($$delete from public.confirmacion_cambio$$, '42501', null, 'nadie borra confirmaciones');
select is((select count(*)::int from public.confirmacion_cambio), 1, 'A ve su confirmacion');
select is((select (public.confirmacion_para_aplicar('hash-a')).vigente), true, 'la confirmacion de A esta vigente');
reset role;
select is((select id_autor from public.confirmacion_cambio where hash_token = 'hash-a'), '00000000-0000-0000-0000-0000000000ad'::uuid, 'la confirmacion queda a nombre de quien la crea');

-- B (otro administrador) no ve la de A ni la aplica.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ae","role":"authenticated"}', true);
select is((select count(*)::int from public.confirmacion_cambio), 0, 'B no ve la confirmacion de A');
select is((select id_autor from public.confirmacion_para_aplicar('hash-a')), '00000000-0000-0000-0000-0000000000ad'::uuid, 'B ve de quien es la confirmacion (el backend responde 403)');
select throws_ok($$select public.aplicar_cambio_confirmado((select id from public.confirmacion_para_aplicar('hash-a')))$$, '55000', null, 'B no aplica la confirmacion de A');
reset role;

-- Un cliente no hace nada.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select throws_ok($$select public.aplicar_cambio_confirmado(gen_random_uuid())$$, '42501', null, 'el cliente no aplica cambios');
select throws_ok($$select * from public.confirmacion_para_aplicar('hash-a')$$, '42501', null, 'el cliente no ve confirmaciones');
select throws_ok($$insert into public.registro_cambio (id_autor, autor_nombre, recurso, nombre_recurso, campo, anterior, nuevo)
  values ('00000000-0000-0000-0000-0000000000c1', 'x', 'impuestos', 'x', 'c', 'a', 'b')$$, '42501', null, 'nadie inserta directo en el registro');
select is((select count(*)::int from public.registro_cambio), 0, 'el cliente no lee el registro');
reset role;

-- A aplica: una fila por campo y la confirmacion queda usada.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.aplicar_cambio_confirmado((select id from public.confirmacion_para_aplicar('hash-a')))$$, 'A aplica su confirmacion');
select is((select count(*)::int from public.registro_cambio where id_autor = '00000000-0000-0000-0000-0000000000ad'), 1, 'una fila por campo cambiado');
select is((select (public.confirmacion_para_aplicar('hash-a')).vigente), false, 'la confirmacion usada ya no esta vigente');
reset role;

-- Inmutabilidad: ni el administrador de la API ni la base (propietario) editan o borran.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select throws_ok($$update public.registro_cambio set nuevo = 'x'$$, '42501', null, 'el administrador no edita el registro');
select throws_ok($$delete from public.registro_cambio$$, '42501', null, 'el administrador no borra el registro');
reset role;
select throws_ok($$update public.registro_cambio set nuevo = 'x'$$, 'P0001', null, 'ni el propietario edita el registro');
select throws_ok($$delete from public.registro_cambio$$, 'P0001', null, 'ni el propietario borra el registro');
select throws_ok($$truncate public.registro_cambio$$, 'P0001', null, 'ni el propietario vacia el registro');

-- Una confirmacion vencida no se aplica.
insert into public.confirmacion_cambio (id, hash_token, id_autor, recurso, nombre_recurso, cambios, creada_en, expira_en)
values ('00000000-0000-0000-0000-00000000a002', 'hash-v', '00000000-0000-0000-0000-0000000000ad', 'impuestos', 'Impuestos',
  '{"porcentaje_igv": {"anterior": "10.00", "nuevo": "9.00"}}', now() - interval '20 minutes', now() - interval '10 minutes');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select throws_ok($$select public.aplicar_cambio_confirmado('00000000-0000-0000-0000-00000000a002')$$, '55000', null, 'una confirmacion vencida no se aplica');
reset role;

select * from finish();
rollback;
