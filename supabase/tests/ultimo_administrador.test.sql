begin;
create extension if not exists pgtap with schema extensions;
select plan(5);

insert into auth.users (id, instance_id, aud, role, email)
values
  ('00000000-0000-0000-0000-0000000000a1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'a1@t.pe'),
  ('00000000-0000-0000-0000-0000000000a2', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'a2@t.pe');
update public.usuario set rol = 'administrador' where id in ('00000000-0000-0000-0000-0000000000a1', '00000000-0000-0000-0000-0000000000a2');

select lives_ok($$update public.usuario set rol = 'personal' where id = '00000000-0000-0000-0000-0000000000a1'$$, 'con otro administrador, uno puede dejar de serlo');
-- quedan A2 y los administradores previos de la base (ninguno en un reset limpio): se dejan solo los de la prueba
select lives_ok($$update public.usuario set rol = 'cliente' where rol = 'administrador' and id <> '00000000-0000-0000-0000-0000000000a2'$$, 'se puede quitar el rol a los demas');
select throws_ok($$update public.usuario set rol = 'cliente' where id = '00000000-0000-0000-0000-0000000000a2'$$, 'BG001', null, 'el ultimo administrador no puede dejar de serlo');
select is((select rol from public.usuario where id = '00000000-0000-0000-0000-0000000000a2'), 'administrador', 'el ultimo administrador sigue siendolo');
select throws_ok($$delete from auth.users where id = '00000000-0000-0000-0000-0000000000a2'$$, 'BG001', null, 'borrar al ultimo administrador tambien se impide');

select * from finish();
rollback;
