begin;
create extension if not exists pgtap with schema extensions;
select plan(9);

insert into auth.users (id, instance_id, aud, role, email)
values
  ('00000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'a@t.pe'),
  ('00000000-0000-0000-0000-00000000000b', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'b@t.pe');

set local role authenticated;
-- A: sesion por contrasena
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-00000000000a","role":"authenticated","amr":[{"method":"password","timestamp":1}]}', true);
select throws_ok($$select public.marcar_correo_verificado()$$, 'BG002', null, 'sesion por contrasena: verificacion no valida');
select is((select correo_verificado_en is null from public.usuario where id = '00000000-0000-0000-0000-00000000000a'), true, 'A sigue sin verificar');
-- sin amr
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-00000000000a","role":"authenticated"}', true);
select throws_ok($$select public.marcar_correo_verificado()$$, 'BG002', null, 'token sin amr: verificacion no valida');
-- A: sesion por enlace de un solo uso
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-00000000000a","role":"authenticated","amr":[{"method":"otp","timestamp":1}]}', true);
select is(public.marcar_correo_verificado(), true, 'sesion otp: verifica');
select is((select correo_verificado_en is not null from public.usuario where id = '00000000-0000-0000-0000-00000000000a'), true, 'A queda verificado');
reset role;
select is((select correo_verificado_en is null from public.usuario where id = '00000000-0000-0000-0000-00000000000b'), true, 'B (fila ajena) intacto');
set local role authenticated;
-- B: google
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-00000000000b","role":"authenticated","amr":[{"method":"password","timestamp":1},{"method":"oauth","timestamp":2}]}', true);
select is(public.marcar_correo_verificado(), true, 'sesion oauth: verifica');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ff","role":"authenticated","amr":[{"method":"magiclink","timestamp":1}]}', true);
select is(public.marcar_correo_verificado(), false, 'magiclink valido pero sin perfil: no hay fila que marcar');

set local role anon;
select set_config('request.jwt.claims', '', true);
select throws_ok($$select public.marcar_correo_verificado()$$, '42501', null, 'anon no ejecuta');
reset role;

select * from finish();
rollback;
