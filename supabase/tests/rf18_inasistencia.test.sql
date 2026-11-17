begin;
create extension if not exists pgtap with schema extensions;
select plan(52);

-- RF-18 (parte A): inasistencia (CA-11), estados automaticos con no_asistio y caso excepcional (CA-12).
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000e1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'pe@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{}');
update public.usuario set rol = 'personal' where id = '00000000-0000-0000-0000-0000000000e1';
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';

-- Ventana de la marca: desde inicio + tolerancia hasta el fin, con limites exactos.
select is(public.ventana_inasistencia('2027-06-10 10:00-05', '2027-06-10 12:00-05', 15, '2027-06-10 10:14:59-05'), 'antes', '14 min 59 s: antes de la tolerancia');
select is(public.ventana_inasistencia('2027-06-10 10:00-05', '2027-06-10 12:00-05', 15, '2027-06-10 10:15:00-05'), 'abierta', '15 min exactos: abierta');
select is(public.ventana_inasistencia('2027-06-10 10:00-05', '2027-06-10 12:00-05', 15, '2027-06-10 12:00:00-05'), 'abierta', 'en el fin exacto: abierta');
select is(public.ventana_inasistencia('2027-06-10 10:00-05', '2027-06-10 12:00-05', 15, '2027-06-10 12:00:01-05'), 'despues', 'pasado el fin: despues');

-- Una sala por reserva para poder tener varias en su ventana abierta (inicio hace 1 h, fin dentro de 1 h).
insert into public.sala_tecnica (id, nombre, sede)
select ('5a5a5a5a-0000-0000-0000-0000000000' || lpad(n::text, 2, '0'))::uuid, 'Sala t' || n, 'Sede t' from generate_series(1, 12) n;
-- ra confirmada, rb pre_reservada con adelanto pagado, rc en_curso, rd finalizada, re cancelada, rf futura, rg confirmada (admin),
-- rh confirmada +11 h (excepcion tras nivel 3), ri confirmada +31 h (nivel 2), rj sin pagos pre_reservada, rk confirmada (excepcion tras inasistencia),
-- rl confirmada +73 h (nivel 1).
insert into public.reserva (id, id_cliente, id_sala, id_servicio, inicio, fin, total, estado, motivo_cancelacion, vence_pago, creada_en)
select d.id, '00000000-0000-0000-0000-0000000000c1', ('5a5a5a5a-0000-0000-0000-0000000000' || lpad(d.n::text, 2, '0'))::uuid, se.id,
  date_trunc('hour', now()) + d.horas * interval '1 hour', date_trunc('hour', now()) + d.horas * interval '1 hour' + interval '2 hours',
  200, d.estado, d.motivo, '2099-01-01', now() - interval '30 days'
from public.servicio se,
  (values
    ('bbbbbbbb-0000-0000-0000-00000000000a'::uuid, 1, -1, 'confirmada', null),
    ('bbbbbbbb-0000-0000-0000-00000000000b', 2, -1, 'pre_reservada', null),
    ('bbbbbbbb-0000-0000-0000-00000000000c', 3, -1, 'en_curso', null),
    ('bbbbbbbb-0000-0000-0000-00000000000d', 4, -1, 'finalizada', null),
    ('bbbbbbbb-0000-0000-0000-00000000000e', 5, -1, 'cancelada', 'cliente'),
    ('bbbbbbbb-0000-0000-0000-00000000000f', 6, 3, 'confirmada', null),
    ('bbbbbbbb-0000-0000-0000-000000000010', 7, -1, 'confirmada', null),
    ('bbbbbbbb-0000-0000-0000-000000000011', 8, 11, 'confirmada', null),
    ('bbbbbbbb-0000-0000-0000-000000000012', 9, 31, 'confirmada', null),
    ('bbbbbbbb-0000-0000-0000-000000000013', 10, -1, 'pre_reservada', null),
    ('bbbbbbbb-0000-0000-0000-000000000014', 11, -1, 'confirmada', null),
    ('bbbbbbbb-0000-0000-0000-000000000015', 12, 73, 'confirmada', null)
  ) as d(id, n, horas, estado, motivo)
