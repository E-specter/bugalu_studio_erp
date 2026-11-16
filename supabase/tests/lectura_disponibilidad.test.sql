begin;
create extension if not exists pgtap with schema extensions;
select plan(12);

insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli@t.pe', '{"nombre":"Cliente Uno"}'),
  ('00000000-0000-0000-0000-0000000000e1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'pe@t.pe', '{}');
update public.usuario set rol = 'personal' where id = '00000000-0000-0000-0000-0000000000e1';
update public.usuario set nombre = 'Cliente Uno' where id = '00000000-0000-0000-0000-0000000000c1';
update public.parametro set valor = 3 where clave = 'anticipacion_minima_horas';
update public.parametro set valor = 5 where clave = 'anticipacion_maxima_semanas';

-- limites_reserva: lectura publica de solo las dos cifras de anticipacion
set local role anon;
select is((select minima_horas from public.limites_reserva()), 3, 'anon lee la anticipacion minima');
select is((select maxima_semanas from public.limites_reserva()), 5, 'anon lee la anticipacion maxima');
select throws_ok($$select * from public.nombres_de_clientes(array['00000000-0000-0000-0000-0000000000c1']::uuid[])$$, '42501', null, 'anon no llama nombres_de_clientes');
reset role;

-- nombres_de_clientes: solo personal o administrador
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select is((select count(*)::int from public.nombres_de_clientes(array['00000000-0000-0000-0000-0000000000c1']::uuid[])), 0, 'un cliente no obtiene nombres, ni el suyo');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000e1","role":"authenticated"}', true);
select is((select nombre from public.nombres_de_clientes(array['00000000-0000-0000-0000-0000000000c1']::uuid[])), 'Cliente Uno', 'personal obtiene el nombre');
select is((select count(*)::int from public.nombres_de_clientes(array[gen_random_uuid()])), 0, 'un id inexistente no devuelve fila');
reset role;

select is((select pg_get_function_result('public.limites_reserva()'::regprocedure)), 'TABLE(minima_horas integer, maxima_semanas integer)', 'forma de limites_reserva');
select is((select proconfig from pg_proc where proname = 'limites_reserva'), array['search_path=""'], 'limites_reserva con search_path vacio');
select is((select proconfig from pg_proc where proname = 'nombres_de_clientes'), array['search_path=""'], 'nombres_de_clientes con search_path vacio');
select is((select has_function_privilege('anon', 'public.nombres_de_clientes(uuid[])', 'execute')), false, 'anon sin execute en nombres_de_clientes');
select is((select has_function_privilege('authenticated', 'public.limites_reserva()', 'execute')), true, 'authenticated ejecuta limites_reserva');
select is((select has_function_privilege('public', 'public.limites_reserva()', 'execute')), false, 'public sin execute');

select * from finish();
rollback;
