begin;
create extension if not exists pgtap with schema extensions;
select plan(18);

insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'a@t.pe', '{}'),
  ('00000000-0000-0000-0000-00000000000b', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'b@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{}');
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';
insert into public.solicitud_acceso (id, id_usuario, especialidad)
values ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-00000000000b', 'ingenieria');

select throws_ok($$insert into public.solicitud_acceso (id_usuario, especialidad) values ('00000000-0000-0000-0000-00000000000a', '  ')$$, '23514', null, 'la especialidad no puede estar en blanco');

-- A
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-00000000000a","role":"authenticated"}', true);
select lives_ok($$insert into public.solicitud_acceso (id_usuario, especialidad, mensaje) values ('00000000-0000-0000-0000-00000000000a', 'asesoria', 'hola')$$, 'A crea su solicitud pendiente');
select is((select count(*)::int from public.solicitud_acceso), 1, 'A solo ve su solicitud');
select is((select count(*)::int from public.solicitud_acceso where id_usuario = '00000000-0000-0000-0000-00000000000b'), 0, 'A no ve la de B');
select throws_ok($$insert into public.solicitud_acceso (id_usuario, especialidad) values ('00000000-0000-0000-0000-00000000000b', 'x')$$, '42501', null, 'A no crea solicitudes a nombre de B');
select throws_ok($$insert into public.solicitud_acceso (id_usuario, especialidad, estado) values ('00000000-0000-0000-0000-00000000000a', 'x', 'aprobada')$$, '42501', null, 'A no inserta una solicitud ya aprobada');
select throws_ok($$insert into public.solicitud_acceso (id_usuario, especialidad, motivo) values ('00000000-0000-0000-0000-00000000000a', 'x', 'm')$$, '42501', null, 'A no inserta con motivo');
select throws_ok($$insert into public.solicitud_acceso (id_usuario, especialidad, id_revisor) values ('00000000-0000-0000-0000-00000000000a', 'x', '00000000-0000-0000-0000-00000000000a')$$, '42501', null, 'A no inserta con revisor');
select throws_ok($$insert into public.solicitud_acceso (id_usuario, especialidad) values ('00000000-0000-0000-0000-00000000000a', 'otra')$$, '23505', null, 'una sola solicitud pendiente por usuario');
select lives_ok($$update public.solicitud_acceso set estado = 'aprobada' where id_usuario in ('00000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-00000000000b')$$, 'A intenta aprobar sin error (0 filas)');
select is((select estado from public.solicitud_acceso where id_usuario = '00000000-0000-0000-0000-00000000000a'), 'pendiente', 'la solicitud de A sigue pendiente');
select throws_ok($$delete from public.solicitud_acceso$$, '42501', null, 'nadie borra por la API');

-- administrador
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select is((select count(*)::int from public.solicitud_acceso where id_usuario in ('00000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-00000000000b')), 2, 'el administrador lee las de A y B');
select is((select estado from public.solicitud_acceso where id = '00000000-0000-0000-0000-0000000000b1'), 'pendiente', 'la solicitud de B sigue intacta');
select lives_ok($$update public.solicitud_acceso set estado = 'rechazada', motivo = 'no hay cupo', id_revisor = '00000000-0000-0000-0000-0000000000ad', revisada_en = now() where id = '00000000-0000-0000-0000-0000000000b1'$$, 'el administrador rechaza con motivo');
select is((select (estado, motivo, id_revisor)::text from public.solicitud_acceso where id = '00000000-0000-0000-0000-0000000000b1'), '(rechazada,"no hay cupo",00000000-0000-0000-0000-0000000000ad)', 'estado, motivo y revisor guardados');
select throws_ok($$delete from public.solicitud_acceso$$, '42501', null, 'ni el administrador borra por la API');

-- anon
set local role anon;
select set_config('request.jwt.claims', '', true);
select throws_ok($$select count(*) from public.solicitud_acceso$$, '42501', null, 'anon no lee solicitudes');
reset role;

select * from finish();
rollback;
