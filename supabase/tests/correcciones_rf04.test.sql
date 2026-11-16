begin;
create extension if not exists pgtap with schema extensions;
select plan(8);

-- TAREA-RF04-9: defensa en profundidad de cuota y reserva, aviso sin sub y retiro de franjas con reservas.
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli@t.pe', '{}');

set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);

select throws_ok($$insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total)
  select auth.uid(), sa.id, se.id, '2027-06-01 10:00-05', '2027-06-01 11:00-05', 1
  from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo'$$, '42501', null,
  'el cliente no inserta una reserva sin vence_pago');
select lives_ok($$insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total, vence_pago)
  select auth.uid(), sa.id, se.id, '2027-06-01 10:00-05', '2027-06-01 11:00-05', 1, '2027-05-30 10:00-05'
  from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo'$$,
  'con vence_pago si inserta');
select lives_ok($$insert into public.cuota (id_reserva, hito, monto)
  select id, 'al_reservar', 1 from public.reserva where inicio = '2027-06-01 10:00-05'$$,
  'el dueno inserta una cuota con hito y monto');
select throws_ok($$insert into public.cuota (id_reserva, hito, monto, estado)
  select id, 'al_terminar', 1, 'pagada' from public.reserva where inicio = '2027-06-01 10:00-05'$$, '42501', null,
  'el dueno no inserta una cuota pagada');
select throws_ok($$insert into public.cuota (id_reserva, hito, monto, estado)
  select id, 'al_terminar', 1, 'pendiente' from public.reserva where inicio = '2027-06-01 10:00-05'$$, '42501', null,
  'ni siquiera indicando el estado');

-- aviso sin sub: no hay dueno posible
select set_config('prueba.id', (select id::text from public.reserva where inicio = '2027-06-01 10:00-05'), true);
select set_config('request.jwt.claims', '{"role":"authenticated"}', true);
select throws_ok($$select public.encolar_aviso_reserva(current_setting('prueba.id')::uuid)$$, '42501', null,
  'sin sub no se encola el aviso');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select lives_ok($$select public.encolar_aviso_reserva(current_setting('prueba.id')::uuid)$$, 'con sub, el dueno si');
reset role;

-- retirar una franja deja la reserva enlazada con id_franja nulo
insert into public.franja_sala (id_sala, inicio, fin) select id, '2027-06-01 08:00-05', '2027-06-01 20:00-05' from public.sala_tecnica limit 1;
update public.reserva set id_franja = (select id from public.franja_sala where inicio = '2027-06-01 08:00-05') where inicio = '2027-06-01 10:00-05';
delete from public.franja_sala where inicio = '2027-06-01 08:00-05';
select is((select id_franja from public.reserva where inicio = '2027-06-01 10:00-05'), null, 'retirar la franja libera el enlace de la reserva');

select * from finish();
rollback;
