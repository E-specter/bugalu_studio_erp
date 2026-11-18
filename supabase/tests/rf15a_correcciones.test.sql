begin;
create extension if not exists pgtap with schema extensions;
select plan(21);

-- Correcciones de la auditoria de RF-15 etapa A (ronda 1): B1 (el profesional no es cliente de sala ni de pagos),
-- perfil solo de quien conserva el rol y foto en dos rutas fijas por perfil.
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{"nombre":"Admin"}'),
  ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'p1@t.pe', '{"nombre":"Pablo Uno"}'),
  ('00000000-0000-0000-0000-0000000000b2', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'p2@t.pe', '{"nombre":"Paula Dos"}'),
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'c1@t.pe', '{"nombre":"Clara Cliente"}');
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';
update public.usuario set rol = 'cliente' where rol = 'administrador' and id <> '00000000-0000-0000-0000-0000000000ad';
-- Clara es cliente con una reserva, su cuota y un credito; luego pasara a ser profesional.
insert into public.reserva (id, id_cliente, id_sala, id_servicio, inicio, fin, total, vence_pago)
select '00000000-0000-0000-0000-0000000000f1', '00000000-0000-0000-0000-0000000000c1', sa.id, se.id,
       '2099-03-01 10:00-05', '2099-03-01 11:00-05', 100, '2099-02-01'
from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo' limit 1;
insert into public.cuota (id, id_reserva, hito, monto) values
  ('00000000-0000-0000-0000-0000000000f2', '00000000-0000-0000-0000-0000000000f1', 'al_reservar', 50);
insert into public.credito (id, id_cliente, id_reserva, tipo, monto, saldo, vence)
values ('00000000-0000-0000-0000-0000000000f3', '00000000-0000-0000-0000-0000000000c1',
        '00000000-0000-0000-0000-0000000000f1', 'nivel_1', 10, 10, now() + interval '5 days');
insert into public.especialidad_asesoria (id, nombre) values ('ee000000-0000-0000-0000-000000000001', 'Mezcla');

set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
do $$ begin
  perform public.asignar_rol('00000000-0000-0000-0000-0000000000b1', 'profesional', null);
  perform public.asignar_rol('00000000-0000-0000-0000-0000000000b2', 'profesional', null);
end $$;
reset role;
insert into public.perfil_especialidad (id_profesional, id_especialidad)
select id, 'ee000000-0000-0000-0000-000000000001' from public.perfil_profesional;
insert into public.precio_asesoria (id_profesional, minutos, precio) select id, 30, 50 from public.perfil_profesional;

-- B1: es_profesional() y las altas de reserva, pago y credito.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000b1","role":"authenticated"}', true);
select ok(public.es_profesional(), 'es_profesional() es verdadero para el rol profesional');
select throws_ok($$insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total, vence_pago)
  select '00000000-0000-0000-0000-0000000000b1', sa.id, se.id, '2099-04-01 10:00-05', '2099-04-01 11:00-05', 10, '2099-03-01'
  from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo' limit 1$$,
  '42501', null, 'el profesional no inserta reservas de sala');
