begin;
create extension if not exists pgtap with schema extensions;
select plan(88);

select has_table('public', t, 'existe ' || t)
from unnest(array['franja_sala','cierre_sala','reserva','reserva_especialista','cuota','notificacion']) as t;

-- Usuarios: c1 y c2 clientes, pe personal, ad administrador
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000c2', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli2@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000e1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'pe@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{}');
update public.usuario set rol = 'personal' where id = '00000000-0000-0000-0000-0000000000e1';
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';

-- Franjas: restricciones y solapes
select lives_ok($$insert into public.franja_sala (id_sala, inicio, fin, id_publicador)
  select id, '2027-03-01 08:00-05', '2027-03-01 20:00-05', '00000000-0000-0000-0000-0000000000ad' from public.sala_tecnica$$, 'franja valida');
select throws_ok($$insert into public.franja_sala (id_sala, inicio, fin, id_publicador)
  select id, '2027-03-02 10:00-05', '2027-03-02 10:00-05', '00000000-0000-0000-0000-0000000000ad' from public.sala_tecnica$$, '23514', null, 'franja con fin igual al inicio');
select throws_ok($$insert into public.franja_sala (id_sala, inicio, fin, id_publicador)
  select id, '2027-03-02 10:15-05', '2027-03-02 12:00-05', '00000000-0000-0000-0000-0000000000ad' from public.sala_tecnica$$, '23514', null, 'franja con inicio fuera de los 30 min');
select throws_ok($$insert into public.franja_sala (id_sala, inicio, fin, id_publicador)
  select id, '2027-03-02 10:00-05', '2027-03-02 12:20-05', '00000000-0000-0000-0000-0000000000ad' from public.sala_tecnica$$, '23514', null, 'franja con fin fuera de los 30 min');
select throws_ok($$insert into public.franja_sala (id_sala, inicio, fin, id_publicador)
  select id, '2027-03-01 19:00-05', '2027-03-01 22:00-05', '00000000-0000-0000-0000-0000000000ad' from public.sala_tecnica$$, '23P01', null, 'franjas solapadas en la misma sala');
select lives_ok($$insert into public.franja_sala (id_sala, inicio, fin, id_publicador)
  select id, '2027-03-01 20:00-05', '2027-03-01 22:00-05', '00000000-0000-0000-0000-0000000000ad' from public.sala_tecnica$$, 'franjas contiguas permitidas');
select lives_ok($$insert into public.cierre_sala (id_sala, inicio, fin, motivo, id_autor)
  select id, '2027-03-03 08:00-05', '2027-03-03 20:00-05', 'Mantenimiento', '00000000-0000-0000-0000-0000000000ad' from public.sala_tecnica$$, 'cierre valido');
select throws_ok($$insert into public.cierre_sala (id_sala, inicio, fin, motivo, id_autor)
  select id, '2027-03-04 10:00-05', '2027-03-04 09:00-05', 'X', '00000000-0000-0000-0000-0000000000ad' from public.sala_tecnica$$, '23514', null, 'cierre con fin antes del inicio');

-- Reservas: restricciones, buffer y folio
select lives_ok($$insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total, precio, vence_pago)
  select '00000000-0000-0000-0000-0000000000c1', sa.id, se.id, '2027-03-01 10:00-05', '2027-03-01 12:00-05', 160, '{"sala":160}', '2099-01-01'
  from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo'$$, 'reserva valida');
select is((select fin_buffer from public.reserva where inicio = '2027-03-01 10:00-05'), '2027-03-01 12:30-05'::timestamptz, 'fin_buffer = fin + 30 min');
select is((select estado from public.reserva where inicio = '2027-03-01 10:00-05'), 'pre_reservada', 'estado inicial pre_reservada');
select matches((select folio from public.reserva where inicio = '2027-03-01 10:00-05'), '^R-[0-9]{4}-[0-9]{5}$', 'folio legible');
select throws_ok($$insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total)
  select '00000000-0000-0000-0000-0000000000c1', sa.id, se.id, '2027-03-05 10:00-05', '2027-03-05 10:00-05', 1
  from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo'$$, '23514', null, 'duracion cero');
