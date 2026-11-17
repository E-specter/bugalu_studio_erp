begin;
create extension if not exists pgtap with schema extensions;
select plan(28);

-- RF-20 (2/2): confirmaciones de cambios sensibles (token de un solo uso) y registro de cambios inmutable.
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000ae', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ae@t.pe', '{}');
update public.usuario set rol = 'administrador', nombre = 'Ana Admin' where id = '00000000-0000-0000-0000-0000000000ad';
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ae';

select has_table('public', 'confirmacion_cambio', 'existe confirmacion_cambio');
select has_table('public', 'registro_cambio', 'existe registro_cambio');
select has_function('public', 'registrar_cambios', array['uuid'], 'existe registrar_cambios');
select has_function('public', 'confirmacion_para_aplicar', array['text'], 'existe confirmacion_para_aplicar');

-- El administrador A previsualiza: guarda su propia confirmacion.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$insert into public.confirmacion_cambio (id, hash_token, id_autor, recurso, nombre_recurso, cambios, expira_en)
  values ('00000000-0000-0000-0000-00000000a001', 'hash-a', '00000000-0000-0000-0000-0000000000ad', 'impuestos', 'Impuestos',
    '{"porcentaje_igv": {"anterior": "18.00", "nuevo": "10.00"}}', now() + interval '10 minutes')$$, 'el administrador guarda su confirmacion');
select throws_ok($$insert into public.confirmacion_cambio (hash_token, id_autor, recurso, nombre_recurso, cambios, expira_en)
  values ('hash-x', '00000000-0000-0000-0000-0000000000ae', 'impuestos', 'Impuestos', '{}', now() + interval '10 minutes')$$,
  '42501', null, 'no guarda confirmaciones a nombre de otro');
select throws_ok($$update public.confirmacion_cambio set usada_en = now()$$, '42501', null, 'nadie marca usada una confirmacion sin la funcion');
select throws_ok($$delete from public.confirmacion_cambio$$, '42501', null, 'nadie borra confirmaciones');
select is((select count(*)::int from public.confirmacion_cambio), 1, 'A ve su confirmacion');
select is((select (public.confirmacion_para_aplicar('hash-a')).vigente), true, 'la confirmacion de A esta vigente');
reset role;

-- B (otro administrador) no ve la de A ni la toma.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ae","role":"authenticated"}', true);
select is((select count(*)::int from public.confirmacion_cambio), 0, 'B no ve la confirmacion de A');
select is((select id_autor from public.confirmacion_para_aplicar('hash-a')), '00000000-0000-0000-0000-0000000000ad'::uuid, 'B ve de quien es la confirmacion (el backend responde 403)');
select throws_ok($$select public.registrar_cambios('00000000-0000-0000-0000-00000000a001')$$, '55000', null, 'B no registra la confirmacion de A');
reset role;

-- Un cliente no hace nada.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select throws_ok($$select public.registrar_cambios('00000000-0000-0000-0000-00000000a001')$$, '42501', null, 'el cliente no registra cambios');
select throws_ok($$insert into public.registro_cambio (id_autor, autor_nombre, recurso, nombre_recurso, campo, anterior, nuevo)
  values ('00000000-0000-0000-0000-0000000000c1', 'x', 'impuestos', 'x', 'c', 'a', 'b')$$, '42501', null, 'nadie inserta directo en el registro');
select is((select count(*)::int from public.registro_cambio), 0, 'el cliente no lee el registro');
reset role;

-- A confirma: registrar_cambios escribe una fila por campo y marca usada la confirmacion.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.registrar_cambios('00000000-0000-0000-0000-00000000a001')$$, 'A registra su confirmacion');
select is((select count(*)::int from public.registro_cambio where id_autor = '00000000-0000-0000-0000-0000000000ad'), 1, 'una fila por campo cambiado');
select is((select autor_nombre || ':' || campo || ':' || anterior || ':' || nuevo from public.registro_cambio where id_autor = '00000000-0000-0000-0000-0000000000ad'),
  'Ana Admin:porcentaje_igv:18.00:10.00', 'la fila guarda autor, campo, anterior y nuevo');
select throws_ok($$select public.registrar_cambios('00000000-0000-0000-0000-00000000a001')$$, '55000', null, 'un token se usa una sola vez');
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
select is((select nuevo from public.registro_cambio where id_autor = '00000000-0000-0000-0000-0000000000ad'), '10.00', 'la fila sigue intacta');

-- Una confirmacion vencida no se registra.
insert into public.confirmacion_cambio (id, hash_token, id_autor, recurso, nombre_recurso, cambios, creada_en, expira_en)
values ('00000000-0000-0000-0000-00000000a002', 'hash-v', '00000000-0000-0000-0000-0000000000ad', 'impuestos', 'Impuestos',
  '{"porcentaje_igv": {"anterior": "10.00", "nuevo": "9.00"}}', now() - interval '20 minutes', now() - interval '10 minutes');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select throws_ok($$select public.registrar_cambios('00000000-0000-0000-0000-00000000a002')$$, '55000', null, 'una confirmacion vencida no se registra');
reset role;

select * from finish();
rollback;
