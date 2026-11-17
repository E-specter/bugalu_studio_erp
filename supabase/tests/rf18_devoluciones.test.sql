begin;
create extension if not exists pgtap with schema extensions;
select plan(67);

-- RF-18 (parte A): devoluciones de credito (CA-07): solicitud, decision, realizada, congelado, avisos y seguridad.
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000c2', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli2@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000e1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'pe@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000a2', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad2@t.pe', '{}');
update public.usuario set rol = 'personal' where id = '00000000-0000-0000-0000-0000000000e1';
update public.usuario set rol = 'administrador' where id in ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-0000000000a2');
update public.usuario set nombre = 'Ana Cliente' where id = '00000000-0000-0000-0000-0000000000c1';

insert into public.reserva (id, id_cliente, id_sala, id_servicio, inicio, fin, total, estado, motivo_cancelacion, vence_pago)
select d.id, d.cliente, sa.id, se.id, d.inicio, d.inicio + interval '1 hour', 200, 'cancelada', 'cliente', '2099-01-01'
from public.sala_tecnica sa, public.servicio se,
  (values
    ('bbbbbbbb-0000-0000-0000-0000000000a0'::uuid, '00000000-0000-0000-0000-0000000000c1'::uuid, '2027-01-01 10:00-05'::timestamptz),
    ('bbbbbbbb-0000-0000-0000-0000000000a1', '00000000-0000-0000-0000-0000000000c2', '2027-01-02 10:00-05')
  ) as d(id, cliente, inicio)
where se.nombre = 'Ensayo';
-- d1 nivel_1, d2 nivel_2, d3 reprogramacion, d4 excepcion, d5 vencido sin marcar, d6 de c2.
insert into public.credito (id, id_cliente, id_reserva, tipo, monto, saldo, vence)
values
  ('eeeeeeee-0000-0000-0000-000000000001', '00000000-0000-0000-0000-0000000000c1', 'bbbbbbbb-0000-0000-0000-0000000000a0', 'nivel_1', 100, 100, now() + interval '10 days'),
  ('eeeeeeee-0000-0000-0000-000000000002', '00000000-0000-0000-0000-0000000000c1', 'bbbbbbbb-0000-0000-0000-0000000000a0', 'nivel_2', 40, 40, now() + interval '10 days'),
  ('eeeeeeee-0000-0000-0000-000000000003', '00000000-0000-0000-0000-0000000000c1', 'bbbbbbbb-0000-0000-0000-0000000000a0', 'reprogramacion', 20, 20, now() + interval '10 days'),
  ('eeeeeeee-0000-0000-0000-000000000004', '00000000-0000-0000-0000-0000000000c1', 'bbbbbbbb-0000-0000-0000-0000000000a0', 'excepcion', 50, 50, now() + interval '11 days'),
  ('eeeeeeee-0000-0000-0000-000000000005', '00000000-0000-0000-0000-0000000000c1', 'bbbbbbbb-0000-0000-0000-0000000000a0', 'nivel_1', 10, 10, now() - interval '1 hour'),
  ('eeeeeeee-0000-0000-0000-000000000006', '00000000-0000-0000-0000-0000000000c2', 'bbbbbbbb-0000-0000-0000-0000000000a1', 'nivel_1', 80, 80, now() + interval '10 days');