select throws_ok($$insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total)
  select '00000000-0000-0000-0000-0000000000c1', sa.id, se.id, '2027-03-05 10:00-05', '2027-03-05 18:30-05', 1
  from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo'$$, '23514', null, 'duracion mayor a 8 h');
select lives_ok($$insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total)
  select '00000000-0000-0000-0000-0000000000c1', sa.id, se.id, '2027-03-06 08:00-05', '2027-03-06 16:00-05', 1
  from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo'$$, 'duracion de 8 h permitida');
select lives_ok($$insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total)
  select '00000000-0000-0000-0000-0000000000c1', sa.id, se.id, '2027-03-07 08:00-05', '2027-03-07 08:30-05', 1
  from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo'$$, 'duracion de 30 min permitida');
select throws_ok($$insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total)
  select '00000000-0000-0000-0000-0000000000c1', sa.id, se.id, '2027-03-08 10:10-05', '2027-03-08 11:40-05', 1
  from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo'$$, '23514', null, 'inicio fuera de los 30 min');
select throws_ok($$insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total)
  select '00000000-0000-0000-0000-0000000000c1', sa.id, se.id, '2027-03-08 10:00-05', '2027-03-08 11:40-05', 1
  from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo'$$, '23514', null, 'fin fuera de los 30 min');
select throws_ok($$insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total, estado)
  select '00000000-0000-0000-0000-0000000000c1', sa.id, se.id, '2027-03-09 10:00-05', '2027-03-09 11:00-05', 1, 'otro'
  from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo'$$, '23514', null, 'estado fuera de la lista');
select throws_ok($$insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total, estado, motivo_cancelacion)
  select '00000000-0000-0000-0000-0000000000c1', sa.id, se.id, '2027-03-09 10:00-05', '2027-03-09 11:00-05', 1, 'cancelada', 'otro'
  from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo'$$, '23514', null, 'motivo fuera de la lista');
select throws_ok($$insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total, estado)
  select '00000000-0000-0000-0000-0000000000c1', sa.id, se.id, '2027-03-09 10:00-05', '2027-03-09 11:00-05', 1, 'cancelada'
  from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo'$$, '23514', null, 'cancelada exige motivo');
select throws_ok($$insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total, motivo_cancelacion)
  select '00000000-0000-0000-0000-0000000000c1', sa.id, se.id, '2027-03-09 10:00-05', '2027-03-09 11:00-05', 1, 'cliente'
  from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo'$$, '23514', null, 'el motivo solo con cancelada');

-- Solapes (RN-01, RN-02): la reserva vigente 10:00-12:00 bloquea hasta 12:30
select throws_ok($$insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total)
  select '00000000-0000-0000-0000-0000000000c2', sa.id, se.id, '2027-03-01 11:00-05', '2027-03-01 13:00-05', 1
  from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo'$$, '23P01', null, 'dos reservas en el mismo tramo');
select throws_ok($$insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total)
  select '00000000-0000-0000-0000-0000000000c2', sa.id, se.id, '2027-03-01 12:00-05', '2027-03-01 13:00-05', 1
  from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo'$$, '23P01', null, 'el buffer bloquea el inicio pegado al fin');
select throws_ok($$insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total)
  select '00000000-0000-0000-0000-0000000000c2', sa.id, se.id, '2027-03-01 09:00-05', '2027-03-01 10:00-05', 1
  from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo'$$, '23P01', null, 'el buffer de la nueva choca con la existente');
select lives_ok($$insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total)
  select '00000000-0000-0000-0000-0000000000c2', sa.id, se.id, '2027-03-01 12:30-05', '2027-03-01 13:30-05', 1
  from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo'$$, 'a partir del fin del buffer se puede reservar');
