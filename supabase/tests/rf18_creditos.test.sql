begin;
create extension if not exists pgtap with schema extensions;
select plan(61);

-- RF-18 (parte A): credito, su uso al pagar (CA-05, CA-06), aviso y vencimiento por cron, inmutabilidad y RLS (CA-15).
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000c2', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli2@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000e1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'pe@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{}');
update public.usuario set rol = 'personal' where id = '00000000-0000-0000-0000-0000000000e1';
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';
update public.instruccion_pago set texto = 'x', activo = true where metodo = 'yape';

-- Reservas de origen (canceladas) y reservas donde se paga: ra y rb pre_reservadas de c1 (adelanto 100 y saldo 100).
insert into public.reserva (id, id_cliente, id_sala, id_servicio, inicio, fin, total, estado, motivo_cancelacion, vence_pago)
select d.id, d.cliente, sa.id, se.id, d.inicio, d.inicio + interval '1 hour', 200, d.estado, d.motivo, '2099-01-01'
from public.sala_tecnica sa, public.servicio se,
  (values
    ('bbbbbbbb-0000-0000-0000-0000000000a0'::uuid, '00000000-0000-0000-0000-0000000000c1'::uuid, '2027-01-01 10:00-05'::timestamptz, 'cancelada', 'cliente'),
    ('bbbbbbbb-0000-0000-0000-0000000000a1', '00000000-0000-0000-0000-0000000000c2', '2027-01-02 10:00-05', 'cancelada', 'cliente'),
    ('bbbbbbbb-0000-0000-0000-000000000001', '00000000-0000-0000-0000-0000000000c1', '2027-07-01 10:00-05', 'pre_reservada', null),
    ('bbbbbbbb-0000-0000-0000-000000000002', '00000000-0000-0000-0000-0000000000c1', '2027-07-02 10:00-05', 'pre_reservada', null),
    ('bbbbbbbb-0000-0000-0000-000000000003', '00000000-0000-0000-0000-0000000000c2', '2027-07-03 10:00-05', 'pre_reservada', null),
    ('bbbbbbbb-0000-0000-0000-000000000004', '00000000-0000-0000-0000-0000000000c1', '2027-07-04 10:00-05', 'pre_reservada', null)
  ) as d(id, cliente, inicio, estado, motivo)
where se.nombre = 'Ensayo';
insert into public.cuota (id, id_reserva, hito, monto) select ('cccccccc-0000-0000-0000-0000000000' || right(id::text, 2))::uuid, id, 'al_reservar', 100
  from public.reserva where right(id::text, 2) in ('01', '02', '03', '04');
insert into public.cuota (id, id_reserva, hito, monto) select ('dddddddd-0000-0000-0000-0000000000' || right(id::text, 2))::uuid, id, 'al_terminar', 100
  from public.reserva where right(id::text, 2) in ('01', '02', '03', '04');

-- Creditos: k1 vence en 10 dias (100), k2 en 5 dias (50), k3 ya vencido (30), k4 de c2, k5 en 6 dias (20), k6 en 20 dias (20).
select throws_ok($$insert into public.credito (id_cliente, id_reserva, tipo, monto, saldo, vence)
  values ('00000000-0000-0000-0000-0000000000c1', 'bbbbbbbb-0000-0000-0000-0000000000a0', 'nivel_1', 10, -1, now() + interval '1 day')$$, '23514', null, 'el saldo no es negativo');
select throws_ok($$insert into public.credito (id_cliente, id_reserva, tipo, monto, saldo, vence)
  values ('00000000-0000-0000-0000-0000000000c1', 'bbbbbbbb-0000-0000-0000-0000000000a0', 'nivel_1', 10, 11, now() + interval '1 day')$$, '23514', null, 'el saldo no supera el monto');
select throws_ok($$insert into public.credito (id_cliente, id_reserva, tipo, monto, saldo, vence)
  values ('00000000-0000-0000-0000-0000000000c1', 'bbbbbbbb-0000-0000-0000-0000000000a0', 'otro', 10, 10, now() + interval '1 day')$$, '23514', null, 'el tipo es de la lista');