-- Solicitar (c1).
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select throws_ok($$select public.solicitar_devolucion('eeeeeeee-0000-0000-0000-000000000001', 'corto')$$, '22023', 'motivo_invalido', 'motivo de menos de 10 caracteres');
select throws_ok($$select public.solicitar_devolucion('eeeeeeee-0000-0000-0000-000000000001', repeat('x', 501))$$, '22023', 'motivo_invalido', 'motivo de mas de 500');
select throws_ok($$select public.solicitar_devolucion('eeeeeeee-0000-0000-0000-000000000001', '          ')$$, '22023', 'motivo_invalido', 'motivo en blanco');
select throws_ok($$select public.solicitar_devolucion('eeeeeeee-0000-0000-0000-000000000002', 'Quiero mi dinero de vuelta')$$, 'P0001', 'devolucion_no_permitida', 'nivel 2: no permitida');
select throws_ok($$select public.solicitar_devolucion('eeeeeeee-0000-0000-0000-000000000003', 'Quiero mi dinero de vuelta')$$, 'P0001', 'devolucion_no_permitida', 'reprogramacion: no permitida');
select throws_ok($$select public.solicitar_devolucion('eeeeeeee-0000-0000-0000-000000000005', 'Quiero mi dinero de vuelta')$$, 'P0001', 'credito_no_vigente', 'vencido: credito_no_vigente');
select throws_ok($$select public.solicitar_devolucion('eeeeeeee-0000-0000-0000-000000000006', 'Quiero mi dinero de vuelta')$$, 'P0002', null, 'el credito de otro cliente no existe para el');
select throws_ok($$select public.solicitar_devolucion(gen_random_uuid(), 'Quiero mi dinero de vuelta')$$, 'P0002', null, 'inexistente');
select lives_ok($$select public.solicitar_devolucion('eeeeeeee-0000-0000-0000-000000000001', '  Cambie de planes y necesito el dinero  ')$$, 'pide la devolucion del credito de nivel 1');
select throws_ok($$select public.solicitar_devolucion('eeeeeeee-0000-0000-0000-000000000001', 'Quiero mi dinero de vuelta')$$, 'P0001', 'devolucion_pendiente', 'una sola solicitud pendiente por credito');
select lives_ok($$select public.solicitar_devolucion('eeeeeeee-0000-0000-0000-000000000004', 'Credito de excepcion que no usare')$$, 'el credito de excepcion tambien');
reset role;
select results_eq($$select tipo, estado, id_cliente, id_reserva, motivo, monto_solicitado from public.devolucion where id_credito = 'eeeeeeee-0000-0000-0000-000000000001'$$,
  $$values ('nivel_1', 'pendiente', '00000000-0000-0000-0000-0000000000c1'::uuid, 'bbbbbbbb-0000-0000-0000-0000000000a0'::uuid, 'Cambie de planes y necesito el dinero', 100.00::numeric)$$,
  'queda pendiente con el motivo recortado y el saldo del credito como monto solicitado');
select is((select count(*)::int from public.notificacion where tipo = 'devolucion_solicitada' and destinatario in ('ad@t.pe', 'ad2@t.pe')), 4, 'avisa a cada administrador de cada solicitud');
select ok((select datos ->> 'cliente' = 'Ana Cliente' and datos ? 'id_devolucion' and (datos ->> 'saldo')::numeric = 100 and datos ? 'motivo'
  from public.notificacion where tipo = 'devolucion_solicitada' and destinatario = 'ad@t.pe' and datos ->> 'saldo' = '100.00'), 'el aviso lleva cliente, saldo y motivo');
select throws_ok($$insert into public.devolucion (id_credito, id_reserva, id_cliente, tipo, motivo, monto_solicitado)
  values ('eeeeeeee-0000-0000-0000-000000000001', 'bbbbbbbb-0000-0000-0000-0000000000a0', '00000000-0000-0000-0000-0000000000c1', 'nivel_1', 'Otra solicitud pendiente', 100)$$,
  '23505', null, 'la base solo admite una pendiente por credito');

-- Mientras esta pendiente, el credito no se usa ni vence.
update public.credito set vence = now() - interval '1 hour' where id = 'eeeeeeee-0000-0000-0000-000000000004';
select is(public.procesar_creditos(), 1, 'solo vence el d5 (los pendientes de devolucion no)');
select is((select estado from public.credito where id = 'eeeeeeee-0000-0000-0000-000000000004'), 'vigente', 'el congelado no vence');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select throws_ok($$select public.aplicar_credito('cccccccc-0000-0000-0000-000000000001', 10, 'eeeeeeee-0000-0000-0000-000000000001')$$, 'P0002', null, 'ejemplo de cuota inexistente no usa credito');
reset role;