update public.reserva set estado = 'cancelada', motivo_cancelacion = 'cliente' where inicio = '2027-03-01 12:30-05';
select lives_ok($$insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total)
  select '00000000-0000-0000-0000-0000000000c2', sa.id, se.id, '2027-03-01 12:30-05', '2027-03-01 13:30-05', 1
  from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo'$$, 'una cancelada libera el tramo');

-- reserva_especialista
select lives_ok($$insert into public.reserva_especialista (id_reserva, id_especialista, monto_fijo, monto_variable, unidad)
  select r.id, e.id, e.monto_fijo, e.monto_variable, e.unidad from public.reserva r, public.especialista e
  where r.inicio = '2027-03-01 10:00-05' and e.nombre = 'Ingeniero de sonido'$$, 'especialista aplicado a la reserva');
select throws_ok($$insert into public.reserva_especialista (id_reserva, id_especialista, monto_fijo, monto_variable, unidad)
  select r.id, e.id, 1, 1, 'hora' from public.reserva r, public.especialista e
  where r.inicio = '2027-03-01 10:00-05' and e.nombre = 'Ingeniero de sonido'$$, '23505', null, 'un especialista una vez por reserva');
select throws_ok($$insert into public.reserva_especialista (id_reserva, id_especialista, monto_fijo, monto_variable, unidad)
  select r.id, e.id, 1, 1, 'dia' from public.reserva r, public.especialista e
  where r.inicio = '2027-03-01 10:00-05' and e.nombre = 'Ejecutante'$$, '23514', null, 'unidad del especialista invalida');

-- Datos para RLS y caducidad
insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total, vence_pago)
select '00000000-0000-0000-0000-0000000000c2', sa.id, se.id, '2027-03-10 10:00-05', '2027-03-10 11:00-05', 50, '2099-01-01'
from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo';

-- anon: sin lectura directa; ocupacion publica sin datos de cliente
set local role anon;
select throws_ok($$select * from public.reserva$$, '42501', null, 'anon no lee reserva');
select throws_ok($$select * from public.notificacion$$, '42501', null, 'anon no lee notificacion');
select throws_ok($$insert into public.franja_sala (id_sala, inicio, fin) select id, '2027-04-01 08:00-05', '2027-04-01 09:00-05' from public.sala_tecnica$$, '42501', null, 'anon no inserta franja');
select is((select count(*)::int from public.franja_sala), 2, 'anon lee franjas');
select is((select count(*)::int from public.cierre_sala), 1, 'anon lee cierres');
select is((select count(*)::int from public.ocupacion_sala((select id from public.sala_tecnica), '2027-03-01 00:00-05', '2027-03-02 00:00-05')), 2,
  'anon ve la ocupacion publica del dia (reserva valida y la liberada que se reocupo)');
select is((select array_agg(a order by a) from (select unnest(proargnames) a from pg_proc where proname = 'ocupacion_sala') s where a in ('inicio','fin_buffer','id_cliente','folio','total')),
  array['fin_buffer','inicio'], 'ocupacion_sala solo devuelve inicio y fin_buffer');
select is((select fin_buffer from public.ocupacion_sala((select id from public.sala_tecnica), '2027-03-01 00:00-05', '2027-03-02 00:00-05') order by inicio limit 1),
  '2027-03-01 12:30-05'::timestamptz, 'la ocupacion incluye el buffer');
select is((select count(*)::int from public.ocupacion_sala((select id from public.sala_tecnica), '2027-03-05 00:00-05', '2027-03-06 00:00-05')), 0, 'fuera del rango no hay ocupacion');
reset role;

-- cliente c1
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select is((select count(*)::int from public.reserva), 3, 'c1 lee solo las suyas');
select is((select count(*)::int from public.reserva where id_cliente = '00000000-0000-0000-0000-0000000000c2'), 0, 'c1 no ve las de c2');
select lives_ok($$insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total, vence_pago)
  select auth.uid(), sa.id, se.id, '2027-03-11 10:00-05', '2027-03-11 11:00-05', 50, '2099-01-01'
  from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo'$$, 'c1 inserta la suya');