where se.nombre = 'Ensayo';
update public.reserva set fin = date_trunc('hour', now()) + interval '1 hour' where inicio = date_trunc('hour', now()) - interval '1 hour';
insert into public.cuota (id_reserva, hito, monto, estado, pagado)
select id, 'al_reservar', 100, case when right(id::text, 2) = '13' then 'pendiente' else 'pagada' end,
  case when right(id::text, 2) = '13' then 0 else 100 end from public.reserva;
insert into public.cuota (id_reserva, hito, monto) select id, 'al_terminar', 100 from public.reserva;

-- Marcar: solo personal y administrador.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select throws_ok($$select public.marcar_inasistencia('bbbbbbbb-0000-0000-0000-00000000000a')$$, '42501', null, 'el cliente no marca ni la suya');
reset role;
set local role anon;
select throws_ok($$select public.marcar_inasistencia('bbbbbbbb-0000-0000-0000-00000000000a')$$, '42501', null, 'anon no marca');
reset role;
select is((select estado from public.reserva where id = 'bbbbbbbb-0000-0000-0000-00000000000a'), 'confirmada', 'la reserva queda intacta tras los intentos ajenos');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000e1","role":"authenticated"}', true);
select throws_ok($$select public.marcar_inasistencia(gen_random_uuid())$$, 'P0002', null, 'inexistente');
select throws_ok($$select public.marcar_inasistencia('bbbbbbbb-0000-0000-0000-00000000000d')$$, 'P0001', 'no_aplicable', 'finalizada: no_aplicable');
select throws_ok($$select public.marcar_inasistencia('bbbbbbbb-0000-0000-0000-00000000000e')$$, 'P0001', 'no_aplicable', 'cancelada: no_aplicable');
select throws_ok($$select public.marcar_inasistencia('bbbbbbbb-0000-0000-0000-00000000000f')$$, 'P0001', 'tolerancia_no_cumplida', 'antes de inicio + tolerancia: tolerancia_no_cumplida');
select lives_ok($$select public.marcar_inasistencia('bbbbbbbb-0000-0000-0000-00000000000a')$$, 'el personal marca una confirmada');
select lives_ok($$select public.marcar_inasistencia('bbbbbbbb-0000-0000-0000-00000000000b')$$, 'tambien una pre_reservada');
select lives_ok($$select public.marcar_inasistencia('bbbbbbbb-0000-0000-0000-00000000000c')$$, 'y una en_curso');
select throws_ok($$select public.marcar_inasistencia('bbbbbbbb-0000-0000-0000-00000000000a')$$, 'P0001', 'no_aplicable', 'una ya marcada: no_aplicable');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.marcar_inasistencia('bbbbbbbb-0000-0000-0000-000000000010')$$, 'el administrador tambien marca');
select lives_ok($$select public.marcar_inasistencia('bbbbbbbb-0000-0000-0000-000000000014')$$, 'otra para la excepcion');
reset role;
select results_eq($$select estado, nivel_cancelacion, cancelacion_por, pagado_cancelacion, retenido, credito_generado, id_cancelador
  from public.reserva where id = 'bbbbbbbb-0000-0000-0000-00000000000a'$$,
  $$values ('no_asistio', null::smallint, 'inasistencia', 100.00::numeric, 100.00::numeric, 0.00::numeric, '00000000-0000-0000-0000-0000000000e1'::uuid)$$,
  'no_asistio: se retiene lo pagado, sin credito, queda quien la marco');
