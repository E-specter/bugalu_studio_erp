begin;
create extension if not exists pgtap with schema extensions;
select plan(5);

-- Supabase confirma al registrar (ADR-008): lo que cuenta es usuario.correo_verificado_en.
insert into auth.users (id, instance_id, aud, role, email, email_confirmed_at)
values
  ('00000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'a@t.pe', now()),
  ('00000000-0000-0000-0000-00000000000b', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'b@t.pe', now());
update public.usuario set correo_verificado_en = now() where id = '00000000-0000-0000-0000-00000000000b';

set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-00000000000a","role":"authenticated"}', true);
select is(public.correo_confirmado(), false, 'registrado pero sin verificar -> false');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-00000000000b","role":"authenticated"}', true);
select is(public.correo_confirmado(), true, 'verificado -> true');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ff","role":"authenticated"}', true);
select is(public.correo_confirmado(), false, 'usuario inexistente -> false');
select throws_ok($$update public.usuario set correo_verificado_en = now()$$, '42501', null, 'authenticated no escribe correo_verificado_en');

set local role anon;
select set_config('request.jwt.claims', '', true);
select throws_ok($$select public.correo_confirmado()$$, '42501', null, 'anon no ejecuta correo_confirmado');
reset role;

select * from finish();
rollback;
