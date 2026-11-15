begin;
create extension if not exists pgtap with schema extensions;
select plan(28);

-- Usuarios: A y B clientes; ADM administrador (el rol se fija como superusuario)
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'a@t.pe', '{"nombre":"Ana"}'),
  ('00000000-0000-0000-0000-00000000000b', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'b@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{}'),
  ('00000000-0000-0000-0000-00000000000c', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'c@t.pe', '{"telefono":"+51987654321","nombre_artistico":"Anita"}'),
  ('00000000-0000-0000-0000-00000000000d', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'd@t.pe', '{"telefono":"abc","rol":"administrador","especialidad":"asesoria"}');
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';

-- (d) el alta crea el perfil cliente
select is((select rol from public.usuario where id = '00000000-0000-0000-0000-00000000000a'), 'cliente', 'el alta crea perfil con rol cliente');
select is((select nombre from public.usuario where id = '00000000-0000-0000-0000-00000000000a'), 'Ana', 'el nombre viene de raw_user_meta_data');
select is((select nombre from public.usuario where id = '00000000-0000-0000-0000-00000000000b'), null, 'sin nombre en metadatos queda nulo');

-- RF-01: telefono y nombre artistico salen de los metadatos (validados); rol y especialidad nunca
select is((select telefono from public.usuario where id = '00000000-0000-0000-0000-00000000000c'), '+51987654321', 'el telefono valido viene de los metadatos');
select is((select nombre_artistico from public.usuario where id = '00000000-0000-0000-0000-00000000000c'), 'Anita', 'el nombre artistico viene de los metadatos');
select is((select telefono from public.usuario where id = '00000000-0000-0000-0000-00000000000d'), null, 'un telefono invalido en metadatos queda nulo');
select is((select rol from public.usuario where id = '00000000-0000-0000-0000-00000000000d'), 'cliente', 'el rol de los metadatos se ignora');
select is((select especialidad from public.usuario where id = '00000000-0000-0000-0000-00000000000d'), null, 'la especialidad de los metadatos se ignora');

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

select lives_ok($$update public.usuario set telefono = '987654321', nombre_artistico = 'Ani' where id = '00000000-0000-0000-0000-00000000000a'$$, 'A actualiza su telefono y nombre artistico');
select is((select telefono from public.usuario where id = '00000000-0000-0000-0000-00000000000a'), '987654321', 'el telefono cambio');
select is((select nombre_artistico from public.usuario where id = '00000000-0000-0000-0000-00000000000a'), 'Ani', 'el nombre artistico cambio');
select throws_ok($$update public.usuario set telefono = '12' where id = '00000000-0000-0000-0000-00000000000a'$$, '23514', null, 'un telefono invalido viola el check');
select lives_ok($$update public.usuario set telefono = '999999999', nombre_artistico = 'Hack' where id = '00000000-0000-0000-0000-00000000000b'$$, 'A intenta cambiar telefono y nombre artistico de B sin error (0 filas)');

-- A no cambia el nombre de B: RLS filtra la fila, la sentencia no falla pero no toca nada
select lives_ok($$update public.usuario set nombre = 'Hackeado' where id = '00000000-0000-0000-0000-00000000000b'$$, 'A intenta cambiar el nombre de B sin error (0 filas)');

-- nadie inserta ni borra por la API
select throws_ok($$insert into public.usuario (id) values (gen_random_uuid())$$, '42501', null, 'no se inserta por la API');
select throws_ok($$delete from public.usuario where id = '00000000-0000-0000-0000-00000000000a'$$, '42501', null, 'no se borra por la API');

-- (b) el administrador lee ambos
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select is((select count(*)::int from public.usuario where id in ('00000000-0000-0000-0000-00000000000a','00000000-0000-0000-0000-00000000000b')), 2, 'el administrador lee A y B');

select is((select nombre from public.usuario where id = '00000000-0000-0000-0000-00000000000b'), null, 'el nombre de B sigue intacto');
select is((select (telefono, nombre_artistico)::text from public.usuario where id = '00000000-0000-0000-0000-00000000000b'), '(,)', 'telefono y nombre artistico de B siguen intactos');

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