select is((select estado from public.cuota where id_reserva = 'bbbbbbbb-0000-0000-0000-00000000000a' and hito = 'al_terminar'), 'anulada', 'la cuota de saldo se anula');
select is((select estado from public.cuota where id_reserva = 'bbbbbbbb-0000-0000-0000-00000000000a' and hito = 'al_reservar'), 'pagada', 'y la pagada se conserva');
select is((select count(*)::int from public.credito where id_reserva = 'bbbbbbbb-0000-0000-0000-00000000000a'), 0, 'no hay credito');
select is((select count(*)::int from public.ocupacion_sala('5a5a5a5a-0000-0000-0000-000000000001', now() - interval '3 hours', now() + interval '3 hours')), 1, 'el tramo no se libera');
select is((select count(*)::int from public.notificacion where tipo = 'inasistencia_marcada' and destinatario = 'cli@t.pe'), 5, 'avisa al cliente de cada inasistencia');
select ok((select datos ->> 'folio' is not null and (datos ->> 'retenido')::numeric = 100 from public.notificacion
  where tipo = 'inasistencia_marcada' and datos ->> 'id_reserva' = 'bbbbbbbb-0000-0000-0000-00000000000a'), 'el aviso lleva folio y lo retenido');

-- Estados automaticos: pre_reservada con pagos que llega a su fin -> no_asistio; sin pagos la caduca el cron; en_curso -> finalizada.
insert into public.reserva (id, id_cliente, id_sala, id_servicio, inicio, fin, total, estado, vence_pago)
select d.id, '00000000-0000-0000-0000-0000000000c1', sa.id, se.id, d.inicio, d.inicio + interval '1 hour', 100, d.estado, '2099-01-01'
from public.sala_tecnica sa, public.servicio se,
  (values
    ('aaaaaaaa-0000-0000-0000-000000000001'::uuid, '2020-01-01 10:00-05'::timestamptz, 'pre_reservada'),
    ('aaaaaaaa-0000-0000-0000-000000000002', '2020-01-02 10:00-05', 'pre_reservada'),
    ('aaaaaaaa-0000-0000-0000-000000000003', '2020-01-03 10:00-05', 'en_curso')
  ) as d(id, inicio, estado)
where se.nombre = 'Ensayo' and sa.nombre = 'Sala principal';
insert into public.cuota (id_reserva, hito, monto, estado, pagado)
values ('aaaaaaaa-0000-0000-0000-000000000001', 'al_reservar', 50, 'pagada', 50),
       ('aaaaaaaa-0000-0000-0000-000000000001', 'al_terminar', 50, 'pendiente', 0),
       ('aaaaaaaa-0000-0000-0000-000000000002', 'al_reservar', 50, 'pendiente', 0),
       ('aaaaaaaa-0000-0000-0000-000000000003', 'al_terminar', 50, 'pendiente', 0);
select ok(public.avanzar_reservas() >= 2, 'avanza las reservas vencidas');
select results_eq($$select estado, retenido, credito_generado from public.reserva where id = 'aaaaaaaa-0000-0000-0000-000000000001'$$,
  $$values ('no_asistio', 50.00::numeric, 0.00::numeric)$$, 'la pre_reservada con pagos que llego a su fin pasa sola a no_asistio y retiene lo pagado');
select is((select estado from public.cuota where id_reserva = 'aaaaaaaa-0000-0000-0000-000000000001' and hito = 'al_terminar'), 'anulada', 'y anula su saldo');
select is((select estado from public.reserva where id = 'aaaaaaaa-0000-0000-0000-000000000002'), 'pre_reservada', 'sin pagos no pasa a no_asistio (la caducidad la trata el cron)');
select is((select estado from public.reserva where id = 'aaaaaaaa-0000-0000-0000-000000000003'), 'finalizada', 'una en_curso sin marca pasa a finalizada como hoy');
select is((select count(*)::int from public.notificacion where tipo = 'inasistencia_marcada' and datos ->> 'id_reserva' = 'aaaaaaaa-0000-0000-0000-000000000001'), 1, 'la automatica tambien avisa');
select is(public.avanzar_reservas(), 0, 'segunda corrida sin cambios');