-- Decidir: solo el administrador.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select throws_ok($$select public.decidir_devolucion((select id from public.devolucion where id_credito = 'eeeeeeee-0000-0000-0000-000000000001'), 'total', null, null)$$, '42501', null, 'el cliente no decide');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000e1","role":"authenticated"}', true);
select throws_ok($$select public.decidir_devolucion((select id from public.devolucion where id_credito = 'eeeeeeee-0000-0000-0000-000000000001'), 'total', null, null)$$, '42501', null, 'el personal no decide');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select throws_ok($$select public.decidir_devolucion(gen_random_uuid(), 'total', null, null)$$, 'P0002', null, 'inexistente');
select throws_ok($$select public.decidir_devolucion((select id from public.devolucion where id_credito = 'eeeeeeee-0000-0000-0000-000000000001'), 'parcial', 0, null)$$, '22023', 'monto_invalido', 'parcial con 0: monto_invalido');
select throws_ok($$select public.decidir_devolucion((select id from public.devolucion where id_credito = 'eeeeeeee-0000-0000-0000-000000000001'), 'parcial', 100.01, null)$$, '22023', 'monto_invalido', 'parcial mayor que el saldo');
select throws_ok($$select public.decidir_devolucion((select id from public.devolucion where id_credito = 'eeeeeeee-0000-0000-0000-000000000001'), 'parcial', null, null)$$, '22023', 'monto_invalido', 'parcial sin monto');
select throws_ok($$select public.decidir_devolucion((select id from public.devolucion where id_credito = 'eeeeeeee-0000-0000-0000-000000000001'), 'rechazo', null, null)$$, '22023', 'motivo_requerido', 'rechazo sin motivo');
select throws_ok($$select public.decidir_devolucion((select id from public.devolucion where id_credito = 'eeeeeeee-0000-0000-0000-000000000001'), 'parcial', 30, null)$$, '22023', 'motivo_requerido', 'parcial sin motivo');
select throws_ok($$select public.decidir_devolucion((select id from public.devolucion where id_credito = 'eeeeeeee-0000-0000-0000-000000000001'), 'rechazo', null, 'corto')$$, '22023', 'motivo_requerido', 'el motivo de la decision lleva de 10 a 500 caracteres');
select throws_ok($$select public.decidir_devolucion((select id from public.devolucion where id_credito = 'eeeeeeee-0000-0000-0000-000000000001'), 'rechazo', null, '   ')$$, '22023', 'motivo_requerido', 'rechazo con motivo en blanco');
select throws_ok($$select public.decidir_devolucion((select id from public.devolucion where id_credito = 'eeeeeeee-0000-0000-0000-000000000001'), 'otra', null, null)$$, '22023', null, 'decision desconocida');
select lives_ok($$select public.decidir_devolucion((select id from public.devolucion where id_credito = 'eeeeeeee-0000-0000-0000-000000000001'), 'parcial', 30, 'Se devuelve una parte')$$, 'aprueba parcial 30');
select throws_ok($$select public.decidir_devolucion((select id from public.devolucion where id_credito = 'eeeeeeee-0000-0000-0000-000000000001'), 'total', null, null)$$, 'P0001', 'devolucion_decidida', 'una vez decidida no se decide otra vez');
-- El credito de excepcion (d4) tenia el vencimiento pasado mientras estaba pendiente: se rechaza y el resto vence 7 dias despues.
select lives_ok($$select public.decidir_devolucion((select id from public.devolucion where id_credito = 'eeeeeeee-0000-0000-0000-000000000004'), 'rechazo', null, 'Ya se uso el crédito')$$, 'rechaza con motivo');
reset role;
select results_eq($$select estado, monto_aprobado, motivo_decision, id_decisor from public.devolucion where id_credito = 'eeeeeeee-0000-0000-0000-000000000001'$$,
  $$values ('aprobada', 30.00::numeric, 'Se devuelve una parte', '00000000-0000-0000-0000-0000000000ad'::uuid)$$, 'aprobada parcial con su monto');
select ok((select decidida_en is not null from public.devolucion where id_credito = 'eeeeeeee-0000-0000-0000-000000000001'), 'guarda cuando se decidio');
select results_eq($$select saldo, estado from public.credito where id = 'eeeeeeee-0000-0000-0000-000000000001'$$,
  $$values (70.00::numeric, 'vigente')$$, 'lo aprobado se descuenta y el resto queda como credito');
select results_eq($$select estado, motivo_decision from public.devolucion where id_credito = 'eeeeeeee-0000-0000-0000-000000000004'$$,
  $$values ('rechazada', 'Ya se uso el crédito')$$, 'rechazada con su motivo');
select ok((select estado = 'vigente' and saldo = 50 and vence > now() + interval '6 days' and vence <= now() + interval '8 days'
  from public.credito where id = 'eeeeeeee-0000-0000-0000-000000000004'), 'si ya habia pasado su vencimiento, el resto vence 7 dias despues de la decision');
select ok((select vence = (date_trunc('day', (now() at time zone 'America/Lima') + interval '8 days') at time zone 'America/Lima') - interval '1 microsecond'
  from public.credito where id = 'eeeeeeee-0000-0000-0000-000000000004'), 'al final de ese dia en Lima');
select is((select count(*)::int from public.notificacion where tipo = 'devolucion_decidida' and destinatario = 'cli@t.pe'), 2, 'avisa al cliente de cada decision');
select ok((select datos ->> 'decision' = 'parcial' and (datos ->> 'monto_aprobado')::numeric = 30 and datos ? 'folio_origen' is not null
  from public.notificacion where tipo = 'devolucion_decidida' and datos ->> 'decision' = 'parcial'), 'el aviso lleva la decision y el monto');

-- Tras una decision se puede pedir otra por el resto; total agota el credito.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select lives_ok($$select public.solicitar_devolucion('eeeeeeee-0000-0000-0000-000000000001', 'Devuelvanme lo que queda')$$, 'nueva solicitud por el resto');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.decidir_devolucion((select id from public.devolucion where id_credito = 'eeeeeeee-0000-0000-0000-000000000001' and estado = 'pendiente'), 'total', null, null)$$, 'aprueba total');
reset role;
select results_eq($$select monto_aprobado from public.devolucion where id_credito = 'eeeeeeee-0000-0000-0000-000000000001' and estado = 'aprobada' order by monto_aprobado desc limit 1$$,
  $$values (70.00::numeric)$$, 'total = el saldo del momento');