reset role;
select is((select count(*)::int from public.reserva where id_cliente = '00000000-0000-0000-0000-0000000000b1'), 0, 'y no quedo ninguna reserva suya');
select ok(not (select public.es_profesional() from (select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1"}', true)) x),
  'es_profesional() es falso para un cliente');

-- Clara pasa a ser profesional conservando su reserva: ya no usa credito ni paga.
update public.usuario set rol = 'profesional' where id = '00000000-0000-0000-0000-0000000000c1';
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select throws_ok($$select public.aplicar_credito('00000000-0000-0000-0000-0000000000f2', 10, null)$$,
  '42501', null, 'un profesional no usa credito');
select throws_ok($$insert into public.comprobante_pago (id, id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
  values (gen_random_uuid(), '00000000-0000-0000-0000-0000000000f2', '00000000-0000-0000-0000-0000000000c1', 'yape', 50, 'OP-1234',
          '00000000-0000-0000-0000-0000000000c1/x.png', 'image/png')$$,
  '42501', null, 'un profesional no registra pagos');
reset role;
select is((select saldo from public.credito where id = '00000000-0000-0000-0000-0000000000f3'), 10::numeric, 'el credito quedo intacto');
select is((select count(*)::int from public.comprobante_pago), 0, 'no hay pagos registrados');
update public.usuario set rol = 'cliente' where id = '00000000-0000-0000-0000-0000000000c1';
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select lives_ok($$select public.aplicar_credito('00000000-0000-0000-0000-0000000000f2', 10, null)$$, 'un cliente si usa su credito');
reset role;

-- No bloqueante 1: el perfil solo se activa y publica si el usuario conserva el rol.
update public.perfil_profesional set activo = true where id = '00000000-0000-0000-0000-0000000000b1';
select ok(public.perfil_publicado('00000000-0000-0000-0000-0000000000b1'), 'con rol profesional el perfil activo esta publicado');
update public.usuario set rol = 'cliente' where id = '00000000-0000-0000-0000-0000000000b1';
select ok(not public.perfil_publicado('00000000-0000-0000-0000-0000000000b1'), 'sin el rol deja de estar publicado');
set local role anon;
select set_config('request.jwt.claims', '', true);
select is((select count(*)::int from public.perfil_profesional where id = '00000000-0000-0000-0000-0000000000b1'), 0, 'y el directorio no lo muestra');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select throws_ok($$select public.cambiar_estado_profesional('00000000-0000-0000-0000-0000000000b1', true)$$,
  'P0001', 'rol_no_admitido', 'el administrador no activa el perfil de quien dejo de ser profesional');
select lives_ok($$select public.cambiar_estado_profesional('00000000-0000-0000-0000-0000000000b1', false)$$, 'pero si puede desactivarlo');
select lives_ok($$select public.cambiar_estado_profesional('00000000-0000-0000-0000-0000000000b2', true)$$, 'y activar el de un profesional');
reset role;

-- No bloqueante 3: la foto solo se sube a `<perfil>/foto-1` o `<perfil>/foto-2` (se sobrescribe, no se acumula).
update public.usuario set rol = 'profesional' where id = '00000000-0000-0000-0000-0000000000b1';
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000b1","role":"authenticated"}', true);
select lives_ok($$insert into storage.objects (bucket_id, name, owner_id) values ('profesionales', '00000000-0000-0000-0000-0000000000b1/foto-1', '00000000-0000-0000-0000-0000000000b1')$$,
  'sube a su ruta foto-1');
select lives_ok($$update storage.objects set name = name where bucket_id = 'profesionales' and name = '00000000-0000-0000-0000-0000000000b1/foto-1'$$,
  'y la sobrescribe (upsert)');
select throws_ok($$insert into storage.objects (bucket_id, name, owner_id) values ('profesionales', '00000000-0000-0000-0000-0000000000b1/otra.png', '00000000-0000-0000-0000-0000000000b1')$$,
  '42501', null, 'no sube con otro nombre en su carpeta');
select throws_ok($$insert into storage.objects (bucket_id, name, owner_id) values ('profesionales', '00000000-0000-0000-0000-0000000000b1/foto-3', '00000000-0000-0000-0000-0000000000b1')$$,
  '42501', null, 'ni a una tercera ruta');
select throws_ok($$insert into storage.objects (bucket_id, name, owner_id) values ('profesionales', '00000000-0000-0000-0000-0000000000b1/sub/foto-1', '00000000-0000-0000-0000-0000000000b1')$$,
  '42501', null, 'ni en una subcarpeta');
select throws_ok($$insert into storage.objects (bucket_id, name, owner_id) values ('profesionales', '00000000-0000-0000-0000-0000000000b2/foto-1', '00000000-0000-0000-0000-0000000000b1')$$,
  '42501', null, 'ni en la carpeta de otro perfil');
reset role;

select * from finish();
rollback;