insert into public.credito (id, id_cliente, id_reserva, tipo, monto, saldo, vence)
values
  ('eeeeeeee-0000-0000-0000-000000000001', '00000000-0000-0000-0000-0000000000c1', 'bbbbbbbb-0000-0000-0000-0000000000a0', 'nivel_1', 100, 100, now() + interval '10 days'),
  ('eeeeeeee-0000-0000-0000-000000000002', '00000000-0000-0000-0000-0000000000c1', 'bbbbbbbb-0000-0000-0000-0000000000a0', 'nivel_1', 50, 50, now() + interval '5 days'),
  ('eeeeeeee-0000-0000-0000-000000000003', '00000000-0000-0000-0000-0000000000c1', 'bbbbbbbb-0000-0000-0000-0000000000a0', 'nivel_2', 30, 30, now() - interval '1 day'),
  ('eeeeeeee-0000-0000-0000-000000000004', '00000000-0000-0000-0000-0000000000c2', 'bbbbbbbb-0000-0000-0000-0000000000a1', 'nivel_1', 80, 80, now() + interval '10 days'),
  ('eeeeeeee-0000-0000-0000-000000000005', '00000000-0000-0000-0000-0000000000c1', 'bbbbbbbb-0000-0000-0000-0000000000a0', 'excepcion', 20, 20, now() + interval '6 days'),
  ('eeeeeeee-0000-0000-0000-000000000006', '00000000-0000-0000-0000-0000000000c1', 'bbbbbbbb-0000-0000-0000-0000000000a0', 'nivel_2', 20, 20, now() + interval '20 days');

-- Usar credito: errores previos a tocar nada.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select throws_ok($$select public.aplicar_credito('cccccccc-0000-0000-0000-000000000001', 0)$$, '22023', 'monto_invalido', 'monto 0: monto_invalido');
select throws_ok($$select public.aplicar_credito('cccccccc-0000-0000-0000-000000000001', 100.01)$$, '22023', 'monto_invalido', 'mas de lo que falta de la cuota: monto_invalido');
select throws_ok($$select public.aplicar_credito('cccccccc-0000-0000-0000-000000000001', 10.005)$$, '22023', 'monto_invalido', 'mas de dos decimales: monto_invalido');
select throws_ok($$select public.aplicar_credito('cccccccc-0000-0000-0000-000000000001', 100, 'eeeeeeee-0000-0000-0000-000000000002')$$, 'P0001', 'credito_insuficiente', 'el credito elegido no alcanza');
select throws_ok($$select public.aplicar_credito('cccccccc-0000-0000-0000-000000000001', 100, 'eeeeeeee-0000-0000-0000-000000000003')$$, 'P0001', 'credito_insuficiente', 'un credito vencido no se usa');
select throws_ok($$select public.aplicar_credito('cccccccc-0000-0000-0000-000000000001', 10, 'eeeeeeee-0000-0000-0000-000000000004')$$, 'P0002', null, 'el credito de otro cliente no existe para el');
select throws_ok($$select public.aplicar_credito('cccccccc-0000-0000-0000-000000000003', 10)$$, 'P0002', null, 'la cuota de otro cliente no existe para el');
select throws_ok($$select public.aplicar_credito('cccccccc-0000-0000-0000-000000000001', 230)$$, '22023', 'monto_invalido', 'mas que la cuota se rechaza antes que mirar el credito');

-- Parcial, sin elegir: usa el que vence antes (k2, 50).
select lives_ok($$select public.aplicar_credito('cccccccc-0000-0000-0000-000000000001', 30)$$, 'aplica 30 a la cuota del adelanto');
reset role;
select results_eq($$select saldo, estado from public.credito where id = 'eeeeeeee-0000-0000-0000-000000000002'$$,
  $$values (20.00::numeric, 'vigente')$$, 'se uso primero el que vence antes');
select results_eq($$select estado, pagado from public.cuota where id = 'cccccccc-0000-0000-0000-000000000001'$$,
  $$values ('pendiente', 30.00::numeric)$$, 'aplicacion parcial: la cuota sigue pendiente con 30 pagados');