select results_eq($$select saldo, estado from public.credito where id = 'eeeeeeee-0000-0000-0000-000000000001'$$, $$values (0.00::numeric, 'agotado')$$, 'el credito queda agotado');

-- Marcar realizada (antes, el cliente vuelve a pedir por el credito que se le rechazo: queda una pendiente).
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select lives_ok($$select public.solicitar_devolucion('eeeeeeee-0000-0000-0000-000000000004', 'Ahora si quiero la devolucion')$$, 'tras un rechazo se puede pedir de nuevo');
select throws_ok($$select public.marcar_devolucion_realizada((select id from public.devolucion where monto_aprobado = 70), 'Yape 123')$$, '42501', null, 'el cliente no la marca');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select throws_ok($$select public.marcar_devolucion_realizada((select id from public.devolucion where monto_aprobado = 70), '   ')$$, '22023', 'nota_invalida', 'la nota es obligatoria');
select throws_ok($$select public.marcar_devolucion_realizada((select id from public.devolucion where monto_aprobado = 70), repeat('x', 501))$$, '22023', 'nota_invalida', 'la nota admite hasta 500 caracteres');
select throws_ok($$select public.marcar_devolucion_realizada((select id from public.devolucion where id_credito = 'eeeeeeee-0000-0000-0000-000000000004' and estado = 'rechazada'), 'Yape 1')$$, 'P0001', 'devolucion_no_aprobada', 'una rechazada no se marca realizada');
select throws_ok($$select public.marcar_devolucion_realizada((select id from public.devolucion where estado = 'pendiente'), 'Yape 1')$$, 'P0001', 'devolucion_no_aprobada', 'una pendiente tampoco');
select throws_ok($$select public.marcar_devolucion_realizada(gen_random_uuid(), 'Yape 1')$$, 'P0002', null, 'inexistente');
select lives_ok($$select public.marcar_devolucion_realizada((select id from public.devolucion where monto_aprobado = 70), '  Yape, operacion 998877  ')$$, 'marca realizada con medio y operacion');
select throws_ok($$select public.marcar_devolucion_realizada((select id from public.devolucion where monto_aprobado = 70), 'Yape 998877')$$, 'P0001', 'devolucion_no_aprobada', 'una realizada no se vuelve a marcar');
reset role;
select results_eq($$select estado, nota_realizada, id_realizador from public.devolucion where monto_aprobado = 70$$,
  $$values ('realizada', 'Yape, operacion 998877', '00000000-0000-0000-0000-0000000000ad'::uuid)$$, 'queda realizada con su nota');
select ok((select realizada_en is not null from public.devolucion where monto_aprobado = 70), 'guarda cuando se realizo');
select is((select count(*)::int from public.notificacion where tipo = 'devolucion_realizada' and destinatario = 'cli@t.pe'), 1, 'avisa al cliente de la devolucion realizada');

-- Lectura (RLS) e inmutabilidad.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c2","role":"authenticated"}', true);
select is((select count(*)::int from public.devolucion), 0, 'otro cliente no ve devoluciones ajenas');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000e1","role":"authenticated"}', true);
select is((select count(*)::int from public.devolucion), 0, 'el personal no ve devoluciones');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select is((select count(*)::int from public.devolucion), 4, 'el dueno ve las suyas');
select throws_ok($$update public.devolucion set estado = 'realizada', monto_aprobado = 1000$$, '42501', null, 'el cliente no edita devoluciones');
select throws_ok($$delete from public.devolucion$$, '42501', null, 'ni las borra');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select throws_ok($$update public.devolucion set estado = 'realizada'$$, '42501', null, 'el administrador tampoco edita directo');
reset role;
set local role anon;
select throws_ok($$select * from public.devolucion$$, '42501', null, 'anon no lee devoluciones');
select throws_ok($$select public.solicitar_devolucion('eeeeeeee-0000-0000-0000-000000000001', 'Quiero mi dinero de vuelta')$$, '42501', null, 'anon no solicita');
select throws_ok($$select public.decidir_devolucion(gen_random_uuid(), 'total', null, null)$$, '42501', null, 'anon no decide');
reset role;
select throws_ok($$delete from public.devolucion$$, 'P0001', null, 'una devolucion no se borra');
select throws_ok($$update public.devolucion set monto_aprobado = 1 where tipo = 'nivel_1' and estado = 'rechazada'$$, 'P0001', null, 'una devolucion decidida no cambia su monto por fuera de las funciones');

select * from finish();
rollback;
