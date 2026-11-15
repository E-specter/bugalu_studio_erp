begin;
create extension if not exists pgtap with schema extensions;
select plan(17);

-- Usuarios: A y B clientes; ADM administrador (el rol se fija como superusuario)
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'a@t.pe', '{"nombre":"Ana"}'),
  ('00000000-0000-0000-0000-00000000000b', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'b@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{}');
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';

-- (d) el alta crea el perfil cliente
select is((select rol from public.usuario where id = '00000000-0000-0000-0000-00000000000a'), 'cliente', 'el alta crea perfil con rol cliente');
select is((select nombre from public.usuario where id = '00000000-0000-0000-0000-00000000000a'), 'Ana', 'el nombre viene de raw_user_meta_data');
select is((select nombre from public.usuario where id = '00000000-0000-0000-0000-00000000000b'), null, 'sin nombre en metadatos queda nulo');

-- Buckets privados
select is((select count(*)::int from storage.buckets where id in ('entregables','comprobantes') and public = false), 2, 'buckets privados');

-- (a) A no lee a B
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-00000000000a","role":"authenticated"}', true);
select is((select count(*)::int from public.usuario), 1, 'A solo ve un perfil');
select is((select count(*)::int from public.usuario where id = '00000000-0000-0000-0000-00000000000b'), 0, 'A no lee el perfil de B');

-- (c) A no cambia su rol, pero si su nombre
select throws_ok($$update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-00000000000a'$$, '42501', null, 'A no puede cambiarse el rol');
select throws_ok($$update public.usuario set especialidad = 'asesoria' where id = '00000000-0000-0000-0000-00000000000a'$$, '42501', null, 'A no puede cambiarse la especialidad');
select lives_ok($$update public.usuario set nombre = 'Ana M' where id = '00000000-0000-0000-0000-00000000000a'$$, 'A actualiza su nombre');
select is((select nombre from public.usuario where id = '00000000-0000-0000-0000-00000000000a'), 'Ana M', 'el nombre cambió');

-- A no cambia el nombre de B: RLS filtra la fila, la sentencia no falla pero no toca nada
select lives_ok($$update public.usuario set nombre = 'Hackeado' where id = '00000000-0000-0000-0000-00000000000b'$$, 'A intenta cambiar el nombre de B sin error (0 filas)');

-- nadie inserta ni borra por la API
select throws_ok($$insert into public.usuario (id) values (gen_random_uuid())$$, '42501', null, 'no se inserta por la API');
select throws_ok($$delete from public.usuario where id = '00000000-0000-0000-0000-00000000000a'$$, '42501', null, 'no se borra por la API');

-- (b) el administrador lee ambos
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select is((select count(*)::int from public.usuario where id in ('00000000-0000-0000-0000-00000000000a','00000000-0000-0000-0000-00000000000b')), 2, 'el administrador lee A y B');

select is((select nombre from public.usuario where id = '00000000-0000-0000-0000-00000000000b'), null, 'el nombre de B sigue intacto');

-- anon: sin policy ni grant de lectura
set local role anon;
select set_config('request.jwt.claims', '', true);
select throws_ok($$select count(*) from public.usuario$$, '42501', null, 'anon no puede leer usuario (permission denied)');
reset role;

-- el borrado en auth.users arrastra el perfil (cascada)
delete from auth.users where id = '00000000-0000-0000-0000-00000000000b';
select is((select count(*)::int from public.usuario where id = '00000000-0000-0000-0000-00000000000b'), 0, 'borrar en auth.users borra el perfil');

select * from finish();
rollback;
