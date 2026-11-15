begin;
create extension if not exists pgtap with schema extensions;
select plan(4);

insert into auth.users (id, instance_id, aud, role, email, email_confirmed_at)
values
  ('00000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'a@t.pe', null),
  ('00000000-0000-0000-0000-00000000000b', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'b@t.pe', now());

set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-00000000000a","role":"authenticated"}', true);
select is(public.correo_confirmado(), false, 'correo sin confirmar -> false');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-00000000000b","role":"authenticated"}', true);
select is(public.correo_confirmado(), true, 'correo confirmado -> true');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ff","role":"authenticated"}', true);
select is(public.correo_confirmado(), false, 'usuario inexistente -> false');

set local role anon;
select set_config('request.jwt.claims', '', true);
select throws_ok($$select public.correo_confirmado()$$, '42501', null, 'anon no ejecuta correo_confirmado');
reset role;

select * from finish();
rollback;