select throws_ok($$insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total)
  select '00000000-0000-0000-0000-0000000000c2', sa.id, se.id, '2027-03-12 10:00-05', '2027-03-12 11:00-05', 50
  from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo'$$, '42501', null, 'c1 no inserta a nombre de otro');
select throws_ok($$insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total, estado)
  select auth.uid(), sa.id, se.id, '2027-03-12 10:00-05', '2027-03-12 11:00-05', 50, 'confirmada'
  from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo'$$, '42501', null, 'c1 no inserta confirmada');
select throws_ok($$insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total, estado, motivo_cancelacion)
  select auth.uid(), sa.id, se.id, '2027-03-12 10:00-05', '2027-03-12 11:00-05', 50, 'cancelada', 'cliente'
  from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo'$$, '42501', null, 'c1 no inserta cancelada con motivo');
select throws_ok($$insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total, folio)
  select auth.uid(), sa.id, se.id, '2027-03-12 10:00-05', '2027-03-12 11:00-05', 50, 'R-2027-99999'
  from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo'$$, '42501', null, 'c1 no fija el folio');
select throws_ok($$update public.reserva set total = 1 where id_cliente = auth.uid()$$, '42501', null, 'c1 no cambia el total');
select throws_ok($$update public.reserva set inicio = inicio + interval '1 hour' where id_cliente = auth.uid()$$, '42501', null, 'c1 no cambia fechas');
select throws_ok($$update public.reserva set folio = 'X' where id_cliente = auth.uid()$$, '42501', null, 'c1 no cambia el folio');
select lives_ok($$update public.reserva set estado = 'cancelada', motivo_cancelacion = 'cliente'$$, 'c1 update de estado no afecta filas');
select throws_ok($$delete from public.reserva$$, '42501', null, 'c1 no borra reservas');
select throws_ok($$insert into public.franja_sala (id_sala, inicio, fin) select id, '2027-04-01 08:00-05', '2027-04-01 09:00-05' from public.sala_tecnica$$, '42501', null, 'c1 no inserta franja');
select throws_ok($$select * from public.notificacion$$, '42501', null, 'c1 no lee notificacion');
select lives_ok($$delete from public.franja_sala$$, 'c1 delete de franjas no afecta filas');
select lives_ok($$delete from public.servicio_especialista$$, 'c1 delete de servicio_especialista no afecta filas');
reset role;
select is((select count(*)::int from public.reserva where estado = 'pre_reservada'), 6, 'reservas ajenas y propias intactas tras c1 (una cancelada por el setup)');
select is((select count(*)::int from public.servicio_especialista), 4, 'servicio_especialista intacto tras c1');
select is((select count(*)::int from public.franja_sala), 2, 'franjas intactas tras c1');

-- personal: lee todas, no escribe
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000e1","role":"authenticated"}', true);
select is((select count(*)::int from public.reserva), 7, 'personal lee todas las reservas');
select lives_ok($$update public.reserva set estado = 'confirmada'$$, 'personal update de estado no afecta filas');
reset role;
select is((select count(*)::int from public.reserva where estado = 'confirmada'), 0, 'reservas intactas tras personal');

-- administrador
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select is((select count(*)::int from public.reserva), 7, 'admin lee todas las reservas');
select lives_ok($$update public.reserva set estado = 'confirmada' where inicio = '2027-03-10 10:00-05'$$, 'admin cambia el estado');
select is((select estado from public.reserva where inicio = '2027-03-10 10:00-05'), 'confirmada', 'el estado cambio');
select lives_ok($$insert into public.franja_sala (id_sala, inicio, fin, id_publicador)
  select id, '2027-04-01 08:00-05', '2027-04-01 09:00-05', auth.uid() from public.sala_tecnica$$, 'admin publica franja');
