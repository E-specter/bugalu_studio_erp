begin;
create extension if not exists pgtap with schema extensions;
select plan(13);

insert into auth.users (id, instance_id, aud, role, email)
values
  ('00000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'a@t.pe'),
  ('00000000-0000-0000-0000-00000000000b', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'b@t.pe'),
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe');
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';
-- el ultimo administrador es el de la prueba, haya lo que haya en la base
update public.usuario set rol = 'cliente' where rol = 'administrador' and id <> '00000000-0000-0000-0000-0000000000ad';

-- no administrador
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-00000000000a","role":"authenticated"}', true);
select throws_ok($$select public.asignar_rol('00000000-0000-0000-0000-00000000000a', 'administrador', null)$$, '42501', null, 'un cliente no se autoasigna rol');
select throws_ok($$select public.asignar_rol('00000000-0000-0000-0000-00000000000b', 'personal', 'x')$$, '42501', null, 'un cliente no asigna a otro');
select throws_ok($$select public.correo_de_usuario('00000000-0000-0000-0000-00000000000b')$$, '42501', null, 'un cliente no lee el correo de otro');
select is(public.correo_de_usuario('00000000-0000-0000-0000-00000000000a'), 'a@t.pe', 'cada uno lee su correo');

-- administrador
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.asignar_rol('00000000-0000-0000-0000-00000000000b', 'personal', 'ingenieria')$$, 'el administrador asigna rol y especialidad');
select is((select (rol, especialidad)::text from public.usuario where id = '00000000-0000-0000-0000-00000000000b'), '(personal,ingenieria)', 'B quedo personal/ingenieria');
select is((select (rol, especialidad)::text from public.usuario where id = '00000000-0000-0000-0000-00000000000a'), '(cliente,)', 'A (fila ajena) intacto');
select is(public.correo_de_usuario('00000000-0000-0000-0000-00000000000b'), 'b@t.pe', 'el administrador lee cualquier correo');
select throws_ok($$select public.asignar_rol('00000000-0000-0000-0000-00000000000b', 'jefe', null)$$, '23514', null, 'rol fuera del catalogo');
select throws_ok($$select public.asignar_rol('00000000-0000-0000-0000-0000000000ff', 'personal', null)$$, 'P0002', null, 'usuario inexistente');
-- ultimo administrador
select throws_ok($$select public.asignar_rol('00000000-0000-0000-0000-0000000000ad', 'cliente', null)$$, 'BG001', null, 'el ultimo administrador no se quita el rol');
select is((select rol from public.usuario where id = '00000000-0000-0000-0000-0000000000ad'), 'administrador', 'sigue siendo administrador');

set local role anon;
select set_config('request.jwt.claims', '', true);
select throws_ok($$select public.asignar_rol('00000000-0000-0000-0000-00000000000a', 'personal', null)$$, '42501', null, 'anon no ejecuta');
reset role;

select * from finish();
rollback;