-- Excepcion: cancelacion de nivel 2 o 3 del cliente, o inasistencia; una sola vez; solo el administrador.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select lives_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000011', null, 3)$$, 'cancelacion de nivel 3');
select lives_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000012', null, 2)$$, 'cancelacion de nivel 2');
select lives_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000015', null, 1)$$, 'cancelacion de nivel 1');
select throws_ok($$select public.aplicar_excepcion('bbbbbbbb-0000-0000-0000-000000000011', 'Fuerza mayor del cliente')$$, '42501', null, 'el cliente no aplica excepciones');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000e1","role":"authenticated"}', true);
select throws_ok($$select public.aplicar_excepcion('bbbbbbbb-0000-0000-0000-000000000011', 'Fuerza mayor del cliente')$$, '42501', null, 'el personal tampoco');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select throws_ok($$select public.aplicar_excepcion('bbbbbbbb-0000-0000-0000-000000000011', 'corto')$$, '22023', 'motivo_invalido', 'motivo de menos de 10 caracteres');
select throws_ok($$select public.aplicar_excepcion('bbbbbbbb-0000-0000-0000-000000000011', repeat('x', 501))$$, '22023', 'motivo_invalido', 'o de mas de 500');
select throws_ok($$select public.aplicar_excepcion(gen_random_uuid(), 'Fuerza mayor del cliente')$$, 'P0002', null, 'inexistente');
select throws_ok($$select public.aplicar_excepcion('bbbbbbbb-0000-0000-0000-000000000015', 'Fuerza mayor del cliente')$$, 'P0001', 'excepcion_no_aplicable', 'nivel 1 no necesita excepcion');
select throws_ok($$select public.aplicar_excepcion('bbbbbbbb-0000-0000-0000-00000000000f', 'Fuerza mayor del cliente')$$, 'P0001', 'excepcion_no_aplicable', 'una reserva viva no aplica');
select lives_ok($$select public.aplicar_excepcion('bbbbbbbb-0000-0000-0000-000000000011', '  Fuerza mayor: hospitalizacion  ')$$, 'excepcion sobre un nivel 3');
select lives_ok($$select public.aplicar_excepcion('bbbbbbbb-0000-0000-0000-000000000012', 'Fuerza mayor: hospitalizacion')$$, 'excepcion sobre un nivel 2');
select lives_ok($$select public.aplicar_excepcion('bbbbbbbb-0000-0000-0000-000000000014', 'El estudio abrio tarde ese dia')$$, 'excepcion sobre una inasistencia');
select throws_ok($$select public.aplicar_excepcion('bbbbbbbb-0000-0000-0000-000000000011', 'Fuerza mayor del cliente')$$, 'P0001', 'excepcion_ya_aplicada', 'una sola vez por reserva');
reset role;
select results_eq($$select tipo, monto, saldo, estado from public.credito where id_reserva = 'bbbbbbbb-0000-0000-0000-000000000011'$$,
  $$values ('excepcion', 100.00::numeric, 100.00::numeric, 'vigente')$$, 'lo retenido (100) pasa a credito de excepcion');
select results_eq($$select tipo, monto from public.credito where tipo = 'excepcion' and id_reserva = 'bbbbbbbb-0000-0000-0000-000000000012'$$,
  $$values ('excepcion', 50.00::numeric)$$, 'nivel 2: lo retenido (50) pasa a credito');
select results_eq($$select tipo, monto from public.credito where id_reserva = 'bbbbbbbb-0000-0000-0000-000000000014'$$,
  $$values ('excepcion', 100.00::numeric)$$, 'inasistencia: se convierte lo retenido');
select ok((select vence = (date_trunc('day', (now() at time zone 'America/Lima') + interval '31 days') at time zone 'America/Lima') - interval '1 microsecond'
  from public.credito where id_reserva = 'bbbbbbbb-0000-0000-0000-000000000011'), 'vence 30 dias despues de la decision, al final del dia en Lima');
select results_eq($$select retenido, credito_generado, excepcion_motivo, excepcion_por from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000011'$$,
  $$values (0.00::numeric, 100.00::numeric, 'Fuerza mayor: hospitalizacion', '00000000-0000-0000-0000-0000000000ad'::uuid)$$, 'la reserva anota la excepcion, quien y por que');
select ok((select excepcion_en is not null from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000011'), 'y cuando');

-- Una excepcion hace devolvible el credito (como el de nivel 1) y la unicidad esta en la base.
select throws_ok($$update public.reserva set excepcion_en = null where id = 'bbbbbbbb-0000-0000-0000-000000000011'$$, 'P0001', null, 'la excepcion aplicada no se quita');

select * from finish();
rollback;