select is((select estado from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000001'), 'pre_reservada', 'sin cubrir el adelanto la reserva no se confirma');
select is(public.tiene_pagos('bbbbbbbb-0000-0000-0000-000000000001'), true, 'el credito aplicado cuenta como pago');

-- El pago con captura posterior exige el monto restante (70).
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select throws_ok($$insert into public.comprobante_pago (id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
  values ('cccccccc-0000-0000-0000-000000000001', auth.uid(), 'yape', 100, 'OP-CRED-1', auth.uid() || '/a.png', 'image/png')$$,
  'P0001', 'monto_invalido', 'la captura debe ser por el monto restante');
select lives_ok($$insert into public.comprobante_pago (id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
  values ('cccccccc-0000-0000-0000-000000000001', auth.uid(), 'yape', 70, 'OP-CRED-2', auth.uid() || '/b.png', 'image/png')$$, 'por el restante si');
-- Con una captura en validacion no se aplica credito a esa cuota.
select throws_ok($$select public.aplicar_credito('cccccccc-0000-0000-0000-000000000001', 10)$$, 'P0001', 'no_pagable', 'cuota con pago en validacion: no_pagable');
reset role;
-- Aprobar: la cuota queda pagada con 30 de credito + 70 de captura, y la reserva se confirma.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.aprobar_pago((select id from public.comprobante_pago where numero_operacion = 'OP-CRED-2'))$$, 'aprueba la captura restante');
reset role;
select results_eq($$select estado, pagado from public.cuota where id = 'cccccccc-0000-0000-0000-000000000001'$$,
  $$values ('pagada', 100.00::numeric)$$, 'credito + captura = cuota pagada');
select is((select estado from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000001'), 'confirmada', 'y la reserva se confirma');

-- Total, sin elegir, en la reserva rb: 100 = k2 (20) + k5 (20) + k1 (60); k5 vence en 6 dias y k1 en 10: orden por vencimiento.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select lives_ok($$select public.aplicar_credito('cccccccc-0000-0000-0000-000000000002', 100)$$, 'cubre toda la cuota con varios creditos');
select throws_ok($$select public.aplicar_credito('cccccccc-0000-0000-0000-000000000002', 1)$$, 'P0001', 'cuota_pagada', 'cuota ya pagada');
reset role;
select results_eq($$select id::text, saldo, estado from public.credito where id in ('eeeeeeee-0000-0000-0000-000000000002', 'eeeeeeee-0000-0000-0000-000000000005',
  'eeeeeeee-0000-0000-0000-000000000001') order by id$$, $$values ('eeeeeeee-0000-0000-0000-000000000001', 40.00::numeric, 'vigente'),
  ('eeeeeeee-0000-0000-0000-000000000002', 0.00::numeric, 'agotado'), ('eeeeeeee-0000-0000-0000-000000000005', 0.00::numeric, 'agotado')$$,
  'se agotan en orden de vencimiento: k2, k5 y 60 de k1');
select is((select count(*)::int from public.aplicacion_credito where id_cuota = 'cccccccc-0000-0000-0000-000000000002'), 3, 'una aplicacion por credito usado');
select is((select sum(monto) from public.aplicacion_credito where id_cuota = 'cccccccc-0000-0000-0000-000000000002'), 100.00::numeric, 'que suman lo aplicado');
select is((select estado from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000002'), 'confirmada', 'cubrir el adelanto confirma la reserva');

-- Quien usa: solo el dueno.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c2","role":"authenticated"}', true);
select throws_ok($$select public.aplicar_credito('cccccccc-0000-0000-0000-000000000004', 10)$$, 'P0002', null, 'otro cliente: la cuota no existe para el');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000e1","role":"authenticated"}', true);
select throws_ok($$select public.aplicar_credito('cccccccc-0000-0000-0000-000000000004', 10)$$, '42501', null, 'el personal no usa creditos');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select throws_ok($$select public.aplicar_credito('cccccccc-0000-0000-0000-000000000004', 10)$$, '42501', null, 'el administrador tampoco');
reset role;
set local role anon;
select throws_ok($$select public.aplicar_credito('cccccccc-0000-0000-0000-000000000004', 10)$$, '42501', null, 'anon no usa creditos');
reset role;
select is((select pagado from public.cuota where id = 'cccccccc-0000-0000-0000-000000000004'), 0.00::numeric, 'la cuota ajena queda intacta');
select is((select saldo from public.credito where id = 'eeeeeeee-0000-0000-0000-000000000004'), 80.00::numeric, 'el credito ajeno queda intacto');

-- Cuota no pagable: reserva cancelada o cuota anulada; pago en validacion.
update public.reserva set estado = 'cancelada', motivo_cancelacion = 'cliente' where id = 'bbbbbbbb-0000-0000-0000-000000000004';
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select throws_ok($$select public.aplicar_credito('cccccccc-0000-0000-0000-000000000004', 10)$$, 'P0001', 'no_pagable', 'reserva cancelada: no_pagable');
reset role;

-- Cron diario: aviso 7 dias antes (una sola vez) y vencimiento.
select is((select schedule from cron.job where jobname = 'procesar_creditos'), '5 5 * * *', 'se programa cada dia a las 00:05 de Lima');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select throws_ok($$select public.procesar_creditos()$$, '42501', null, 'ni el administrador la ejecuta');
reset role;
-- k5 esta agotado; k6 (20 dias) y k1 (10 dias) no avisan; se prepara k7 que vence en 6 dias con saldo.
insert into public.credito (id, id_cliente, id_reserva, tipo, monto, saldo, vence)
values ('eeeeeeee-0000-0000-0000-000000000007', '00000000-0000-0000-0000-0000000000c1', 'bbbbbbbb-0000-0000-0000-0000000000a0', 'nivel_1', 60, 60, now() + interval '6 days');
select is(public.procesar_creditos(), 2, 'primera corrida: vence k3 y avisa k7 (2 cambios)');
select is((select estado from public.credito where id = 'eeeeeeee-0000-0000-0000-000000000003'), 'vencido', 'el vencido pasa a vencido');
select is((select estado from public.credito where id = 'eeeeeeee-0000-0000-0000-000000000006'), 'vigente', 'el que vence en 20 dias sigue vigente');
select is((select count(*)::int from public.notificacion where tipo = 'credito_por_vencer'), 1, 'un aviso de credito por vencer');
select ok((select destinatario = 'cli@t.pe' and datos ->> 'id_credito' = 'eeeeeeee-0000-0000-0000-000000000007' and (datos ->> 'saldo')::numeric = 60
  and datos ? 'vence' from public.notificacion where tipo = 'credito_por_vencer'), 'va al dueno con saldo y vencimiento');
select is(public.procesar_creditos(), 0, 'segunda corrida: nada nuevo');
select is((select count(*)::int from public.notificacion where tipo = 'credito_por_vencer'), 1, 'el aviso se envia una sola vez');

-- Una devolucion pendiente congela el credito: no vence ni se usa.
update public.credito set vence = now() - interval '1 hour' where id = 'eeeeeeee-0000-0000-0000-000000000006';
insert into public.devolucion (id_credito, id_reserva, id_cliente, tipo, motivo, monto_solicitado)
values ('eeeeeeee-0000-0000-0000-000000000006', 'bbbbbbbb-0000-0000-0000-0000000000a0', '00000000-0000-0000-0000-0000000000c1', 'nivel_1', 'Necesito el dinero de vuelta', 20);
select is(public.procesar_creditos(), 0, 'con devolucion pendiente no vence');
select is((select estado from public.credito where id = 'eeeeeeee-0000-0000-0000-000000000006'), 'vigente', 'sigue vigente mientras esta pendiente');

-- Inmutabilidad: ni por la API (sin privilegios) ni directo.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select throws_ok($$update public.credito set saldo = 1000 where id = 'eeeeeeee-0000-0000-0000-000000000001'$$, '42501', null, 'el cliente no edita su credito');
select throws_ok($$delete from public.credito$$, '42501', null, 'ni lo borra');
select throws_ok($$insert into public.credito (id_cliente, id_reserva, tipo, monto, saldo, vence) values (auth.uid(), 'bbbbbbbb-0000-0000-0000-0000000000a0', 'nivel_1', 1, 1, now())$$, '42501', null, 'ni se lo crea');
select throws_ok($$update public.aplicacion_credito set monto = 1$$, '42501', null, 'las aplicaciones no se editan');
reset role;
select ok(not has_table_privilege('bugalu_api', 'public.credito', 'update') and not has_table_privilege('bugalu_api', 'public.credito', 'insert'),
  'el rol de la API no edita ni crea creditos');
select ok(not has_table_privilege('bugalu_api', 'public.aplicacion_credito', 'delete') and not has_table_privilege('bugalu_api', 'public.devolucion', 'update'),
  'ni borra aplicaciones ni edita devoluciones');
select throws_ok($$update public.credito set monto = 1000 where id = 'eeeeeeee-0000-0000-0000-000000000001'$$, 'P0001', null, 'el monto de un credito no cambia nunca');
select throws_ok($$delete from public.credito where id = 'eeeeeeee-0000-0000-0000-000000000001'$$, 'P0001', null, 'un credito no se borra');
select throws_ok($$update public.aplicacion_credito set monto = 1$$, 'P0001', null, 'una aplicacion no se edita');
select throws_ok($$delete from public.aplicacion_credito$$, 'P0001', null, 'una aplicacion no se borra');

-- RLS de lectura: cada cliente ve los suyos, el administrador todos, el personal y anon ninguno.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c2","role":"authenticated"}', true);
select results_eq($$select id::text from public.credito$$, $$values ('eeeeeeee-0000-0000-0000-000000000004')$$, 'c2 solo ve su credito');
select is((select count(*)::int from public.aplicacion_credito), 0, 'c2 no ve aplicaciones ajenas');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000e1","role":"authenticated"}', true);
select is((select count(*)::int from public.credito), 0, 'el personal no ve creditos');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select is((select count(*)::int from public.credito), 7, 'el administrador ve todos');
reset role;
set local role anon;
select throws_ok($$select * from public.credito$$, '42501', null, 'anon no lee creditos');
reset role;

select * from finish();
rollback;