select lives_ok($$delete from public.franja_sala where inicio = '2027-04-01 08:00-05'$$, 'admin borra franja');
select lives_ok($$delete from public.servicio_especialista where id_especialista = (select id from public.especialista where nombre = 'Ingeniero de sonido')
  and id_servicio = (select id from public.servicio where nombre = 'Ensayo')$$, 'admin delete de servicio_especialista (sin fila)');
select lives_ok($$delete from public.servicio_especialista where id_servicio = (select id from public.servicio where nombre = 'Live session')$$, 'admin quita el especialista por defecto');
select is((select count(*)::int from public.servicio_especialista), 3, 'se quito una fila');
reset role;

-- Caducidad (RN-18)
-- A vencida sin pagos, B vigente, C vencida con cuota pagada
insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total, vence_pago)
select '00000000-0000-0000-0000-0000000000c1', sa.id, se.id, t.i, t.i + interval '1 hour', 50, t.v
from public.sala_tecnica sa, public.servicio se,
  (values ('2027-05-01 10:00-05'::timestamptz, '2020-01-01'::timestamptz),
          ('2027-05-02 10:00-05', '2099-01-01'),
          ('2027-05-03 10:00-05', '2020-01-01')) t(i, v)
where se.nombre = 'Ensayo';
insert into public.cuota (id_reserva, hito, monto, estado)
select id, 'al_reservar', 25, 'pagada' from public.reserva where inicio = '2027-05-03 10:00-05';

select is((select count(*)::int from public.ocupacion_sala((select id from public.sala_tecnica), '2027-05-01 00:00-05', '2027-05-02 00:00-05')), 0,
  'la ocupacion trata como libre una pre_reservada vencida sin marcar');
select is((select count(*)::int from public.ocupacion_sala((select id from public.sala_tecnica), '2027-05-03 00:00-05', '2027-05-04 00:00-05')), 1,
  'una vencida con pago sigue ocupando');
select is(public.caducar_reservas(), 1, 'caducar_reservas cancela una');
select is((select estado || '/' || motivo_cancelacion from public.reserva where inicio = '2027-05-01 10:00-05'), 'cancelada/caducada', 'vencida sin pagos queda cancelada por caducidad');
select is((select estado from public.reserva where inicio = '2027-05-02 10:00-05'), 'pre_reservada', 'no vencida intacta');
select is((select estado from public.reserva where inicio = '2027-05-03 10:00-05'), 'pre_reservada', 'vencida con pago intacta');
select is((select count(*)::int from public.notificacion where tipo = 'reserva_caducada' and destinatario = 'cli@t.pe'
  and datos->>'folio' = (select folio from public.reserva where inicio = '2027-05-01 10:00-05')), 1, 'aviso reserva_caducada encolado con folio');
select is(public.caducar_reservas(), 0, 'segunda corrida no caduca nada');
select is((select count(*)::int from public.notificacion where tipo = 'reserva_caducada'), 1, 'sin avisos duplicados');
select is((select count(*)::int from cron.job where jobname = 'caducar_reservas' and schedule = '* * * * *'), 1, 'pg_cron cada minuto');

-- Reinsercion sobre vencida sin marcar
insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total, vence_pago)
select '00000000-0000-0000-0000-0000000000c1', sa.id, se.id, '2027-06-01 10:00-05', '2027-06-01 11:00-05', 50, '2020-01-01'
from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo';
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c2","role":"authenticated"}', true);
select lives_ok($$insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total, vence_pago)
  select auth.uid(), sa.id, se.id, '2027-06-01 10:30-05', '2027-06-01 11:30-05', 50, '2099-01-01'
  from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo'$$, 'reinsertar sobre vencida sin marcar caduca primero');
reset role;
select is((select estado || '/' || motivo_cancelacion from public.reserva where inicio = '2027-06-01 10:00-05'), 'cancelada/caducada', 'la vencida quedo caducada');
select is((select count(*)::int from public.notificacion where tipo = 'reserva_caducada'), 2, 'aviso de la caducidad en el insert');

select * from finish();
rollback;
